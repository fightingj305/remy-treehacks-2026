#include <WiFi.h>
#include <WiFiUdp.h>
#include <driver/i2s.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// --- WiFi ---
const char* ssid = "allenw";
const char* password = "tt123456";

WiFiUDP udpIn;        // receive audio packets
WiFiUDP udpOut;       // send microphone audio

const IPAddress remoteIP(172, 20, 10, 3);
const uint16_t remotePort = 12345;
const uint16_t localPort = 12345;

// --- I2S DAC (output) ---
#define I2S_DAC_BCK_PIN   26
#define I2S_DAC_WS_PIN    25
#define I2S_DAC_DATA_PIN  27
#define I2S_DAC I2S_NUM_0

// --- I2S MIC (input) ---
#define I2S_MIC_WS 19
#define I2S_MIC_SD 23
#define I2S_MIC_SCK 21
#define I2S_MIC I2S_NUM_1

// --- Buffers ---
#define UDP_BUFFER_SIZE 1024
uint8_t udpBuffer[UDP_BUFFER_SIZE];       // for incoming audio
int16_t micBuffer[512];                   // for sending mic audio

// --- DS18B20 - MOVED TO GPIO 4 (GPIO 22 conflicts with I2S) ---
#define ONE_WIRE_BUS 4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

enum TempState { IDLE, WAITING_CONVERSION };
TempState tempState = IDLE;
unsigned long conversionStartTime = 0;
const unsigned long TEMP_READ_INTERVAL = 2000;  // Read every 2 seconds
const unsigned long CONVERSION_TIME = 200;      // 9-bit resolution = 93.75ms
unsigned long lastTempRead = 0;
float lastTempC = -127;
DeviceAddress tempSensor;
bool sensorInit = false;

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== UDP Audio Stream ===");

    // --- WiFi ---
    WiFi.begin(ssid, password);
    WiFi.setSleep(false);
    while (WiFi.status() != WL_CONNECTED) {
        delay(200);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected: " + WiFi.localIP().toString());

    udpIn.begin(localPort);
    Serial.printf("Listening for UDP on port %d\n", localPort);

    // --- I2S DAC config ---
    i2s_config_t dacConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = 44100,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 512,
        .use_apll = false,
        .tx_desc_auto_clear = true
    };

    i2s_pin_config_t dacPins = {
        .mck_io_num = I2S_PIN_NO_CHANGE,
        .bck_io_num = I2S_DAC_BCK_PIN,
        .ws_io_num = I2S_DAC_WS_PIN,
        .data_out_num = I2S_DAC_DATA_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    i2s_driver_install(I2S_DAC, &dacConfig, 0, NULL);
    i2s_set_pin(I2S_DAC, &dacPins);

    // --- I2S MIC config ---
    i2s_config_t micConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 44100,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = 0,
        .dma_buf_count = 4,
        .dma_buf_len = 256,
        .use_apll = false
    };

    i2s_pin_config_t micPins = {
        .bck_io_num = I2S_MIC_SCK,
        .ws_io_num = I2S_MIC_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_MIC_SD
    };

    i2s_driver_install(I2S_MIC, &micConfig, 0, NULL);
    i2s_set_pin(I2S_MIC, &micPins);
    
    // --- Temperature Sensor Init ---
    delay(100);
    Serial.println("\nInitializing DS18B20 on GPIO 4...");
    sensors.begin();
    
    int deviceCount = sensors.getDeviceCount();
    Serial.printf("Found %d temperature sensor(s)\n", deviceCount);
    
    if (deviceCount > 0) {
        if (sensors.getAddress(tempSensor, 0)) {
            Serial.print("Sensor address: ");
            for (uint8_t i = 0; i < 8; i++) {
                Serial.printf("%02X ", tempSensor[i]);
            }
            Serial.println();
            
            sensors.setResolution(tempSensor, 9);  // 9-bit = 93.75ms conversion
            sensors.setWaitForConversion(false);   // Non-blocking mode
            sensorInit = true;
            Serial.println("Temperature sensor ready!");
        } else {
            Serial.println("ERROR: Could not get sensor address");
        }
    } else {
        Serial.println("WARNING: No sensors found - check wiring on GPIO 4");
    }
}

void loop() {
    unsigned long now = millis();
    
    // --- Non-blocking temperature state machine ---
    if (sensorInit) {
        switch (tempState) {
            case IDLE:
                if (now - lastTempRead >= TEMP_READ_INTERVAL) {
                    sensors.requestTemperaturesByAddress(tempSensor);
                    conversionStartTime = now;
                    tempState = WAITING_CONVERSION;
                }
                break;
                
            case WAITING_CONVERSION:
                if (now - conversionStartTime >= CONVERSION_TIME) {
                    float tempC = sensors.getTempC(tempSensor);
                    
                    if (tempC > -55 && tempC < 125) {  // DS18B20 valid range
                        lastTempC = tempC;
                        Serial.printf("Temperature: %.2f°C\n", tempC);
                    }
                    lastTempRead = now;
                    tempState = IDLE;
                }
                break;
        }
    }
    
    // --- Receive UDP audio and play over DAC ---
    int packetSize = udpIn.parsePacket();
    if (packetSize > 0) {
        if (packetSize > UDP_BUFFER_SIZE) packetSize = UDP_BUFFER_SIZE;
        int len = udpIn.read(udpBuffer, packetSize);
        size_t written;
        i2s_write(I2S_DAC, udpBuffer, len, &written, pdMS_TO_TICKS(10));
    }

    // --- Read I2S MIC and send to remote ---
    size_t bytesRead = 0;
    esp_err_t res = i2s_read(I2S_MIC, micBuffer, sizeof(micBuffer), &bytesRead, 0);
    if (res == ESP_OK && bytesRead > 0) {
        udpOut.beginPacket(remoteIP, remotePort);
        udpOut.write((uint8_t*)micBuffer, bytesRead);
        udpOut.endPacket();
    }
}