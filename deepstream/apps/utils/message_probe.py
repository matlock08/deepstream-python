import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import logging
import pyds

logger = logging.getLogger('ds')


def tiler_sink_pad_buffer_probe(pad, info, u_data):
    frame_number=0
    num_rects=0
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        logger.error("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
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
        num_rects = frame_meta.num_obj_meta
        
        
        while l_obj is not None:
            try: 
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            
            logger.info( "Frame: %d class_id: %d label: %s ",frame_number, obj_meta.class_id, obj_meta.obj_label )

            c_list = obj_meta.classifier_meta_list # Second GIE

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
                            logger.info( "                            label_id: %d", label_info.label_id )
                            logger.info( "                            num_classes: %d", label_info.num_classes )
                            logger.info( "                            result_label: %s", label_info.result_label )
                            logger.info( "                            result_prob: %f", label_info.result_prob )
                        except StopIteration:
                            break
                        class_meta.label_info_list = class_meta.label_info_list.next

                        label_meta_list = label_meta_list.next


                    c_list=c_list.next
                except StopIteration:
                    break

            try: 
                l_obj=l_obj.next
            except StopIteration:
                break
        
        
        try:
            l_frame=l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK