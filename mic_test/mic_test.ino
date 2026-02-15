#include <Arduino.h>
#include <WiFi.h>
#include <driver/i2s.h>
#include <WiFiUdp.h>

// I2S (Inter-IC Sound) pin definitions for the microphone
#define I2S_WS 18    // Word Select (LRCLK) pin
#define I2S_SD 16    // Serial Data (SDATA) pin, receives audio data from the mic
#define I2S_SCK 17   // Serial Clock (BCLK) pin
#define I2S_PORT I2S_NUM_0 // Use I2S port 0

// Audio buffer configuration
#define bufferLen 1024  // Increase buffer size to accommodate more audio data

// WiFi network credentials
const char* ssid = "Dbit_2.4G_AF2D";           // Replace with your WiFi name
const char* password = "x4CM4AkmMMp$EkkN";   // Replace with your WiFi password

// UDP server settings (where audio data will be sent)
const char* host = "192.168.10.102"; // IP address of the computer/server receiving audio
const int port = 8888;                  // Port number the receiver is listening on

WiFiUDP udp;              // Create a UDP object for data transmission
int16_t sBuffer[bufferLen]; // Buffer array to hold 16-bit audio samples

void setup() {
    Serial.begin(115200);
    Serial.println("Setting up I2S...");

    // Connect to WiFi network
    setup_wifi();

    delay(1000);
    i2s_install();   // Configure and install the I2S driver
    i2s_setpin();    // Set the I2S pins
    i2s_start(I2S_PORT); // Start the I2S receiver
    delay(500);
}

void loop() {
    size_t bytesIn = 0;
    // Read audio data from the I2S buffer
    esp_err_t result = i2s_read(I2S_PORT, &sBuffer, bufferLen * sizeof(int16_t), &bytesIn, portMAX_DELAY);

    // If data was read successfully and the buffer isn't empty
    if (result == ESP_OK && bytesIn > 0) {
        // Send the audio data via UDP to the specified host and port
        udp.beginPacket(host, port);
        udp.write((uint8_t*)sBuffer, bytesIn);
        udp.endPacket();
    }
}

// Function to handle WiFi connection
void setup_wifi() {
    delay(10);
    Serial.println();
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);

    WiFi.begin(ssid, password); // Initiate connection

    // Wait for connection to establish
    while (WiFi.status() != WL_CONNECTED) {
        delay(600);
        Serial.print("-"); // Print a dash every 600ms while connecting
    }

    // Connection successful
    Serial.println("\nWiFi connected");
    Serial.println("IP address assigned: ");
    Serial.println(WiFi.localIP()); // Print the ESP32's IP address
}

// Function to install and configure the I2S driver
void i2s_install() {
    const i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX), // Set as master receiver
        .sample_rate = 16000,              // Audio sample rate (16kHz)
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT, // 16-bit per sample
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT, // Use left channel only (mono)
        .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_STAND_I2S), // Standard I2S format
        .intr_alloc_flags = 0,             // No interrupt flags
        .dma_buf_count = 8,                // Number of DMA buffers
        .dma_buf_len = bufferLen,          // Size of each DMA buffer
        .use_apll = false                  // Do not use APLL clock
    };

    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL); // Install the driver
}

// Function to set the I2S pinout
void i2s_setpin() {
    const i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,   // Bit clock pin
        .ws_io_num = I2S_WS,     // Word select pin
        .data_out_num = I2S_PIN_NO_CHANGE, // No data output needed (RX only)
        .data_in_num = I2S_SD    // Data input pin (from microphone)
    };

    i2s_set_pin(I2S_PORT, &pin_config); // Apply the pin configuration
}