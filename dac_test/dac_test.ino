#include <WiFi.h>
#include <WiFiUdp.h>
#include <driver/i2s.h>

const char* ssid = "allenw";
const char* password = "tt123456";

#define I2S_BCK_PIN   26
#define I2S_WS_PIN    25
#define I2S_DATA_PIN  27

#define FRAMES_PER_PACKET 256

WiFiUDP udp;

// Simple buffer
#define BUFFER_SIZE 32768
uint8_t audioBuffer[BUFFER_SIZE];
int writePos = 0;
int readPos = 0;

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
  
  Serial.println("\n=== Audio Stream v2 (Non-Blocking) ===\n");
  
  // WiFi
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi: " + WiFi.localIP().toString());
  
  udp.begin(12345);
  Serial.println("UDP: port 12345");
  
  // I2S
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 44100,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 1024,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t pin_config = {
    .mck_io_num = I2S_PIN_NO_CHANGE,
    .bck_io_num = I2S_BCK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_DATA_PIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };
  
  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
  
  Serial.println("I2S: ready");
  Serial.println("\nWaiting for audio...\n");
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