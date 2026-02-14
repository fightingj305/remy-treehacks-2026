#include <WiFi.h>
#include <WiFiUdp.h>

const char* ssid = "allenw";
const char* password = "tt123456";

WiFiUDP udp;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=== UDP Reception Test ===\n");
  
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nConnected!");
  Serial.println("IP: " + WiFi.localIP().toString());
  
  udp.begin(12345);
  Serial.println("Listening on UDP port 12345\n");
}

unsigned long totalPackets = 0;
unsigned long totalBytes = 0;

void loop() {
  int packetSize = udp.parsePacket();
  
  if (packetSize > 0) {
    uint8_t buffer[2048];
    int len = udp.read(buffer, 2048);
    
    totalPackets++;
    totalBytes += len;
    
    Serial.printf("[%lu] Packet #%lu: %d bytes (total: %lu KB)\n",
                  millis(), totalPackets, len, totalBytes / 1024);
  }
  
  yield();
}