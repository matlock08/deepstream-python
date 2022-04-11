#!/usr/bin/env python3

import sys
sys.path.append('.')
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

import json
import logging
import logging.config

logging.config.fileConfig('log.conf')
logger = logging.getLogger('ds')

import utils.pipeline_builder as pb
import utils.bus_call as bc
import utils.mqtt_handler as mh
import utils.image_probe as ip
import utils.message_probe as mp


def main(args):
    # Get sources from ENV Variable from Docker
    sources = os.environ.get("STREAMS").split(" ")
    mqtt_broker = os.environ.get("MQTT_BROKER")
    mqtt_port = int(os.environ.get("MQTT_PORT"))
    mqtt_topic_command = os.environ.get("MQTT_TOPIC_COMMAND") 
    mqtt_topic_messages = os.environ.get("MQTT_TOPIC_MESSAGES") 

    #MQTT Message Callback
    def on_mqtt_message(client, userdata, msg):
        nonlocal pipeline, valveInfer, valveNotInfer
        logger.debug(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        data = json.loads(msg.payload.decode())

        if 'command' in data:
            if data['command'] == 'play':
                pipeline.set_state(Gst.State.PLAYING) 
            elif data['command'] == 'stop':
                pipeline.set_state(Gst.State.STOPPED)
            elif data['command'] == 'pause':
                pipeline.set_state(Gst.State.PAUSED) 

        if 'inference' in data:
            if data['inference'] == 'enable':
                valveInfer.set_property("drop", False)
                valveNotInfer.set_property("drop", True)
            elif data['inference'] == 'disable':
                valveInfer.set_property("drop", True)
                valveNotInfer.set_property("drop", False)

    # MQTT Handler   
    mqttHandler = mh.MQTTHandler(mqtt_broker, mqtt_port, mqtt_topic_command)    
    mqttClient = mqttHandler.connect_mqtt(on_mqtt_message)
    
    # Utility class to build the pipeline
    pipe = pb.PipelineBuilder(sources)
    # Visualize true and no probe
    #pipeline = pipe.build() # Default pipeline visualize true no probe 
    
    # Sample probe Visualize true and Save image every 30 frames
    #ipi = ip.ImageProbe('/tmp')
    #pipeline, valveInfer, valveNotInfer = pipe.build(True , ipi.process_buffer_probe )  

    # Sample probe Visualize true and Send json message every 30 frames 
    mpi = mp.MessageProbe(mqttClient, mqtt_topic_messages)
    pipeline, valveInfer, valveNotInfer = pipe.build(True , mpi.process_buffer_probe ) 
        
    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bc.BusHandler.bus_call , loop)
    
    
    logger.info("Starting pipeline...")
    # start play back and listed to events		
    pipeline.set_state(Gst.State.PLAYING)
    logger.info("Started pipeline...")

    # Start MQTT client    
    mqttClient.loop_start()

    try:
        loop.run()                
    except Exception as err:
        logger.error("Error Type " + type(err))    # the exception instance
        logger.error(err.args)     # arguments stored in .args
        pass
    # cleanup
    logger.info("Exiting app\n")
    pipeline.set_state(Gst.State.NULL)




if __name__ == '__main__':
    sys.exit(main(sys.argv))


