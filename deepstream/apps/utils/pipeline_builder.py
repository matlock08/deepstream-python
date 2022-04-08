"""Pipeline Builder it creates a gstreammer pipeline based on nvidia deepstream 6.
    
                                 l-- queue -- valve --nvinfer --| 
                                 l                              |
    camera srcs -- streammux -- tee                           funnel -- nvvideoconvert -- capsfilter -- nvmultistreamtiler -- nvvideoconvert -- nvosd -- nveglglessink
                                 l                              |
                                 l-- queue -- valve ------------|

    ...

    Attributes
    ----------
    sources : str[]
        String array of rtsp uri of cameras
    TILED_OUTPUT_WIDTH : str
        Tiled width (default: '1280')
    TILED_OUTPUT_HEIGHT : str
        Tiled heaight (default: '720')
    PGIE_CONFIG_FILE : str
        Configuration file for pgie (default dstest_pgie_config.txt)

    Methods
    -------
    build()
        Creates the pipeline elements from the sources

"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import math
import logging
import pyds

logger = logging.getLogger('ds')

class PipelineBuilder:
    
    def __init__(self, sources , TILED_OUTPUT_WIDTH : int = 1280, TILED_OUTPUT_HEIGHT : int = 720, PGIE_CONFIG_FILE :str = "dstest_pgie_config.txt"):
        """
        Initializes the builder
        Arguments:
            sources: str[] - String array of rtsp uri of cameras
            TILED_OUTPUT_WIDTH: int - Tiled width (default: 1280)
            TILED_OUTPUT_HEIGHT: int - Tiled heaight (default: 720)
            PGIE_CONFIG_FILE: str - Configuration file for pgie (default dstest_pgie_config.txt)
        """
        self.inferenceEnabled = True
        self.PGIE_CONFIG_FILE = PGIE_CONFIG_FILE
        self.TILED_OUTPUT_WIDTH = TILED_OUTPUT_WIDTH
        self.TILED_OUTPUT_HEIGHT = TILED_OUTPUT_HEIGHT
        self.OSD_PROCESS_MODE = 0
        self.OSD_DISPLAY_TEXT = 0
        self.sources = sources
        self.mem_type = int(pyds.NVBUF_MEM_CUDA_UNIFIED)
        

    def build(self, displaySync : bool = True, probeCallback : any = None):
        """
        Creates the pipeline elements from the sources
        Returns:
            pipeline: GstPipeline  
        """

        logger.info("Building Pipeline...")

        pipeline, streammux = self.build_pipeline_source()

        pipeline, pgie, valveNotInfer = self.build_pipeline_flows(pipeline, streammux)

        pipeline = self.build_pipeline_sync(pipeline, displaySync, pgie, valveNotInfer, probeCallback)

        logger.info("Builded Pipeline...")
        return pipeline

    def build_pipeline_source(self):
        """
        Utility to create the pipeline elements from the sources
        Returns:
            pipeline: GstPipeline  
            streammux: Gst-streammux          
        """

        logger.info("Building Pipeline Source...")

        # Standard GStreamer initialization
        GObject.threads_init()
        Gst.init(None)
        

        logger.debug("Creating Pipeline")
        pipeline = Gst.Pipeline()
        
        if not pipeline:
            raise Exception("Unable to create Pipeline")

        is_live = False    
        
        logger.debug("Creating streamux")
        streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
        streammux.set_property('width', 1920)
        streammux.set_property('height', 1080)
        streammux.set_property('batch-size', len(self.sources))
        streammux.set_property('batched-push-timeout', 4000000)
        streammux.set_property('live-source', 1)
        streammux.set_property("nvbuf-memory-type", self.mem_type)

        if not streammux:
            raise Exception("Unable to create NvStreamMux")

        pipeline.add(streammux)

        for i in range(len(self.sources)):
            logger.debug("Creating source_bin %d", i)
            uri_name = self.sources[i]
            if uri_name.find("rtsp://") == 0 :
                is_live = True
            source_bin = self.create_source_bin(i, uri_name)
            if not source_bin:
                raise Exception("Unable to create source bin")

            pipeline.add(source_bin)
            padname = "sink_%u" %i
            sinkpad = streammux.get_request_pad(padname) 
            if not sinkpad:
                raise Exception("Unable to create sink pad bin")

            srcpad = source_bin.get_static_pad("src")
            if not srcpad:
                raise Exception("Unable to create src pad bin")

            srcpad.link(sinkpad)
        
        return pipeline, streammux


    def build_pipeline_flows(self, pipeline, streammux):
        """
        Attach to the pipeline elements to enable 2 flows of data.
        Arguments:
            pipeline: GstPipeline
            streammux: Gst-streammux 
        Returns:
            pipeline: GstPipeline  
            endflow1: GstElement
            endflow2: GstElement
        """

        logger.debug("Creating tee")
        tee = Gst.ElementFactory.make("tee", "tee")
        if not tee:
            raise Exception("Unable to create tee")

        logger.debug("Creating queueInference")
        queueInference = Gst.ElementFactory.make("queue","queueInference")
        if not queueInference:
            raise Exception("Unable to create queueInference")

        logger.debug("Creating Pgie")
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        if not pgie:
            raise Exception("Unable to create pgie")

        pgie.set_property('config-file-path', self.PGIE_CONFIG_FILE)

        logger.debug("Creating queueWithoutInference")
        queueWithoutInference = Gst.ElementFactory.make("queue","queueWithoutInference")
        if not queueWithoutInference:
            raise Exception("Unable to create queueWithoutInference")

        logger.debug("Creating valveInfer")
        valveInfer = Gst.ElementFactory.make("valve", "valveInfer")
        if not valveInfer:
            raise Exception("Unable to create valveInfer")

        valveInfer.set_property("drop", not self.inferenceEnabled)


        logger.debug("Creating valveNotInfer")
        valveNotInfer = Gst.ElementFactory.make("valve", "valveNotInfer")
        if not valveNotInfer:
            raise Exception("Unable to create valveNotInfer")

        valveNotInfer.set_property("drop", self.inferenceEnabled )
        

        logger.debug("Adding elements to Pipeline")
        pipeline.add(tee)
        pipeline.add(queueInference)        
        pipeline.add(valveInfer)
        pipeline.add(pgie)

        pipeline.add(queueWithoutInference)
        pipeline.add(valveNotInfer)


        logger.debug("Linking elements of Pipeline")
        streammux.link(tee)
        tee.link(queueInference)
        tee.link(queueWithoutInference)

        queueInference.link(valveInfer)
        valveInfer.link(pgie)

        queueWithoutInference.link(valveNotInfer)
        
        return pipeline, pgie, valveNotInfer


    def build_pipeline_sync(self, pipeline, displaySync,  endFlow1, endFlow2, probeCallback ):
        """
        Attach to the pipeline sync elements form the 2 flows
        Arguments:
            pipeline: GstPipeline
            endFlow1: GstElement - the end of the first flow
            endFlow2: GstElement - the end of the second flow
        Returns:
            pipeline: GstPipeline              
        """

        logger.debug("Creating funnel")
        funnel = Gst.ElementFactory.make("funnel","funnel")
        if not funnel:
            raise Exception("Unable to create funnel")
        

        logger.debug("Creating nvvideoconvert")
        nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
        if not nvvidconv1:
            raise Exception("Unable to create nvvideoconvert1")
        nvvidconv1.set_property("nvbuf-memory-type", self.mem_type)

        logger.debug("Creating caps")
        caps1 = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA")
        filter1 = Gst.ElementFactory.make("capsfilter", "filter1")
        if not filter1 or not caps1:
            raise Exception("Unable to create caps filter")

        filter1.set_property("caps", caps1)

        logger.debug("Creating tiler")
        tiler = Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
        if not tiler:
            raise Exception("Unable to create tiler")
        tiler.set_property("nvbuf-memory-type", self.mem_type)

        tiler_rows = int(math.sqrt(len(self.sources)))
        tiler_columns = int(math.ceil((1.0*len(self.sources))/tiler_rows))
        tiler.set_property("rows",tiler_rows)
        tiler.set_property("columns",tiler_columns)
        tiler.set_property("width", self.TILED_OUTPUT_WIDTH)
        tiler.set_property("height", self.TILED_OUTPUT_HEIGHT)

        logger.debug("Creating nvvideoconvert")
        nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
        if not nvvidconv:
            raise Exception("Unable to create nvvidconv2")
        nvvidconv.set_property("nvbuf-memory-type", self.mem_type) 

        logger.debug("Creating nvosd")
        nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        if not nvosd:
            raise Exception("Unable to create nvosd")
            
        nvosd.set_property('process-mode', self.OSD_PROCESS_MODE)
        nvosd.set_property('display-text', self.OSD_DISPLAY_TEXT)

        logger.debug("Creating nveglglessink")
        if displaySync:
            sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
        else:
            sink = Gst.ElementFactory.make("fakesink", "nvvideo-renderer")

        if not sink:
            raise Exception("Unable to create nveglglessink")
            
        if displaySync:
            sink.set_property("sync",0)
            sink.set_property("qos",0)

        
        logger.debug("Adding elements to Pipeline")
        pipeline.add(funnel)  
        pipeline.add(tiler)
        pipeline.add(nvvidconv)     
        pipeline.add(filter1)
        pipeline.add(nvvidconv1)         
        pipeline.add(nvosd)
        pipeline.add(sink)


        logger.debug("Linking elements of Pipeline")
        endFlow1.link(funnel)
        endFlow2.link(funnel)
        funnel.link(nvvidconv1)
        nvvidconv1.link(filter1)
        filter1.link(tiler)        
        tiler.link(nvvidconv)
        nvvidconv.link(nvosd)
        nvosd.link(sink) 
        

        if probeCallback:
            # Add Probe to get access to image from the pipeline
            tiler_sink_pad = tiler.get_static_pad("sink")
            if not tiler_sink_pad:
                raise Exception("Unable to get tiler_sink_pad src pad")
            else:
                tiler_sink_pad.add_probe(Gst.PadProbeType.BUFFER, probeCallback, 0)
        
        return pipeline

    def cb_newpad(self, decodebin, decoder_src_pad, data):
        """
        Callback called when a new pad is created on the decoder sink pad.
        Arguments:
            decodebin: GstElement
            decoder_src_pad: GstPAd
            data: gpointer
        """

        logger.debug("In cb_newpad")
        caps = decoder_src_pad.get_current_caps()
        gststruct = caps.get_structure(0)
        gstname = gststruct.get_name()
        source_bin = data
        features = caps.get_features(0)

        # Need to check if the pad created by the decodebin is for video and not
        # audio.
        logger.debug("gstname = %s",gstname)
        if(gstname.find("video")!=-1):
            # Link the decodebin pad only if decodebin has picked nvidia
            # decoder plugin nvdec_*. We do this by checking if the pad caps contain
            # NVMM memory features.
            logger.debug("features = %s",features)
            if features.contains("memory:NVMM"):
                # Get the source bin ghost pad
                bin_ghost_pad=source_bin.get_static_pad("src")
                if not bin_ghost_pad.set_target(decoder_src_pad):
                    raise Exception("Failed to link decoder src pad to source bin ghost pad")
            else:
                raise Exception("Error: Decodebin did not pick nvidia decoder plugin.")

    def decodebin_child_added(self, child_proxy, Object, name, user_data):
        """
        Callback called when a new child is added on the decoder sink pad.
        Arguments:
            child_proxy: 
            Object: 
            name: 
            user_data:
        """
        logger.debug("Decodebin child added: %s", name)
        if(name.find("decodebin") != -1):
            Object.connect("child-added",self.decodebin_child_added,user_data)

        if "source" in name:
            Object.set_property("drop-on-latency", True)


    def create_source_bin(self, index, uri):
        """
        Create a source GstBin to abstract this bin's content from the rest of the pipeline
        Arguments:
            index: an integer
            uri: a string
        Returns:
            The GstBin created
        """
        
        # Create a source GstBin to abstract this bin's content from the rest of the
        # pipeline
        bin_name="source-bin-%02d" %index
        #print(bin_name)
        nbin = Gst.Bin.new(bin_name)
        if not nbin:
            raise Exception("Unable to create source bin")

        # Source element for reading from the uri.
        # We will use decodebin and let it figure out the container format of the
        # stream and the codec and plug the appropriate demux and decode plugins.
        uri_decode_bin = Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
        if not uri_decode_bin:
            raise Exception("Unable to create uri decode bin")
        # We set the input uri to the source element
        uri_decode_bin.set_property("uri",uri)
        # Connect to the "pad-added" signal of the decodebin which generates a
        # callback once a new pad for raw data has beed created by the decodebin
        uri_decode_bin.connect("pad-added",self.cb_newpad,nbin)
        uri_decode_bin.connect("child-added",self.decodebin_child_added,nbin)

        # We need to create a ghost pad for the source bin which will act as a proxy
        # for the video decoder src pad. The ghost pad will not have a target right
        # now. Once the decode bin creates the video decoder and generates the
        # cb_newpad callback, we will set the ghost pad target to the video decoder
        # src pad.
        Gst.Bin.add(nbin,uri_decode_bin)
        bin_pad = nbin.add_pad(Gst.GhostPad.new_no_target("src",Gst.PadDirection.SRC))
        if not bin_pad:
            raise Exception("Failed to add ghost pad in source bin")
            return None
            
        return nbin

    