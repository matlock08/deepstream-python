import gi
import sys
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import logging

logger = logging.getLogger('ds')

class BusHandler:

    def bus_call(bus, message, loop):
        t = message.type

        if t == Gst.MessageType.EOS:
            logger.error("End-of-stream")
            loop.quit()
        elif t==Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logger.warning(" %s: %s" % (err, debug))
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(" %s: %s" % (err, debug))
            loop.quit()

        return True
