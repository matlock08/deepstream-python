import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import logging
import numpy as np
import pyds
import cv2
import os
import os.path

logger = logging.getLogger('ds')

saved_count = {}

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3

pgie_classes_str = ["Vehicle", "TwoWheeler", "Person", "RoadSign"]
MIN_CONFIDENCE = 0.2
MAX_CONFIDENCE = 1.0

saved_count["stream_0"] = 0
saved_count["stream_1"] = 0

class ImageProbe:

    def __init__(self):
        pass

    # tiler_sink_pad_buffer_probe  will extract metadata received on tiler src pad
    # and update params for drawing rectangle, object information etc.
    def tiler_sink_pad_buffer_probe( pad, info, u_data):
        logger.debug("tiler_sink_pad_buffer_probe")

        frame_number = 0
        num_rects = 0
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
            is_first_obj = True
            save_image = False
            frame_copy = None
            obj_counter = {
                PGIE_CLASS_ID_VEHICLE: 0,
                PGIE_CLASS_ID_PERSON: 0,
                PGIE_CLASS_ID_BICYCLE: 0,
                PGIE_CLASS_ID_ROADSIGN: 0
            }
            while l_obj is not None:
                try:
                    # Casting l_obj.data to pyds.NvDsObjectMeta
                    obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break
                obj_counter[obj_meta.class_id] += 1
                # Periodically check for objects with borderline confidence value that may be false positive detections.
                # If such detections are found, annotate the frame with bboxes and confidence value.
                # Save the annotated frame to file.
                
                if saved_count["stream_{}".format(frame_meta.pad_index)] % 30 == 0 and (
                        MIN_CONFIDENCE < obj_meta.confidence < MAX_CONFIDENCE):
                    if is_first_obj:
                        is_first_obj = False

                        # TODO Checa aqui por que truna al acar la imagen
                        logger.info("Class: %s Confidence: %f " ,pgie_classes_str[obj_meta.class_id],obj_meta.confidence)
                        # Getting Image data using nvbufsurface
                        # the input should be address of buffer and batch_id
                        n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                        n_frame = draw_bounding_boxes(n_frame, obj_meta, obj_meta.confidence)
                        # convert python array into numpy array format in the copy mode.
                        frame_copy = np.array(n_frame, copy=True, order='C')
                        # convert the array into cv2 default color format
                        frame_copy = cv2.cvtColor(frame_copy, cv2.COLOR_RGBA2BGRA)


                    save_image = True

                try:
                    l_obj = l_obj.next
                except StopIteration:
                    break

            #print("Source=", frame_meta.pad_index, "Frame Number=", frame_number, "Number of Objects=", num_rects, "Vehicle_count=",
            #      obj_counter[PGIE_CLASS_ID_VEHICLE], "Person_count=", obj_counter[PGIE_CLASS_ID_PERSON])
            
            
            if save_image:
                img_path = "{}/stream_{}/frame_{}.jpg".format('/opt/nvidia/deepstream/deepstream/sources/python/apps', frame_meta.pad_index, frame_number)
                logger.debug("Saving image to {}".format(img_path))
                if not cv2.imwrite(img_path, frame_copy):
                    logger.error("Failed to save image {}".format(img_path))
            saved_count["stream_{}".format(frame_meta.pad_index)] += 1
            
            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        
        return Gst.PadProbeReturn.OK


    def draw_bounding_boxes(image, obj_meta, confidence):
        confidence = '{0:.2f}'.format(confidence)
        rect_params = obj_meta.rect_params
        top = int(rect_params.top)
        left = int(rect_params.left)
        width = int(rect_params.width)
        height = int(rect_params.height)
        obj_name = pgie_classes_str[obj_meta.class_id]
        # image = cv2.rectangle(image, (left, top), (left + width, top + height), (0, 0, 255, 0), 2, cv2.LINE_4)
        color = (0, 0, 255, 0)
        w_percents = int(width * 0.05) if width > 100 else int(width * 0.1)
        h_percents = int(height * 0.05) if height > 100 else int(height * 0.1)
        linetop_c1 = (left + w_percents, top)
        linetop_c2 = (left + width - w_percents, top)
        image = cv2.line(image, linetop_c1, linetop_c2, color, 6)
        linebot_c1 = (left + w_percents, top + height)
        linebot_c2 = (left + width - w_percents, top + height)
        image = cv2.line(image, linebot_c1, linebot_c2, color, 6)
        lineleft_c1 = (left, top + h_percents)
        lineleft_c2 = (left, top + height - h_percents)
        image = cv2.line(image, lineleft_c1, lineleft_c2, color, 6)
        lineright_c1 = (left + width, top + h_percents)
        lineright_c2 = (left + width, top + height - h_percents)
        image = cv2.line(image, lineright_c1, lineright_c2, color, 6)
        # Note that on some systems cv2.putText erroneously draws horizontal lines across the image
        image = cv2.putText(image, obj_name + ',C=' + str(confidence), (left - 10, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 0, 255, 0), 2)
        return image