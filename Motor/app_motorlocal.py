import flask
import mysql.connector
from mysql.connector import Error

app = flask.Flask(__name__)

@app.route('/')
def home():
    return 'pagina principal del distribuidor'

@app.route('/borrardb')
def borrardb():
    try:
     con = mysql.connector.connect(host='localhost',database='data',user='mariajose',password='majopollito')
     print(con.is_connected())
     if con.is_connected():
        cur = con.cursor()
        cur.execute("USE data;")
        print("conectado a la base de datos")
        cur.execute("DROP TABLE IF EXISTS datossensor;")
        print("borro la base de datos")
        cur.execute("CREATE TABLE datossensor (idsensor NUMERIC, timestamp DATETIME, temperatura NUMERIC, humedad NUMERIC, luz NUMERIC, latitud NUMERIC, longitud NUMERIC, altura NUMERIC);")
        print("crea la tabla nueva")
        cur.close()
        con.commit()
        con.close()
    except Error as e:
     print('Error de conexion: ',e)
    return 'creando la tabla de la base de datos'

@app.route('/send_data', methods=['POST'])
def sensor_send():
    values = flask.request.data
    print(values)

    idsensor_t = str(17091)
    temperatura_t = str(23.4)
    humedad_t = str(67.4)
    luz_t = str(1550)
    latitud_t = str(6.24)
    longitud_t = str(-75.4)
    altura_t = str(1550)
    hash_t = "0xab234ccb32112b"
    try:
     con = mysql.connector.connect(host='localhost', database='data', user='mariajose', password='majopollito')
     if con.is_connected():
       cur = con.cursor()
       cur.execute("USE data;")
       cur.execute("INSERT INTO datossensor VALUES(" + idsensor_t  + "," + "NOW()," + temperatura_t + "," + humedad_t + "," + luz_t + "," + latitud_t + "," + longitud_t + "," + altura_t + ");")
       cur.close()
       con.commit()
       con.close()
    except Error as e:
     print("Error con: ", e)
    return "ok",201

if __name__ == '__main__':
        app.run(debug=True,host='0.0.0.0',port=80)
