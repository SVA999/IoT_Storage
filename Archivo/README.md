# Punto 1 — Archivo (.db SQLite) en Docker sobre EC2

Este componente corresponde a la carpeta **`Archivo`** del proyecto. Implementa un servidor Flask que recibe peticiones HTTP desde los componentes IoT, almacena sus lecturas en una base de datos SQLite local y muestra un panel web de monitoreo estilo Cyberpunk.

El servidor se ejecuta dentro de un contenedor Docker en una instancia Amazon EC2. La base SQLite se conserva fuera del contenedor mediante un volumen, por lo que las lecturas sobreviven a reinicios o recreaciones del contenedor.

> Los pasos genéricos de EC2 (crear la instancia, Security Group, instalar Docker/Git, clonar el repo) están en el [README raíz](../README.md#aprovisionamiento-de-la-instancia-ec2-una-sola-vez). Aquí solo va lo específico de este punto.

## Estructura de esta carpeta

```text
Archivo/
├── app.py
├── Dockerfile
├── requirements.txt
├── .dockerignore
└── datos.db          # se crea/actualiza en tiempo de ejecución
```

## Funcionalidades

- Panel web de monitoreo disponible desde la IP pública de EC2.
- Endpoint `POST /datos` para recibir datos JSON desde un LilyGO T-Beam u otro dispositivo IoT.
- Endpoint `GET /datos` para consultar las lecturas almacenadas.
- Endpoint `DELETE /datos` para vaciar el registro de lecturas.
- Endpoint `GET /health` para comprobar que el servicio está activo.
- SQLite local (`datos.db`) para persistir lecturas.
- Slider en la interfaz para mostrar u ocultar un formulario que simula peticiones IoT manuales.
- Visualización de última lectura, fecha, hora, tiempo transcurrido y las últimas lecturas recibidas.

Este punto usa el puerto **80** de la EC2 (ya incluido en el Security Group común, ver README raíz).

## Archivos necesarios en `Archivo/`

### `app.py`

Contiene la aplicación Flask. Define la interfaz web, los endpoints y el acceso a SQLite. El archivo de base de datos se crea automáticamente como `/app/datos.db` dentro del contenedor.

### `requirements.txt`

```text
Flask==3.0.3
gunicorn==22.0.0
```

No se debe instalar `sqlite3` ni `db-sqlite3`: `sqlite3` hace parte de la biblioteca estándar de Python.

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--access-logfile", "-", "app:app"]
```

### `.dockerignore`

```text
venv/
__pycache__/
*.pyc
.git/
.gitignore
.env
*.pem
datos.db
```

Se excluye `datos.db` del contexto de construcción porque la base debe persistir en el host EC2, no dentro de la imagen Docker.

## Despliegue

Dentro de la EC2, ya con el repo clonado (ver README raíz):

### 1. Construir la imagen Docker

Ubicado en la carpeta `Archivo`:

```bash
docker build -t flask-iot:1.0 .
```

Comprueba que se creó la imagen:

```bash
docker images
```

### 2. Ejecutar el contenedor permanentemente

Ejecuta el siguiente comando desde `Archivo`:

```bash
docker run -d \
  --name flask-iot \
  --restart unless-stopped \
  -p 80:8000 \
  -v "$(pwd)/datos.db:/app/datos.db" \
  flask-iot:1.0
```

Significado de los argumentos:

| Argumento | Función |
|---|---|
| `-d` | Ejecuta el contenedor en segundo plano |
| `--name flask-iot` | Define un nombre fácil de administrar |
| `--restart unless-stopped` | Inicia Docker automáticamente tras reiniciar EC2, excepto si lo detuviste manualmente |
| `-p 80:8000` | Publica el servidor: puerto 80 de EC2 hacia puerto 8000 del contenedor |
| `-v "$(pwd)/datos.db:/app/datos.db"` | Persiste SQLite como archivo local en la carpeta `Archivo` del host EC2 |

Verifica que el contenedor esté arriba:

```bash
docker ps
```

Debes ver un mapeo similar a:

```text
0.0.0.0:80->8000/tcp
```

## Verificación

### Panel web

Abre en el navegador:

```text
http://<IP_PUBLICA_EC2>
```

Ejemplo:

```text
http://107.23.106.61
```

### Health check

Desde EC2 o desde tu computador local:

```bash
curl http://<IP_PUBLICA_EC2>/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "total_lecturas": 0
}
```

### Enviar una petición IoT de prueba

```bash
curl -X POST http://<IP_PUBLICA_EC2>/datos \
  -H "Content-Type: application/json" \
  -d '{"dispositivo":"lilygo-tbeam-01","evento":"heartbeat","contador":1}'
