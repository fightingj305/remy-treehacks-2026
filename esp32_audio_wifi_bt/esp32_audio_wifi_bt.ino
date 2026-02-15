#include <WiFi.h>
#include <WiFiUdp.h>
#include <driver/i2s.h>
#include "BluetoothA2DPSource.h"
#include "esp_heap_caps.h"

const char* ssid = "allenw";
const char* password = "tt123456";

#define I2S_DAC_BCK_PIN   26
#define I2S_DAC_WS_PIN    25
#define I2S_DAC_DATA_PIN  27

#define I2S_MIC_WS 19
#define I2S_MIC_SD 23
#define I2S_MIC_SCK 21
#define I2S_MIC I2S_NUM_1
#define I2S_DAC I2S_NUM_0

#define FRAMES_PER_PACKET 256

WiFiUDP udp;

// Simple buffer
#define BUFFER_SIZE 8192
uint8_t *audioBuffer = NULL;

int writePos = 0;
int readPos = 0;

BluetoothA2DPSource a2dp_source;

// Buffer to hold mono samples before converting to stereo Frames
int16_t mono_buffer[512]; 

// CORRECTED CALLBACK: Uses 'Frame' instead of 'uint8_t'
int32_t get_audio_data(Frame *data, int32_t len) {
    size_t bytes_read = 0;
    
    // 'len' here is the number of Frames requested. 
    // Each Frame is 4 bytes (16-bit L + 16-bit R).
    // We need to read 'len' number of 16-bit samples from the mono mic.
    esp_err_t result = i2s_read(I2S_MIC, mono_buffer, len * sizeof(int16_t), &bytes_read, portMAX_DELAY);

    if (result == ESP_OK && bytes_read > 0) {
        int samples_read = bytes_read / sizeof(int16_t);

        for (int i = 0; i < samples_read; i++) {
            // Map the mono sample to both Left and Right channels of the Frame
            data[i].channel1 = mono_buffer[i]; // Left
            data[i].channel2 = mono_buffer[i]; // Right
        }
        return samples_read; // Return the number of frames populated
    }
    return 0;
}
void connection_state_changed(esp_a2d_connection_state_t state, void *ptr) {
  Serial.print("A2DP state: ");
  Serial.println(state);
}


int available() {
  if (writePos >= readPos) {
    return writePos - readPos;
  } else {
    return BUFFER_SIZE - readPos + writePos;
  }
}

void bufferWrite(uint8_t* data, int len) {
  for (int i = 0; i < len; i++) {
    audioBuffer[writePos] = data[i];
    writePos = (writePos + 1) % BUFFER_SIZE;
  }
}

int bufferRead(uint8_t* dest, int len) {
  int avail = available();
  if (len > avail) len = avail;
  
  for (int i = 0; i < len; i++) {
    dest[i] = audioBuffer[readPos];
    readPos = (readPos + 1) % BUFFER_SIZE;
  }
  return len;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Audio Stream ===\n");
  
  // I2S
  i2s_config_t i2s_dac_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 44100,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t dac_pin_config = {
    .mck_io_num = I2S_PIN_NO_CHANGE,
    .bck_io_num = I2S_DAC_BCK_PIN,
    .ws_io_num = I2S_DAC_WS_PIN,
    .data_out_num = I2S_DAC_DATA_PIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };
  
  i2s_driver_install(I2S_DAC, &i2s_dac_config, 0, NULL);
  i2s_set_pin(I2S_DAC, &dac_pin_config);
  
  const i2s_config_t i2s_mic_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = 44100, 
      .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
      .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
      .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_STAND_I2S),
      .intr_alloc_flags = 0,
      .dma_buf_count = 4,
      .dma_buf_len = 128,
      .use_apll = false
  };


  const i2s_pin_config_t mic_pin_config = {
      .bck_io_num = I2S_MIC_SCK,
      .ws_io_num = I2S_MIC_WS,
      .data_out_num = I2S_PIN_NO_CHANGE,
      .data_in_num = I2S_MIC_SD
  };
  i2s_driver_install(I2S_MIC, &i2s_mic_config, 0, NULL);
  i2s_set_pin(I2S_MIC, &mic_pin_config);
  // 2. Start Bluetooth
  Serial.printf("BT Controller status: %d\n", esp_bt_controller_get_status());
  a2dp_source.set_on_connection_state_changed(connection_state_changed);
  a2dp_source.set_ssp_enabled(false); // use legacy pairing
  a2dp_source.set_auto_reconnect(true);
  a2dp_source.start("FRFR-GO", get_audio_data);
  Serial.printf("BT Controller status AFTER start: %d\n",
              esp_bt_controller_get_status());

  Serial.printf("Free heap: %u\n", heap_caps_get_free_size(MALLOC_CAP_8BIT));
  Serial.printf("Largest block: %u\n",
                heap_caps_get_largest_free_block(MALLOC_CAP_8BIT));

  // 1. Start WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(100);
  delay(1000);

  // 3. NOW allocate big buffer
  audioBuffer = (uint8_t*) heap_caps_malloc(BUFFER_SIZE, MALLOC_CAP_8BIT);

  if (!audioBuffer) {
    Serial.println("Failed to allocate audio buffer!");
    while (1);
  }


  Serial.println("\nWiFi: " + WiFi.localIP().toString());
  
  udp.begin(12345);
  Serial.println("UDP: port 12345");
}

unsigned long packetsReceived = 0;
bool playing = false;

void loop() {
  // PRIORITY 1: Receive packets (don't block here)
  int packetSize = udp.parsePacket();
  
  if (packetSize > 0) {
    uint8_t buffer[2048];
    int len = udp.read(buffer, 2048);
    
    packetsReceived++;
    
    if (packetsReceived == 1) {
      Serial.println(">>> FIRST PACKET RECEIVED <<<");
      Serial.printf("Size: %d bytes\n\n", len);
    }
    
    if (packetsReceived % 20 == 0) {
      Serial.printf("📥 Packets: %lu | Buffer: %d bytes\n", 
                   packetsReceived, available());
    }
    
    // Store in buffer
    bufferWrite(buffer, len);
  }
  
  // PRIORITY 2: Play audio (use timeout to avoid blocking too long)
  int bufLevel = available();
  
  // if (!playing && bufLevel > BUFFER_SIZE * 0.25) {
  if (!playing && bufLevel > BUFFER_SIZE * 0.5) {
    Serial.println("\n▶ Starting playback\n");
    playing = true;
  }
  
  if (playing && bufLevel > 0) {
    uint8_t playBuf[1024];
    int bytesRead = bufferRead(playBuf, bufLevel > 1024 ? 1024 : bufLevel);
    
    if (bytesRead > 0) {
      size_t written;
      // CRITICAL: Use timeout instead of portMAX_DELAY
      i2s_write(I2S_NUM_0, playBuf, bytesRead, &written, pdMS_TO_TICKS(10));
      
      static bool firstWrite = true;
      if (firstWrite) {
        firstWrite = false;
        Serial.println(">>> FIRST I2S WRITE <<<\n");
      }
      delay(FRAMES_PER_PACKET/44.1);
    }
  } else if (playing && bufLevel == 0) {
    playing = false;
  }
}