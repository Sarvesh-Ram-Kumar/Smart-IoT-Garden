import json
import time
import paho.mqtt.client as mqtt

# -------- MQTT Broker --------
BROKER = "localhost"      # or your PC IP, e.g. 192.168.1.5
PORT = 1883

SENSOR_TOPIC = "garden/sensor/soil"
ACTUATOR_TOPIC = "garden/actuator/sprinkler/cmd"

# -------- On Connect --------
def on_connect(client, userdata, flags, rc):
    print("Backend connected to MQTT broker")
    client.subscribe(SENSOR_TOPIC)

# -------- On Message --------
def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    data = json.loads(payload)

    moisture = data["moisture"]
    print(f"Received moisture: {moisture}%")

    # --- Calculation Logic ---
    if moisture < 30:
        command = {"command": "ON", "duration": 10}
    elif moisture < 50:
        command = {"command": "ON", "duration": 5}
    else:
        command = {"command": "OFF", "duration": 0}

    client.publish(ACTUATOR_TOPIC, json.dumps(command))
    print("Command sent:", command)

# -------- Client Setup --------
client = mqtt.Client("BACKEND_BRAIN")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

# -------- Start Listening --------
client.loop_forever()
