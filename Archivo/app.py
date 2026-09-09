import os
import time
import json
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datos.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lecturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            origen TEXT NOT NULL,
            payload TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>:: CYBERDECK IOT ::</title>
<style>
* { box-sizing: border-box; }
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&display=swap');
body {
    font-family: 'Rajdhani', 'Courier New', monospace;
    background: radial-gradient(ellipse at top, #2a0808 0%, #0a0303 55%, #000000 100%);
    color: #e8f7f7;
    margin: 0;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 40px 16px;
}
.card {
    background: linear-gradient(180deg, #170606 0%, #0d0404 100%);
    border: 1px solid #4a1414;
    padding: 26px;
    width: 100%;
    max-width: 560px;
    position: relative;
    clip-path: polygon(0 12px, 12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
    box-shadow: 0 0 30px rgba(255,0,60,0.15), inset 0 0 40px rgba(0,0,0,0.5);
}
.top-bar {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid #4a1414; padding-bottom: 10px; margin-bottom: 18px;
}
h1 {
    font-size: 19px; margin: 0; color: #4fe8e0; letter-spacing: 2px;
    text-transform: uppercase; text-shadow: 0 0 8px rgba(79,232,224,0.5);
}
.subtitle { color: #a34848; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; margin: 2px 0 0; }
.tag-live { font-size: 10px; color: #ff3860; border: 1px solid #ff3860; padding: 3px 8px; letter-spacing: 1px; animation: blink 1.5s infinite; }
@keyframes blink { 50% { opacity: 0.4; } }

.mode-row {
    display: flex; align-items: center; justify-content: space-between;
    background: #1a0808; border: 1px solid #3a1010; padding: 12px 16px; margin-bottom: 18px;
    clip-path: polygon(8px 0, 100% 0, 100% 100%, 0 100%, 0 8px);
}
.mode-label { font-size: 12px; color: #d99; letter-spacing: 0.5px; text-transform: uppercase; }

.switch { position: relative; display: inline-block; width: 46px; height: 22px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider-toggle {
    position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
    background-color: #2a0e0e; transition: 0.25s; border: 1px solid #5a1a1a;
}
.slider-toggle:before {
    position: absolute; content: ""; height: 16px; width: 16px;
    left: 2px; bottom: 2px; background-color: #6a3030; transition: 0.25s;
}
input:checked + .slider-toggle { background-color: #052e2c; border-color: #4fe8e0; }
input:checked + .slider-toggle:before { transform: translateX(22px); background-color: #4fe8e0; }

#panelManual { display: none; margin-bottom: 18px; }
#panelManual.visible { display: block; }
#panelManual input[type=text] {
    width: 100%; padding: 10px 12px; border: 1px solid #3a1010;
    background: #0a0303; color: #4fe8e0; font-family: 'Rajdhani', monospace;
    font-size: 13px; margin-bottom: 10px; letter-spacing: 0.5px;
}
#panelManual input[type=text]:focus { outline: none; border-color: #4fe8e0; }
#panelManual button, .btn-cyber {
    width: 100%; padding: 10px; border: 1px solid #4fe8e0;
    background: transparent; color: #4fe8e0; font-weight: 700; font-family: 'Rajdhani', monospace;
    cursor: pointer; font-size: 13px; letter-spacing: 1px; text-transform: uppercase;
    clip-path: polygon(8px 0, 100% 0, 100% 100%, 0 100%, 0 8px); transition: 0.15s;
}
#panelManual button:hover { background: #4fe8e0; color: #050505; box-shadow: 0 0 14px rgba(79,232,224,0.6); }

.btn-danger {
    border-color: #ff3860; color: #ff3860; margin-top: 10px;
}
.btn-danger:hover { background: #ff3860; color: #050505; box-shadow: 0 0 14px rgba(255,56,96,0.6); }

.result-box {
    padding: 14px; background: #150606; border-left: 3px solid #4fe8e0; margin-bottom: 18px;
}
.result-box .label { font-size: 10px; color: #a34848; letter-spacing: 1.5px; text-transform: uppercase; }
.result-box .payload { color: #fff; font-size: 14px; margin: 6px 0; word-break: break-all; }
.result-box .time-ago { color: #4fe8e0; font-size: 12px; }
.result-box .time-full { color: #806060; font-size: 11px; margin-top: 2px; }

.lista-title {
    font-size: 11px; color: #a34848; text-transform: uppercase; letter-spacing: 1.5px;
    margin: 16px 0 8px; display: flex; justify-content: space-between; align-items: center;
}
#listaLecturas { max-height: 240px; overflow-y: auto; border-top: 1px solid #3a1010; padding-top: 8px; }
.item-lectura {
    display: flex; flex-direction: column; gap: 2px;
    font-size: 12px; padding: 8px 0; border-bottom: 1px dashed #2a1010; color: #cbb;
}
.item-lectura .fila-top { display: flex; justify-content: space-between; gap: 8px; }
.item-lectura .origen-manual { color: #ffb000; }
.item-lectura .origen-iot { color: #4fe8e0; }
.item-lectura .fecha-item { font-size: 10px; color: #705050; }
.empty-state { color: #4a3030; font-size: 12px; text-align: center; padding: 12px 0; }

.footer-row {
    margin-top: 18px; display: flex; justify-content: space-between; align-items: center;
    font-size: 11px; color: #705050; border-top: 1px solid #3a1010; padding-top: 12px;
}
code { background: #1a0808; padding: 2px 6px; color: #4fe8e0; }
.link-purgar { color: #ff3860; text-decoration: none; cursor: pointer; letter-spacing: 0.5px; font-size: 11px; text-transform: uppercase; }
.link-purgar:hover { text-shadow: 0 0 6px #ff3860; }
</style>
</head>
<body>
<div class="card">
    <div class="top-bar">
        <div>
            <h1>&gt; CYBERDECK_IOT</h1>
            <p class="subtitle">monitor de senal :: sqlite persistente</p>
        </div>
        <span class="tag-live">LIVE</span>
    </div>

    <div class="mode-row">
        <div class="mode-label">Simular dispositivo IoT</div>
        <label class="switch">
            <input type="checkbox" id="simSwitch" onchange="toggleManual()">
            <span class="slider-toggle"></span>
        </label>
    </div>

    <div id="panelManual">
        <input type="text" id="mensajeManual" placeholder="valor_sensor:temperatura=24.5">
        <button onclick="enviarManual()">&gt;&gt; TRANSMITIR SENAL</button>
    </div>

    <div class="result-box">
        <div class="label">ultima lectura</div>
        <div class="payload" id="ultimaLectura">-- sin datos --</div>
        <div class="time-ago" id="tiempoTranscurrido"></div>
        <div class="time-full" id="fechaCompleta"></div>
    </div>

    <div class="lista-title">
        <span>registro en vivo</span>
        <span class="link-purgar" onclick="purgarDatos()">[ vaciar registro ]</span>
    </div>
    <div id="listaLecturas"><div class="empty-state">esperando datos...</div></div>

    <div class="footer-row">
        <span>total: <code id="totalCount">0</code></span>
        <span>db: <code>datos.db</code></span>
    </div>
</div>

<script>
function toggleManual() {
    const activo = document.getElementById('simSwitch').checked;
    document.getElementById('panelManual').classList.toggle('visible', activo);
}

function enviarManual() {
    const valor = document.getElementById('mensajeManual').value.trim();
    if (!valor) return;
    fetch('/datos', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mensaje: valor, origen: 'manual'})
    }).then(() => {
        document.getElementById('mensajeManual').value = '';
        cargarDatos();
    });
}

function purgarDatos() {
    if (!confirm('Esto eliminara PERMANENTEMENTE todas las lecturas guardadas. Continuar?')) return;
    fetch('/datos', { method: 'DELETE' }).then(() => cargarDatos());
}

function tiempoRelativo(segundos) {
    if (segundos < 5) return 'justo ahora';
    if (segundos < 60) return 'hace ' + Math.floor(segundos) + 's';
    if (segundos < 3600) return 'hace ' + Math.floor(segundos/60) + 'min';
    return 'hace ' + Math.floor(segundos/3600) + 'h';
}

function formatoFecha(epochSeconds) {
    const d = new Date(epochSeconds * 1000);
    return d.toLocaleDateString('es-CO') + ' ' + d.toLocaleTimeString('es-CO');
}

let ultimoTimestamp = null;

function cargarDatos() {
    fetch('/datos').then(r => r.json()).then(data => {
        document.getElementById('totalCount').innerText = data.length;
        const lista = document.getElementById('listaLecturas');

        if (data.length === 0) {
            lista.innerHTML = '<div class="empty-state">esperando datos...</div>';
            document.getElementById('ultimaLectura').innerText = '-- sin datos --';
            document.getElementById('tiempoTranscurrido').innerText = '';
            document.getElementById('fechaCompleta').innerText = '';
            ultimoTimestamp = null;
            return;
        }

        const ultima = data[data.length - 1];
        ultimoTimestamp = ultima.timestamp;
        document.getElementById('ultimaLectura').innerText = JSON.stringify(ultima.payload);
        document.getElementById('fechaCompleta').innerText = formatoFecha(ultima.timestamp);

        const recientes = data.slice(-10).reverse();
        lista.innerHTML = recientes.map(item => {
            const claseOrigen = item.origen === 'manual' ? 'origen-manual' : 'origen-iot';
            return '<div class="item-lectura">' +
                '<div class="fila-top"><span class="' + claseOrigen + '">[' + item.origen + ']</span><span>' + JSON.stringify(item.payload) + '</span></div>' +
                '<span class="fecha-item">' + formatoFecha(item.timestamp) + '</span>' +
                '</div>';
        }).join('');
    });
}

function actualizarTiempo() {
    if (ultimoTimestamp === null) return;
    const segundos = (Date.now()/1000) - ultimoTimestamp;
    document.getElementById('tiempoTranscurrido').innerText = tiempoRelativo(segundos);
}

cargarDatos();
setInterval(cargarDatos, 3000);
setInterval(actualizarTiempo, 1000);
</script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/datos', methods=['GET', 'POST', 'DELETE'])
def datos_iot():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"error": "Se esperaba JSON"}), 400

        origen = data.pop('origen', 'iot')
        timestamp = time.time()
        payload_json = json.dumps(data)

        conn = get_db()
        conn.execute(
            "INSERT INTO lecturas (timestamp, origen, payload) VALUES (?, ?, ?)",
            (timestamp, origen, payload_json)
        )
        conn.commit()
        conn.close()

        app.logger.info(f"[{origen.upper()}] Dato guardado en SQLite: {data}")
        return jsonify({"status": "recibido", "data": {"timestamp": timestamp, "origen": origen, "payload": data}}), 201

    if request.method == 'DELETE':
        conn = get_db()
        conn.execute("DELETE FROM lecturas")
        conn.commit()
        conn.close()
        app.logger.info("Registro de lecturas purgado por el usuario")
        return jsonify({"status": "purgado"}), 200

    conn = get_db()
    filas = conn.execute("SELECT timestamp, origen, payload FROM lecturas ORDER BY id ASC").fetchall()
    conn.close()

    resultado = [
        {"timestamp": f["timestamp"], "origen": f["origen"], "payload": json.loads(f["payload"])}
        for f in filas
    ]
    return jsonify(resultado)


@app.route('/health', methods=['GET'])
def health():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM lecturas").fetchone()["c"]
    conn.close()
    return jsonify({"status": "ok", "total_lecturas": total}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
