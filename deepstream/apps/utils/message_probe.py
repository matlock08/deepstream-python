import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import logging
import pyds
import json

logger = logging.getLogger('ds')

class MessageProbe:

    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        


    def process_buffer_probe(self, pad, info, u_data):
        frame_number=0
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            logger.error("Unable to get GstBuffer ")
            return

        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list

        objects_classes_msg = []

        while l_frame is not None:
            try:
                # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
                # The casting is done by pyds.NvDsFrameMeta.cast()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone.
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break

            frame_number = frame_meta.frame_num
            l_obj = frame_meta.obj_meta_list
            
            
            while l_obj is not None:
                try: 
                    # Casting l_obj.data to pyds.NvDsObjectMeta
                    obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break
                
                logger.debug( "stream_id: %d Frame: %d class_id: %d label: %s trackid: %d ", frame_meta.pad_index, frame_number, obj_meta.class_id, obj_meta.obj_label, obj_meta.object_id )

                c_list = obj_meta.classifier_meta_list # Second GIE
                attributes_msg = []
                # This will only be available if secondary GIE was run
                while c_list is not None:
                    try: 
                        # Casting c_list.data to pyds.NvDsClassifierMeta
                        class_meta=pyds.NvDsClassifierMeta.cast(c_list.data)
                        label_meta_list = class_meta.label_info_list

                        while label_meta_list is not None:
                            try:
                                # Casting class_meta.label_info_list.data to pyds.NvDsLabelInfo
                                label_info=pyds.NvDsLabelInfo.cast(label_meta_list.data)

                                attributes_msg.append( { "label_id": label_info.label_id, "result_label": label_info.result_label, "result_prob": label_info.result_prob } )
                            except StopIteration:
                                break
                            
                            label_meta_list = label_meta_list.next


                        c_list=c_list.next
                    except StopIteration:
                        break

                objects_classes_msg.append ( { "stream_id": frame_meta.pad_index, "object_id": obj_meta.object_id, "class_id": obj_meta.class_id, "label": obj_meta.obj_label, "confidence": obj_meta.confidence, "frame_number": frame_number, "attributes": attributes_msg } )

                try: 
                    l_obj=l_obj.next
                except StopIteration:
                    break
            
            
            try:
                l_frame=l_frame.next
            except StopIteration:
                break

        # All the Frames, containing, all their objects , all their attributes
        if frame_number % 30 == 0:
            logger.info( json.dumps(objects_classes_msg) )
            
        if frame_number % 30 == 0 and self.mqtt_client and len(objects_classes_msg) > 0:
            self.mqtt_client.publish('/deepstream/message', json.dumps(objects_classes_msg))

        return Gst.PadProbeReturn.OK