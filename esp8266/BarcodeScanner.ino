#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

#define SERVER "http://YOUR_SEVER_IP:9288" //GrocyCompanionCN api的地址
#define CLIENT "temporary_storage" //对应config.ini中GrocyLocation的值
#define GPIO0_PIN 0
#define LED_PIN 2 
#define HTTP_CODE_OK 200
#ifndef STASSID
#define STASSID "YOUR_SSID"  //WiFi名
#define STAPSK "YOUR_PASSWORD" //WiFi密码
#endif

void setup() {
  Serial.begin(9600);
  WiFi.begin(STASSID, STAPSK);
  pinMode(GPIO0_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
}

void loop() {
  // Wait for WiFi connection
  if ((WiFi.status() == WL_CONNECTED)) {
    digitalWrite(LED_PIN, HIGH);
    if (Serial.available()) {

      String serialString = Serial.readStringUntil('\n'); // Read a line from Serial
      // Remove leading and trailing whitespace, including newline characters
      serialString.trim();

      // Ensure serialString has at least 4 characters
      if (serialString.length() >= 4) {
        String code = serialString.substring(0, 3); // Get the first 3 characters
        String digits = serialString.substring(3);   // Get the rest of the string
        int gpio0State = digitalRead(GPIO0_PIN);
        requestPost(code, digits, gpio0State);
      } else {
        errorBlink();
      }
    }
  } else {
  }
}

void requestPost(String code, String digits, int gpio0State) {
  WiFiClient client;
  HTTPClient http;

  int httpCode = 0;
  if (gpio0State == 1){
    http.begin(client, String(SERVER) + "/consume");
    http.addHeader("Content-Type", "application/json");
    httpCode = http.POST("{\"client\":\"" CLIENT "\",\"aimid\":\"" + code + "\",\"barcode\":\"" + digits + "\"}");
  } else {
    http.begin(client, String(SERVER) + "/add");
    http.addHeader("Content-Type", "application/json");
    httpCode = http.POST("{\"client\":\"" CLIENT "\",\"aimid\":\"" + code + "\",\"barcode\":\"" + digits + "\"}");
  }

  if (httpCode == HTTP_CODE_OK) {
    successBlink();
  } else {
    errorBlink();
  }
  http.end();
}

void successBlink(){
  digitalWrite(LED_PIN, LOW);
  delay(500);
  digitalWrite(LED_PIN, HIGH);
}

void errorBlink(){
  for(int i=0;i<=10;i++){
  digitalWrite(LED_PIN, LOW);
  delay(100);
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  }
}