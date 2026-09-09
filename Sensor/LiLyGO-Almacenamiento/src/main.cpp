#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>

// ===================================
// CONFIGURACION DE RED Y SERVIDOR
// ===================================
const char* ssid = "UPBWiFi";
const char* password = "";

// Debe incluir /datos, porque ese es el endpoint POST de Flask.
// Usamos HTTP por ahora para pruebas.
// Cuando agregues HTTPS, se usa WiFiClientSecure.
const char* serverUrl = "http://44.223.60.154/datos";

// Identificador logico del dispositivo
const char* deviceId = "lilygo-tbeam-01";

// Intervalo entre peticiones
const unsigned long INTERVALO_ENVIO_MS = 15000;

unsigned long ultimoEnvio = 0;
unsigned long contadorMensajes = 0;

// ===================================
// FUNCIONES
// ===================================
void conectarWiFi() {
  Serial.print("[WiFi] Conectando a: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  const unsigned long timeout = 15000;
  unsigned long inicio = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - inicio < timeout) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Conexion exitosa.");
    Serial.print("[WiFi] IP local: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WiFi] RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\n[WiFi] No fue posible conectar.");
  }
}

void enviarPeticion() {
  // Si se desconecto, intenta reconectar antes de enviar.
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Conexion perdida. Reconectando...");
    conectarWiFi();

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[HTTP] Envio cancelado: no hay WiFi.");
      return;
    }
  }

  WiFiClient client;
  HTTPClient http;

  Serial.println("\n[HTTP] Preparando POST al servidor...");

  // JSON simple: no GPS, no temperatura, no sensores.
  contadorMensajes++;

  String payload = "{";
  payload += "\"dispositivo\":\"" + String(deviceId) + "\",";
  payload += "\"evento\":\"heartbeat\",";
  payload += "\"mensaje\":\"Hola desde LilyGO T-Beam\",";
  payload += "\"contador\":" + String(contadorMensajes) + ",";
  payload += "\"uptime_ms\":" + String(millis());
  payload += "}";

  Serial.println("[HTTP] Payload:");
  Serial.println(payload);

  // Inicializa la solicitud HTTP hacia EC2.
  http.begin(client, serverUrl);
  http.addHeader("Content-Type", "application/json");

  // Ejecuta POST y recibe el codigo HTTP.
  int codigoRespuesta = http.POST(payload);

  if (codigoRespuesta > 0) {
    Serial.print("[HTTP] Codigo de respuesta: ");
    Serial.println(codigoRespuesta);

    String respuesta = http.getString();
    Serial.print("[HTTP] Respuesta del servidor: ");
    Serial.println(respuesta);

    if (codigoRespuesta == 201) {
      Serial.println("[OK] Peticion registrada en SQLite.");
    }
  } else {
    Serial.print("[HTTP] Error: ");
    Serial.println(http.errorToString(codigoRespuesta));
  }

  // Libera la conexion y recursos del cliente HTTP.
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==================================");
  Serial.println("LILYGO T-BEAM -> FLASK IOT");
  Serial.println("MODO: PETICIONES HTTP SIMPLES");
  Serial.println("==================================");

  conectarWiFi();

  // Enviar una primera peticion apenas arranca.
  enviarPeticion();
  ultimoEnvio = millis();
}

void loop() {
  // Envia un heartbeat cada 10 segundos.
  if (millis() - ultimoEnvio >= INTERVALO_ENVIO_MS) {
    ultimoEnvio = millis();
    enviarPeticion();
  }
}