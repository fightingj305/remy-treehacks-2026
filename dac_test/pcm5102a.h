#ifndef PCM5102A_DRIVER_H
#define PCM5102A_DRIVER_H

#include <Arduino.h>
#include "driver/i2s.h"

#define I2S_BCK_PIN     26
#define I2S_WS_PIN      25
#define I2S_DATA_PIN    27

class PCM5102A {
private:
    i2s_port_t i2s_num;
    uint32_t sample_rate;
    bool is_initialized;
    
public:
    PCM5102A(i2s_port_t port = I2S_NUM_0) {
        i2s_num = port;
        is_initialized = false;
        sample_rate = 44100;
    }
    
    bool begin(uint32_t rate, i2s_bits_per_sample_t bits, i2s_channel_fmt_t channels) {
        sample_rate = rate;
        
        // Critical: Proper DMA buffer sizing
        // For 44.1kHz stereo 16-bit: 4 bytes per sample
        // Want ~23ms per DMA buffer (1024 samples = 4096 bytes)
        i2s_config_t i2s_config = {
            .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
            .sample_rate = rate,
            .bits_per_sample = bits,
            .channel_format = channels,
            .communication_format = I2S_COMM_FORMAT_STAND_I2S,
            .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
            .dma_buf_count = 8,              // 8 buffers
            .dma_buf_len = 1024,             // 1024 samples per buffer (4096 bytes for 16-bit stereo)
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
        
        esp_err_t err = i2s_driver_install(i2s_num, &i2s_config, 0, NULL);
        if (err != ESP_OK) {
            Serial.printf("❌ I2S install failed: %d\n", err);
            return false;
        }
        
        err = i2s_set_pin(i2s_num, &pin_config);
        if (err != ESP_OK) {
            Serial.printf("❌ I2S pin config failed: %d\n", err);
            i2s_driver_uninstall(i2s_num);
            return false;
        }
        
        // Set I2S clock precisely
        err = i2s_set_sample_rates(i2s_num, rate);
        if (err != ESP_OK) {
            Serial.printf("⚠ I2S set sample rate failed: %d\n", err);
        }
        
        i2s_zero_dma_buffer(i2s_num);
        is_initialized = true;
        
        Serial.println("✓ PCM5102A initialized");
        Serial.printf("  Sample Rate: %d Hz\n", rate);
        Serial.printf("  Bits: %d\n", bits);
        Serial.printf("  Channels: %d\n", channels == I2S_CHANNEL_FMT_RIGHT_LEFT ? 2 : 1);
        Serial.printf("  DMA: %d buffers × %d samples\n", 
                     i2s_config.dma_buf_count, i2s_config.dma_buf_len);
        Serial.printf("  Buffer time: %.1f ms\n", 
                     (i2s_config.dma_buf_count * i2s_config.dma_buf_len * 1000.0) / rate);
        
        return true;
    }
    
    size_t write(const void* buffer, size_t size) {
        if (!is_initialized) return 0;
        
        size_t bytes_written = 0;
        
        // CRITICAL: portMAX_DELAY makes this BLOCK until DMA has space
        // This provides natural rate-limiting to match playback speed
        esp_err_t err = i2s_write(i2s_num, buffer, size, &bytes_written, portMAX_DELAY);
        
        if (err != ESP_OK) {
            Serial.printf("⚠ I2S write error: %d\n", err);
            return 0;
        }
        
        return bytes_written;
    }
    // In pcm5102a.h, add this overload:
    size_t write(const void* buffer, size_t size, uint32_t timeout_ms) {
        if (!is_initialized) return 0;
        
        size_t bytes_written = 0;
        TickType_t timeout_ticks = pdMS_TO_TICKS(timeout_ms);
        
        esp_err_t err = i2s_write(i2s_num, buffer, size, &bytes_written, timeout_ticks);
        
        if (err != ESP_OK && err != ESP_ERR_TIMEOUT) {
            Serial.printf("⚠ I2S write error: %d\n", err);
        }
        
        return bytes_written;
    }
    void clear() {
        if (is_initialized) {
            i2s_zero_dma_buffer(i2s_num);
        }
    }
    
    void end() {
        if (is_initialized) {
            i2s_driver_uninstall(i2s_num);
            is_initialized = false;
        }
    }
};

#endif