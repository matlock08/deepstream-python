
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
import random
from paho.mqtt import client as mqtt_client
import logging

logger = logging.getLogger('ds')

class MQTTHandler:

    def __init__(self, broker: str="mqtt", port: int=1883, topic: str="/deepstream/command", client_id: str=f'python-mqtt-{random.randint(0, 1000)}'):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client_id = client_id
        self.enabledInference = False

    def connect_mqtt(self, on_message_callback=None):
        logger.debug("MQTT Connecting!!!!!")
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("MQTT Connected!!!!!")
                client.subscribe(self.topic)
            else:
                logger.error("Failed to connect, return code %d", rc)
        # Set Connecting Client ID
        self.client = mqtt_client.Client(self.client_id)
        #client.username_pw_set(username, password)
        self.client.on_connect = on_connect
        self.client.connect(self.broker, self.port)        
        self.client.on_message = on_message_callback
        return self.client

    

        
