# IoT_Storage

Portafolio de práctica de almacenamiento en la nube para un proyecto IoT (curso 7mo semestre). Un end-device **LilyGO T-Beam** envía lecturas por WiFi hacia una única instancia **AWS EC2**, que corre **4 servidores Flask en paralelo** (cada uno en su propio puerto y su propio contenedor Docker), probando 4 formas distintas de almacenar los mismos datos.

Los 4 servicios comparten exactamente el mismo contrato HTTP:

- `GET /` — panel web de monitoreo (estilo Cyberdeck) con la última lectura y el historial reciente.
- `POST /datos` — recibe un JSON y lo guarda.
- `GET /datos` — devuelve todas las lecturas guardadas.
- `DELETE /datos` — vacía el almacenamiento.
- `GET /health` — chequeo de salud con el total de lecturas.

Cada punto es autocontenido: no hay un dashboard ni un backend compartido entre ellos — para ver los 4 se abren 4 pestañas del navegador, una por puerto.

## Los 4 puntos de la práctica

| # | Técnica de almacenamiento | Carpeta | Puerto EC2 | Guía |
|---|---|---|---|---|
| 1 | Archivo local `.db` (SQLite) | [`Archivo/`](Archivo/) | 80 | [README](Archivo/README.md) |
| 2 | Motor de BD local (MariaDB en su propio contenedor) | [`Motor/MotorLocal/`](Motor/MotorLocal/) | 8002 | [README](Motor/MotorLocal/README.md) |
| 3 | Motor de BD externo (AWS RDS MySQL) | [`Motor/RDS/`](Motor/RDS/) | 8003 | [README](Motor/RDS/README.md) |
| 4 | Almacenamiento de objetos (AWS S3 vía boto3) | [`Contenedores/S3/`](Contenedores/S3/) | 8004 | [README](Contenedores/S3/README.md) |

Todos corren dockerizados con el mismo patrón (Flask + Gunicorn, `EXPOSE 8000` interno) — solo cambia el puerto publicado en el host y el backend de almacenamiento.

## Estructura del repositorio

```text
IoT_Storage/
├── README.md                        # este archivo
├── .gitignore
├── Archivo/                         # Punto 1 — SQLite
├── Motor/
│   ├── MotorLocal/                  # Punto 2 — MariaDB en contenedor local
│   └── RDS/                         # Punto 3 — MySQL en AWS RDS
├── Contenedores/
│   └── S3/                          # Punto 4 — boto3 + S3
└── Sensor/
    └── LiLyGO-Almacenamiento/       # firmware del end-device (PlatformIO)
```

> Nota: `Contenedores/` puede contener también una carpeta de ejemplo dejada por el profesor (stack FIWARE). Esa carpeta se mantiene solo en el disco local para consulta y está excluida del repositorio vía `.gitignore` — no forma parte de la práctica del estudiante.

## Arquitectura general

```text
                         WiFi
LilyGO T-Beam  ------------------------->  Instancia EC2 (una sola IP pública)
(4 URLs, mismo payload)                        |
                                                |-- :80    -> contenedor flask-iot      -> datos.db (SQLite)
                                                |-- :8002  -> contenedor flask-motorlocal -> contenedor mariadb-iot
                                                |-- :8003  -> contenedor flask-rds        -> AWS RDS MySQL (externo)
                                                +-- :8004  -> contenedor flask-s3         -> AWS S3 (bucket)
```

El end-device (`Sensor/LiLyGO-Almacenamiento/src/main.cpp`) envía el mismo heartbeat JSON a las 4 URLs en cada ciclo, para dejar el dato guardado por las 4 vías al mismo tiempo.

## Aprovisionamiento de la instancia EC2 (una sola vez)

Estos pasos se hacen **una sola vez** por instancia EC2, sin importar cuántos de los 4 puntos vayas a correr. Cada README de punto asume que ya hiciste esto y solo documenta lo específico de su backend.

### 1. Crear la instancia EC2

- AMI Ubuntu (LTS reciente), tipo `t2.micro`/`t3.micro` (capa gratuita alcanza para la práctica).
- Crea o reutiliza un par de llaves (`.pem`) para SSH.

### 2. Security Group

Configura un único Security Group para la instancia con estas reglas de entrada:

| Tipo | Protocolo | Puerto | Origen | Para qué punto |
|---|---|---:|---|---|
| SSH | TCP | 22 | Tu IP pública | Administración |
| HTTP | TCP | 80 | `0.0.0.0/0` | Punto 1 — Archivo |
| Custom TCP | TCP | 8002 | `0.0.0.0/0` | Punto 2 — Motor Local |
| Custom TCP | TCP | 8003 | `0.0.0.0/0` | Punto 3 — RDS |
| Custom TCP | TCP | 8004 | `0.0.0.0/0` | Punto 4 — S3 |

(Los puntos 2 y 3 abren además su propio Security Group hacia la base de datos — eso se documenta en cada README específico.)

### 3. Conectarse por SSH

```bash
ssh -i labsuser.pem ubuntu@<IP_PUBLICA_EC2>
```

> En una AMI Ubuntu el usuario por defecto es `ubuntu`; en Amazon Linux normalmente es `ec2-user`.

### 4. Instalar Git y Docker (con plugin de compose)

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu
```

Cierra la sesión y vuelve a entrar por SSH para que el nuevo grupo tome efecto, luego verifica:

```bash
docker --version
docker compose version
docker ps
```

Si antes corriste Flask directo con systemd (sin Docker), libera el puerto que vayas a usar:

```bash
sudo systemctl stop flaskapp
sudo systemctl disable flaskapp
```

### 5. Clonar el repositorio

```bash
cd /home/ubuntu
git clone https://github.com/SVA999/IoT_Storage.git
cd IoT_Storage
```

A partir de aquí, entra a la carpeta del punto que quieras desplegar (`Archivo/`, `Motor/MotorLocal/`, `Motor/RDS/`, `Contenedores/S3/`) y sigue su README específico — ahí solo aparecen las variables de entorno, el build/run del contenedor y la verificación propias de ese backend.
