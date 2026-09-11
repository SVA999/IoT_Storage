# Punto 3 — Motor Externo (AWS RDS MySQL) sobre EC2

Este punto reemplaza el motor local del [Punto 2](../MotorLocal/README.md) por un **motor de base de datos administrado por AWS (RDS MySQL)**, externo a la instancia EC2. El servidor Flask (contenedor Docker) se conecta al endpoint de RDS por red en vez de a un contenedor local. Mismo contrato de endpoints que los demás puntos (`/datos`, `/health`, panel web en `/`).

> Los pasos genéricos de EC2 (crear la instancia, Security Group, instalar Docker/Git, clonar el repo) están en el [README raíz](../../README.md#aprovisionamiento-de-la-instancia-ec2-una-sola-vez). Aquí solo va lo específico de este punto: crear el RDS y desplegar el contenedor.

## Estructura de esta carpeta

```
Motor/RDS/
├── app.py              # servidor Flask, usa mysql-connector-python contra RDS
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

## 1. Crear la instancia RDS MySQL (por consola web de AWS)

1. En la consola de AWS, entra al servicio **RDS** → **Bases de datos** → **Crear base de datos**.
2. Método de creación: **Creación estándar**. Motor: **MySQL** (versión por defecto que ofrezca la consola).
3. Plantillas: elige **Free tier** (capa gratuita) para la práctica.
4. Configuración:
   - **Identificador de instancia de base de datos**: por ejemplo `iot-rds-practica`.
   - **Usuario maestro**: por ejemplo `admin`.
   - **Contraseña maestra**: defínela y guárdala (la vas a necesitar como `DB_PASSWORD`).
5. Clase de instancia: **db.t3.micro** (o la que ofrezca el free tier).
6. Almacenamiento: deja los valores por defecto (20 GiB, gp2/gp3).
7. Conectividad:
   - **Nube privada virtual (VPC)**: la misma VPC donde está tu instancia EC2 (por defecto suele ser la VPC "default", igual que el EC2 del Punto 1).
   - **Acceso público**: **No** (el RDS no necesita ser alcanzable desde internet, solo desde tu EC2).
   - **Grupo de seguridad de VPC**: crea uno nuevo, por ejemplo `sg-rds-practica`.
8. Configuración adicional:
   - **Nombre de la base de datos inicial**: por ejemplo `iot_rds` (si lo dejas vacío, tendrás que crear la base manualmente después).
9. Clic en **Crear base de datos** y espera a que el estado pase a **Available** (unos minutos).
10. Entra a la instancia creada y copia el **endpoint** (algo como `iot-rds-practica.xxxxxxxxxx.us-east-1.rds.amazonaws.com`) — es tu `DB_HOST`.

### Abrir el puerto 3306 solo hacia el EC2

1. Ve a **EC2** → **Security Groups** → localiza el Security Group que se creó para el RDS (`sg-rds-practica`).
2. Edita las **reglas de entrada** → **Agregar regla**:
   - Tipo: **MYSQL/Aurora** (puerto 3306).
   - Origen: **Personalizado**, selecciona el **Security Group de tu instancia EC2** (no `0.0.0.0/0`) — así solo tu EC2 puede conectarse al RDS.
3. Guarda las reglas.

## 2. Variables de entorno de la app

| Variable | Ejemplo | Uso |
|---|---|---|
| `DB_HOST` | `iot-rds-practica.xxxxx.us-east-1.rds.amazonaws.com` | Endpoint copiado de la consola RDS |
| `DB_PORT` | `3306` | Puerto de MySQL |
| `DB_USER` | `admin` | Usuario maestro definido al crear el RDS |
| `DB_PASSWORD` | *(tu contraseña maestra)* | Contraseña del usuario |
| `DB_NAME` | `iot_rds` | Nombre de la base de datos inicial |

La app falla al arrancar con un mensaje claro si falta `DB_HOST`, `DB_USER` o `DB_NAME`, para evitar quedar corriendo mal configurada en silencio.

## 3. Desplegar el contenedor en la EC2

Dentro de la EC2, ya con el repo clonado (ver README raíz):

```bash
cd IoT_Storage/Motor/RDS
docker build -t flask-rds:1.0 .

docker run -d \
  --name flask-rds \
  --restart unless-stopped \
  -p 8003:8000 \
  -e DB_HOST="iot-rds-practica.xxxxx.us-east-1.rds.amazonaws.com" \
  -e DB_PORT=3306 \
  -e DB_USER="admin" \
  -e DB_PASSWORD="TU_PASSWORD" \
  -e DB_NAME="iot_rds" \
  flask-rds:1.0
```

## Verificación

```bash
curl http://<IP_PUBLICA_EC2>:8003/health
# {"status": "ok", "total_lecturas": 0}

curl -X POST http://<IP_PUBLICA_EC2>:8003/datos \
  -H "Content-Type: application/json" \
  -d '{"origen":"iot","temperatura":24.1,"humedad":55}'
# 201 Created

curl http://<IP_PUBLICA_EC2>:8003/datos
```

Panel web: `http://<IP_PUBLICA_EC2>:8003/`.

## Administración y diagnóstico

| Comando | Uso |
|---|---|
| `docker ps` | Ver que `flask-rds` esté corriendo |
| `docker logs -f flask-rds` | Logs en vivo (incluye reintentos de conexión a RDS si los hay) |
| `docker restart flask-rds` | Reiniciar el contenedor |
| `docker rm -f flask-rds` | Detener y eliminar el contenedor |

## Actualizar el proyecto desde GitHub

```bash
git pull
docker stop flask-rds && docker rm flask-rds
docker build -t flask-rds:1.1 .
docker run -d --name flask-rds --restart unless-stopped -p 8003:8000 \
  -e DB_HOST="..." -e DB_USER="..." -e DB_PASSWORD="..." -e DB_NAME="..." \
  flask-rds:1.1
```

Los datos no se pierden porque viven en RDS, completamente fuera del ciclo de vida del contenedor.

## Flujo de comunicación

```
LilyGO T-Beam / curl
        |  POST JSON
        v
EC2 :8003 -> contenedor flask-rds (Flask + Gunicorn)
        |  INSERT parametrizado (fuera de la EC2, por red)
        v
AWS RDS MySQL (instancia administrada, con backups automáticos)
        |
        v
panel web GET /  (mismo host:8003)
```

## Notas de seguridad para la práctica

- El RDS se creó **sin acceso público** y su Security Group solo permite entrada desde el Security Group del EC2 — nunca lo abras a `0.0.0.0/0`.
- La contraseña maestra y las variables `-e` quedan visibles en el historial de shell y en `docker inspect`; para un proyecto real usarías AWS Secrets Manager o al menos un archivo `.env` fuera de git.
- `DELETE /datos` sigue sin autenticación, igual que en los otros puntos — solo válido para la práctica.
