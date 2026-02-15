#include <Arduino.h>
#include "BluetoothA2DPSource.h"
#include <driver/i2s.h>

#define I2S_WS 18
#define I2S_SD 16
#define I2S_SCK 17
#define I2S_PORT I2S_NUM_0

BluetoothA2DPSource a2dp_source;

// Buffer to hold mono samples before converting to stereo Frames
int16_t mono_buffer[512]; 

// CORRECTED CALLBACK: Uses 'Frame' instead of 'uint8_t'
int32_t get_audio_data(Frame *data, int32_t len) {
    size_t bytes_read = 0;
    
    // 'len' here is the number of Frames requested. 
    // Each Frame is 4 bytes (16-bit L + 16-bit R).
    // We need to read 'len' number of 16-bit samples from the mono mic.
    esp_err_t result = i2s_read(I2S_PORT, mono_buffer, len * sizeof(int16_t), &bytes_read, portMAX_DELAY);

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

void setup() {
    Serial.begin(115200);

    // I2S Config
    const i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 44100, 
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = 0,
        .dma_buf_count = 8,
        .dma_buf_len = 512,
        .use_apll = false
    };

    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);

    const i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD
    };
    i2s_set_pin(I2S_PORT, &pin_config);

    Serial.println("Connecting to device...");
    a2dp_source.start("kelvin-rpi", get_audio_data); 
}

void loop() {
    // Bluetooth library runs on Core 0; Loop stays free
    delay(10);
}