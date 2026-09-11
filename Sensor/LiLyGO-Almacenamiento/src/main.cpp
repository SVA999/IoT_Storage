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
// Los 4 puntos de la practica corren en paralelo en la misma EC2,
// cada uno en su propio puerto, asi que se envia el mismo heartbeat a los 4.
const char* serverUrls[] = {
  "http://44.223.60.154:80/datos",    // Punto 1 - Archivo (.db SQLite)
  "http://44.223.60.154:8002/datos",  // Punto 2 - Motor Local (MariaDB)
  "http://44.223.60.154:8003/datos",  // Punto 3 - Motor Externo (AWS RDS MySQL)
  "http://44.223.60.154:8004/datos"   // Punto 4 - Contenedor + boto3 (AWS S3)
};
const int cantidadServidores = sizeof(serverUrls) / sizeof(serverUrls[0]);

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

  Serial.println("\n[HTTP] Preparando POST hacia los 4 puntos de la practica...");

  // JSON simple: no GPS, no temperatura, no sensores.
  // Se arma una sola vez y se reenvia igual a los 4 servidores.
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

  // Envia el mismo payload a cada punto por separado: si uno falla
  // (por ejemplo el RDS externo), los demas igual quedan registrados.
  for (int i = 0; i < cantidadServidores; i++) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, serverUrls[i]);
    http.addHeader("Content-Type", "application/json");

    int codigoRespuesta = http.POST(payload);

    Serial.print("[HTTP] Punto ");
    Serial.print(i + 1);
    Serial.print(" (");
    Serial.print(serverUrls[i]);
    Serial.print(") -> ");

    if (codigoRespuesta > 0) {
      Serial.print("codigo ");
      Serial.println(codigoRespuesta);
    } else {
      Serial.print("error ");
      Serial.println(http.errorToString(codigoRespuesta));
    }

    http.end();
  }
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