#!/usr/bin/env python3

import sys
sys.path.append('.')
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import random
from paho.mqtt import client as mqtt_client

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
    
    # Using utility class to build the pipeline
    pipe = pb.PipelineBuilder(sources)
    pipeline = pipe.build(True , mp.tiler_sink_pad_buffer_probe )
    #pipeline = pipe.build()
    
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
    mqttHandler = mh.MQTTHandler(pipeline)
    
    mqttClient = mqttHandler.connect_mqtt()
    mqttHandler.subscribe(mqttClient)
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


