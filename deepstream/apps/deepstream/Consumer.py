import threading, time
import json
from kafka import KafkaConsumer
import os

KAFKA_BROKER = os.getenv('KAFKA_BROKER', "localhost")
KAFKA_BROKER_PORT = os.getenv('KAFKA_BROKER_PORT')
SUB_TOPIC = os.getenv('SUB_TOPIC', "ds_meta_msg")

conn_str = KAFKA_BROKER + ":" + KAFKA_BROKER_PORT

class Consumer(threading.Thread):
    def __init__(self, valve):
        self.valve = valve
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()

    def forgiving_json_deserializer(self, v):
        if v is None:
            return None
        try:
            #return json.loads(v.decode('utf-8'))
            return v.decode('utf-8')
        except json.decoder.JSONDecodeError:
            print('Unable to decode: %s', v)
            return None
        

    def stop(self):
        self.stop_event.set()

    def run(self):
        consumer = KafkaConsumer(bootstrap_servers=conn_str,
                                 auto_offset_reset='latest',
                                 enable_auto_commit=True,
                                 consumer_timeout_ms=1000,
                                 value_deserializer=self.forgiving_json_deserializer )
        
        consumer.subscribe([ SUB_TOPIC ])

        while not self.stop_event.is_set():
            for message in consumer:
                if self.stop_event.is_set():
                    break

                if message.value is not None and message.value == "ON":
                    self.valve.set_property("drop",True)
                else:
                    self.valve.set_property("drop",False)

        consumer.close()