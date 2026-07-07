import json
import paho.mqtt.client as mqtt
from flask import Flask, render_template
from flask_socketio import SocketIO

# ---------------- MQTT CONFIG ----------------
BROKER = "localhost"
PORT = 1883

SENSOR_TOPIC = "esp32/gateway/temphumsoil"
COMMAND_TOPIC = "esp32/gateway/cmd"

# ---------------- FLASK ----------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ---------------- MQTT CLIENT ----------------
mqtt_client = mqtt.Client(
    client_id="BACKEND_BRAIN",
    protocol=mqtt.MQTTv311,
    clean_session=False
)

subscribed = False


# ---------------- ROUTE ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- NORMALIZATION ----------------
def normalize(value, min_val, max_val):
    return max(0, min(1, (value - min_val) / (max_val - min_val)))


# ---------------- WATER CALCULATION ----------------
def calculate_water(data):
    temp = data["temperature"]
    humidity = data["humidity"]
    soil = data["soil_percent"]
    light = data.get("light", 500)

    M = soil / 100
    D = 1 - M

    Tn = normalize(temp, 10, 45)
    Hn = 1 - normalize(humidity, 20, 100)
    Ln = normalize(light, 0, 1000)

    w1, w2, w3, w4 = 0.4, 0.2, 0.2, 0.2

    WSI = (w1 * D) + (w2 * Tn) + (w3 * Hn) + (w4 * Ln)

    Wbase = 10
    Wdaily = Wbase * (1 + WSI)

    return round(Wdaily, 2), round(WSI, 3)


# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    print("MQTT connect result:", rc)
    if rc == 0:
        print("✅ Connected to MQTT Broker")
    else:
        print("❌ MQTT Connection Failed")


def on_disconnect(client, userdata, rc):
    print("⚠️ Disconnected from MQTT Broker")


def on_subscribe(client, userdata, mid, granted_qos):
    print("📡 Subscription successful. QoS:", granted_qos)


def on_publish(client, userdata, mid):
    print("📤 Message Published. MID:", mid)


def on_message(client, userdata, msg):
    raw_data = msg.payload.decode()
    print("📩 Sensor Data Received:", raw_data)

    try:
        data = json.loads(raw_data)
    except:
        print("❌ Invalid JSON")
        return

    water_time, wsi = calculate_water(data)

    print("🌊 Water Time:", water_time)
    print("📊 WSI:", wsi)

    # Send to Website
    socketio.emit("update", {
        "raw_message": raw_data,
        "water_time": water_time,
        "wsi": wsi
    })

    # Publish Water Command with QoS 2 (Exactly Once)
    command = f"WATER:{water_time}"
    mqtt_client.publish(COMMAND_TOPIC, command, qos=2)
    print("📤 Sent WATER Command with QoS 2")


# Attach Callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_subscribe = on_subscribe
mqtt_client.on_publish = on_publish
mqtt_client.on_message = on_message

mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()


# ---------------- BUTTON HANDLER ----------------
@socketio.on("connect_mqtt")
def handle_connect_mqtt():
    global subscribed

    if not subscribed:
        # Subscribe with QoS 1 (At least once)
        mqtt_client.subscribe(SENSOR_TOPIC, qos=1)
        subscribed = True
        print("📡 Subscribed to Sensor Topic with QoS 1")
        socketio.emit("status", {"message": "Subscribed with QoS 1"})
    else:
        socketio.emit("status", {"message": "Already Subscribed"})


# ---------------- RUN ----------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
