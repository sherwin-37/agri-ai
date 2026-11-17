# Arduino Uno wiring: DHT11 data to D2, soil analog output to A0, rain analog output to A1.
#include <DHT.h>
#include <Wire.h>
#include <math.h>

const uint8_t DHT_PIN = 2;
const uint8_t SOIL_PIN = A0;
const uint8_t RAIN_PIN = A1;
const unsigned long SEND_INTERVAL_MS = 2000;

DHT dht(DHT_PIN, DHT11);
unsigned long lastSentAt = 0;

bool i2cDeviceFound(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

bool lcdAdapterFound() {
  return i2cDeviceFound(0x27) || i2cDeviceFound(0x3F);
}

void setup() {
  Serial.begin(9600);
  Wire.begin();
  dht.begin();
}

void loop() {
  const unsigned long now = millis();
  if (now - lastSentAt < SEND_INTERVAL_MS) {
    return;
  }
  lastSentAt = now;

  const float temperatureC = dht.readTemperature();
  const float humidityPct = dht.readHumidity();
  const bool dhtOk = !isnan(temperatureC) && !isnan(humidityPct);
  const int soilRaw = analogRead(SOIL_PIN);
  const int rainRaw = analogRead(RAIN_PIN);
  const bool lcdOk = lcdAdapterFound();

  Serial.print(F("{\"schema\":\"agri-ai-v1\",\"uptime_ms\":"));
  Serial.print(now);
  Serial.print(F(",\"temperature_c\":"));
  if (dhtOk) {
    Serial.print(temperatureC, 1);
  } else {
    Serial.print(F("null"));
  }
  Serial.print(F(",\"humidity_pct\":"));
  if (dhtOk) {
    Serial.print(humidityPct, 1);
  } else {
    Serial.print(F("null"));
  }
  Serial.print(F(",\"soil_raw\":"));
  Serial.print(soilRaw);
  Serial.print(F(",\"rain_raw\":"));
  Serial.print(rainRaw);
  Serial.print(F(",\"dht_ok\":"));
  Serial.print(dhtOk ? F("true") : F("false"));
  Serial.print(F(",\"lcd_ok\":"));
  Serial.print(lcdOk ? F("true") : F("false"));
  Serial.println(F("}"));
}
