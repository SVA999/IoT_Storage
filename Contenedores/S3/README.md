# Punto 4 — Contenedor con Boto3 conectado a S3

Este punto reemplaza la base de datos relacional de los puntos anteriores por **almacenamiento de objetos (AWS S3)**: cada lectura se guarda como un archivo JSON individual en un bucket, usando `boto3`. Corre en contenedor Docker igual que los demás puntos, mismo contrato de endpoints (`/datos`, `/health`, panel web en `/`).

> Los pasos genéricos de EC2 (crear la instancia, Security Group, instalar Docker/Git, clonar el repo) están en el [README raíz](../../README.md#aprovisionamiento-de-la-instancia-ec2-una-sola-vez). Aquí solo va lo específico de este punto: crear el bucket, dar permisos y desplegar el contenedor.

## Estructura de esta carpeta

```
Contenedores/S3/
├── app.py              # servidor Flask, usa boto3 contra S3
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

Cada lectura queda como un objeto `lecturas/<timestamp>_<origen>.json` dentro del bucket, con el mismo contenido `{timestamp, origen, payload}` que usan los demás puntos.

## 1. Crear el bucket S3 (por consola web de AWS)

1. Consola de AWS → servicio **S3** → **Crear bucket**.
2. **Nombre del bucket**: globalmente único, por ejemplo `iot-storage-practica-<tu-usuario>`.
3. Región: la misma región donde está tu EC2.
4. Deja **Bloquear todo el acceso público** activado (el bucket no necesita ser público, la app accede por API con permisos de IAM).
5. Resto de opciones por defecto → **Crear bucket**.

## 2. Crear y adjuntar un IAM Role al EC2 (para no manejar llaves de acceso)

1. Consola de AWS → **IAM** → **Roles** → **Crear rol**.
2. Entidad de confianza: **AWS service** → **EC2**.
3. En permisos, crea una política en línea (o gestionada) que solo permita lo necesario sobre tu bucket, por ejemplo:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
         "Resource": "arn:aws:s3:::iot-storage-practica-<tu-usuario>/*"
       },
       {
         "Effect": "Allow",
         "Action": ["s3:ListBucket"],
         "Resource": "arn:aws:s3:::iot-storage-practica-<tu-usuario>"
       }
     ]
   }
   ```
4. Nombra el rol, por ejemplo `iot-ec2-s3-role`, y créalo.
5. Ve a **EC2** → selecciona tu instancia → **Acciones** → **Seguridad** → **Modificar rol de IAM** → elige `iot-ec2-s3-role` → **Actualizar rol de IAM**.

Con esto, `boto3` dentro del contenedor obtiene credenciales automáticamente a través del rol de la instancia — **no hace falta configurar `AWS_ACCESS_KEY_ID` ni `AWS_SECRET_ACCESS_KEY`** en ningún lado.

## 3. Variables de entorno de la app

| Variable | Ejemplo | Uso |
|---|---|---|
| `S3_BUCKET` | `iot-storage-practica-<tu-usuario>` | Bucket donde se guardan las lecturas |
| `AWS_REGION` | `us-east-1` | Región del bucket |

## 4. Desplegar el contenedor en la EC2

Dentro de la EC2, ya con el repo clonado y el IAM Role adjunto (ver paso 2):

```bash
cd IoT_Storage/Contenedores/S3
docker build -t flask-s3:1.0 .

docker run -d \
  --name flask-s3 \
  --restart unless-stopped \
  -p 8004:8000 \
  -e S3_BUCKET="iot-storage-practica-<tu-usuario>" \
  -e AWS_REGION="us-east-1" \
  flask-s3:1.0
```

## Verificación

```bash
curl http://<IP_PUBLICA_EC2>:8004/health
# {"status": "ok", "total_lecturas": 0}

curl -X POST http://<IP_PUBLICA_EC2>:8004/datos \
  -H "Content-Type: application/json" \
  -d '{"origen":"iot","temperatura":24.1,"humedad":55}'
# 201 Created

curl http://<IP_PUBLICA_EC2>:8004/datos
```

También puedes ver los objetos directamente en la consola de S3, dentro del prefijo `lecturas/`. Panel web: `http://<IP_PUBLICA_EC2>:8004/`.

## Administración y diagnóstico

| Comando | Uso |
|---|---|
| `docker ps` | Ver que `flask-s3` esté corriendo |
| `docker logs -f flask-s3` | Logs en vivo |
| `docker restart flask-s3` | Reiniciar el contenedor |
| `docker rm -f flask-s3` | Detener y eliminar el contenedor |

## Actualizar el proyecto desde GitHub

```bash
git pull
docker stop flask-s3 && docker rm flask-s3
docker build -t flask-s3:1.1 .
docker run -d --name flask-s3 --restart unless-stopped -p 8004:8000 \
  -e S3_BUCKET="..." -e AWS_REGION="..." \
  flask-s3:1.1
```

Los datos no se pierden porque viven como objetos en el bucket, fuera del contenedor.

## Flujo de comunicación

```
LilyGO T-Beam / curl
        |  POST JSON
        v
EC2 :8004 -> contenedor flask-s3 (Flask + Gunicorn)
        |  put_object (credenciales via IAM Role de la instancia)
        v
AWS S3 -> bucket, prefijo lecturas/<timestamp>_<origen>.json
        |
        v
panel web GET /  (mismo host:8004, lista y lee los objetos)
```

## Notas de seguridad para la práctica

- El bucket se mantiene **privado**; nunca se activó acceso público. Todo el acceso pasa por la API de S3 con las credenciales temporales del IAM Role.
- El IAM Role solo tiene permisos sobre ese bucket específico (principio de mínimo privilegio), no `AdministratorAccess` ni `s3:*` sobre todos los buckets de la cuenta.
- `DELETE /datos` sigue sin autenticación, igual que en los otros puntos — solo válido para la práctica.
