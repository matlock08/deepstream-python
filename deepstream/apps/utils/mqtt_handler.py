
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
import random
import json
from paho.mqtt import client as mqtt_client
import logging

logger = logging.getLogger('ds')

class MQTTHandler:

    def __init__(self, pipeline: GObject,  broker: str="mqtt", port: int=1883, topic: str="/deepstream/command", client_id: str=f'python-mqtt-{random.randint(0, 1000)}'):
        self.pipeline = pipeline
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client_id = client_id
        self.enabledInference = False

    def connect_mqtt(self):
        logger.debug("MQTT Connecting!!!!!")
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("MQTT Connected!!!!!")
            else:
                logger.error("Failed to connect, return code %d", rc)
        # Set Connecting Client ID
        client = mqtt_client.Client(self.client_id)
        #client.username_pw_set(username, password)
        client.on_connect = on_connect
        client.connect(self.broker, self.port)
        return client

    def subscribe(self, client: mqtt_client):

        def on_message(client, userdata, msg):
            logger.debug(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            data = json.loads(msg.payload.decode())

            if 'command' in data:
                if data['command'] == 'play':
                    self.pipeline.set_state(Gst.State.PLAYING) 
                elif data['command'] == 'stop':
                    self.pipeline.set_state(Gst.State.STOPPED)
                elif data['command'] == 'pause':
                    self.pipeline.set_state(Gst.State.PAUSED) 

            if 'inference' in data:
                if data['inference'] == 'enable':
                    self.enabledInference = True
                elif data['inference'] == 'disable':
                    self.enabledInference = False
            
            # logger.debug("Enable inference = %s", enabledInference)
            

        client.subscribe(self.topic)
        client.on_message = on_message