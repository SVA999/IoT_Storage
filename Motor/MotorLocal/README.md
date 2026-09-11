# Punto 2 — Motor Local (MariaDB) en Docker sobre EC2

Este punto reemplaza el archivo `.db` del [Punto 1](../../Archivo/README.md) por un **motor de base de datos relacional (MariaDB)** corriendo en su propio contenedor Docker, junto al servidor Flask, en la misma instancia EC2. La app expone el mismo contrato de endpoints que los demás puntos (`/datos`, `/health`, panel web en `/`), pero ahora las lecturas quedan en tablas SQL en vez de un archivo plano.

> Los pasos genéricos de EC2 (crear la instancia, Security Group, instalar Docker/Git, clonar el repo) están en el [README raíz](../../README.md#aprovisionamiento-de-la-instancia-ec2-una-sola-vez). Aquí solo va lo específico de este punto.

## Estructura de esta carpeta

```
Motor/MotorLocal/
├── app.py              # servidor Flask, usa mysql-connector-python
├── docker-compose.yml  # levanta MariaDB + la app juntos
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

## Variables de entorno

| Variable | Default en `docker-compose.yml` | Uso |
|---|---|---|
| `DB_HOST` | `mariadb` | Nombre del servicio de MariaDB en la red de compose |
| `DB_PORT` | `3306` | Puerto de MariaDB |
| `DB_USER` | `iot_user` | Usuario de la base de datos |
| `DB_PASSWORD` | `iot_pass` | Contraseña del usuario |
| `DB_NAME` | `iot_local` | Base de datos usada |

**Cambia `MARIADB_PASSWORD`, `MARIADB_ROOT_PASSWORD` y `DB_PASSWORD` en `docker-compose.yml` antes de desplegar** — los valores del repo son solo para pruebas de la práctica.

## Despliegue

Dentro de la EC2, ya con el repo clonado (ver README raíz):

```bash
cd IoT_Storage/Motor/MotorLocal
docker compose up -d --build
```

Esto levanta dos contenedores: `mariadb-iot` (motor de base de datos) y `flask-motorlocal` (servidor Flask con Gunicorn), conectados por la red interna que crea `docker compose`. El servicio queda expuesto en el puerto **8002** del host.

La app espera automáticamente a que MariaDB esté lista antes de crear la tabla (`init_db` reintenta la conexión varias veces al arrancar), así que no hace falta levantar los servicios en un orden especial.

## Verificación

```bash
curl http://<IP_PUBLICA_EC2>:8002/health
# {"status": "ok", "total_lecturas": 0}

curl -X POST http://<IP_PUBLICA_EC2>:8002/datos \
  -H "Content-Type: application/json" \
  -d '{"origen":"iot","temperatura":24.1,"humedad":55}'
# 201 Created

curl http://<IP_PUBLICA_EC2>:8002/datos
```

Panel web: `http://<IP_PUBLICA_EC2>:8002/`.

## Administración y diagnóstico

| Comando | Uso |
|---|---|
| `docker compose ps` | Ver estado de los dos contenedores |
| `docker compose logs -f app` | Logs en vivo del servidor Flask |
| `docker compose logs -f mariadb` | Logs en vivo del motor de base de datos |
| `docker compose restart app` | Reiniciar solo el servidor Flask |
| `docker compose down` | Detener y eliminar los contenedores (el volumen de datos se conserva) |
| `docker exec -it mariadb-iot mysql -u iot_user -p iot_local` | Entrar directo a la base de datos |

## Persistencia de datos

`docker-compose.yml` define el volumen nombrado `mariadb_data`, montado en `/var/lib/mysql` dentro del contenedor de MariaDB. Los datos sobreviven a `docker compose down`, reinicios de la EC2 y reconstrucciones de la imagen de la app (`docker compose up -d --build`). Solo se pierden si se elimina explícitamente el volumen (`docker compose down -v` o `docker volume rm`).

## Actualizar el proyecto desde GitHub

```bash
git pull
docker compose up -d --build
```

`docker compose` reconstruye solo la imagen de `app` (el código cambió) y reutiliza el contenedor de `mariadb` que ya está corriendo, sin perder datos.

## Flujo de comunicación

```
LilyGO T-Beam / curl
        |  POST JSON
        v
EC2 :8002 -> contenedor flask-motorlocal (Flask + Gunicorn)
        |  INSERT parametrizado
        v
contenedor mariadb-iot -> tabla `lecturas` (volumen mariadb_data)
        |
        v
panel web GET /  (mismo host:8002)
```

## Notas de seguridad para la práctica

- Las credenciales de `docker-compose.yml` están en texto plano por simplicidad de la práctica; en un proyecto real irían en un archivo `.env` fuera de git (ya cubierto por `.gitignore`) o en un gestor de secretos.
- El puerto 3306 de MariaDB no se expone a internet en este `docker-compose.yml` (no tiene `ports:` hacia el host) — solo es alcanzable dentro de la red interna de Docker, entre los propios contenedores.
- `DELETE /datos` no tiene autenticación, igual que en el Punto 1 — válido para la práctica, no para producción.
