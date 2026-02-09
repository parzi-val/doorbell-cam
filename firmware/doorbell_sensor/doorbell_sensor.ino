
#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// --- CONFIGURATION ---
const char* ssid = "Bala";
const char* password = "cakn5137";

// Backend Server IP (Change this to your PC's IP)
const char* backend_host = "10.35.161.141"; 
const int backend_port = 8000;
const char* backend_path = "/ws/sensor";

// Pins (NodeMCU / Wemos D1 Mini Mapping)
const int PIN_PIR = D1; 
const int PIN_BTN = D2;

// --- GLOBALS ---
WebSocketsClient webSocket;
unsigned long lastHeartbeat = 0;
const unsigned long HEARTBEAT_INTERVAL = 30000;

// State Tracking
int lastPirState = LOW;
int lastBtnState = HIGH; // Pullup, so HIGH is unpressed
unsigned long lastBtnDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 50;

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.printf("[WSc] Disconnected!\n");
            break;
        case WStype_CONNECTED: {
            Serial.printf("[WSc] Connected to url: %s\n", payload);
            // Send initial heartbeat
            sendHeartbeat();
        } break;
        case WStype_TEXT:
            Serial.printf("[WSc] get text: %s\n", payload);
            break;
    }
}

void setup() {
    Serial.begin(115200);
    
    // Pin Modes
    pinMode(PIN_PIR, INPUT);
    pinMode(PIN_BTN, INPUT_PULLUP);

    // WiFi
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());

    // WebSocket
    webSocket.begin(backend_host, backend_port, backend_path);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
}

void sendJson(String sensor, String state) {
    StaticJsonDocument<200> doc;
    doc["type"] = "sensor_reading";
    doc["sensor"] = sensor;
    doc["state"] = state;
    doc["timestamp"] = millis();
    
    String jsonString;
    serializeJson(doc, jsonString);
    webSocket.sendTXT(jsonString);
    Serial.println("Sent: " + jsonString);
}

void sendHeartbeat() {
    StaticJsonDocument<200> doc;
    doc["type"] = "heartbeat";
    doc["device"] = "esp8266";
    
    String jsonString;
    serializeJson(doc, jsonString);
    webSocket.sendTXT(jsonString);
}

void loop() {
    webSocket.loop();

    // 1. Heartbeat
    if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
        lastHeartbeat = millis();
        sendHeartbeat();
    }

    // 2. Read PIR
    int pirState = digitalRead(PIN_PIR);
    if (pirState != lastPirState) {
        if (pirState == HIGH) {
            sendJson("pir", "active");
        } else {
            sendJson("pir", "inactive");
        }
        lastPirState = pirState;
    }

    // 3. Read Button (Debounced)
    int reading = digitalRead(PIN_BTN);
    if (reading != lastBtnState) {
        if (millis() - lastBtnDebounceTime > DEBOUNCE_DELAY) {
             if (reading == LOW) { // Pressed (Active Low)
                 sendJson("doorbell_btn", "pressed");
             }
             lastBtnDebounceTime = millis();
             lastBtnState = reading;
        }
    }
}