```

En Git Bash para Windows, si tienes inconvenientes con los saltos de línea, usa una sola línea:

```bash
curl -X POST http://<IP_PUBLICA_EC2>/datos -H "Content-Type: application/json" -d "{\"dispositivo\":\"lilygo-tbeam-01\",\"evento\":\"heartbeat\",\"contador\":1}"
```

La respuesta debe tener código HTTP `201` y una estructura similar a:

```json
{
  "status": "recibido",
  "data": {
    "timestamp": 1778030000.0,
    "origen": "iot",
    "payload": {
      "dispositivo": "lilygo-tbeam-01",
      "evento": "heartbeat",
      "contador": 1
    }
  }
}
```

### Consultar las lecturas

```bash
curl http://<IP_PUBLICA_EC2>/datos
```

### Vaciar las lecturas

> Advertencia: esta acción elimina permanentemente todas las filas de la tabla `lecturas`.

```bash
curl -X DELETE http://<IP_PUBLICA_EC2>/datos
```

También es posible hacerlo desde el botón **[ vaciar registro ]** de la interfaz web.

## Actualizar el proyecto desde GitHub

Cuando subas cambios al repositorio:

```bash
cd /home/ubuntu/<REPOSITORIO>
git pull
cd Archivo
```

Detén y elimina el contenedor anterior:

```bash
docker stop flask-iot
docker rm flask-iot
```

Construye la nueva versión:

```bash
docker build -t flask-iot:1.1 .
```

Inicia el nuevo contenedor reutilizando el mismo archivo `datos.db`:

```bash
docker run -d \
  --name flask-iot \
  --restart unless-stopped \
  -p 80:8000 \
  -v "$(pwd)/datos.db:/app/datos.db" \
  flask-iot:1.1
```

El archivo SQLite no se pierde porque se mantiene en el host EC2 dentro de:

```text
/home/ubuntu/<REPOSITORIO>/Archivo/datos.db
```

## Administración y diagnóstico

| Acción | Comando |
|---|---|
| Ver contenedores activos | `docker ps` |
| Ver todos los contenedores | `docker ps -a` |
| Ver logs en vivo | `docker logs -f flask-iot` |
| Ver últimos logs | `docker logs --tail 100 flask-iot` |
| Reiniciar | `docker restart flask-iot` |
| Detener | `docker stop flask-iot` |
| Iniciar | `docker start flask-iot` |
| Eliminar contenedor | `docker rm -f flask-iot` |
| Ver tamaño de la base | `ls -lh datos.db` |
| Consultar health desde EC2 | `curl http://localhost/health` |

## Persistencia de datos

La persistencia se logra con el volumen Docker:

```bash
-v "$(pwd)/datos.db:/app/datos.db"
```

- `/app/datos.db` es la ruta que utiliza Flask dentro del contenedor.
- `$(pwd)/datos.db` es el archivo real guardado en la carpeta `Archivo` de EC2.
- Reiniciar el contenedor o reiniciar la instancia EC2 no elimina las lecturas.
- Eliminar el archivo `datos.db` sí elimina todos los datos almacenados.

## Flujo de comunicación

```text
LilyGO T-Beam / Cliente de prueba
              |
              | POST JSON a http://<IP_EC2>/datos
              v
EC2: Docker (flask-iot)
              |
              v
Flask + Gunicorn
              |
              v
SQLite: Archivo/datos.db
              |
              v
Panel web: GET http://<IP_EC2>/
```

## Notas de seguridad para la práctica

- Este despliegue usa HTTP, adecuado para laboratorio y pruebas controladas. En una implementación real conviene usar HTTPS con Nginx y certificados TLS.
- El endpoint `DELETE /datos` no tiene autenticación: cualquier persona que conozca la IP puede vaciar los datos si el puerto está público. Para un proyecto real, se debe proteger con API key, autenticación o una red privada.
