FROM nvcr.io/nvidia/deepstream:6.0.1-devel

# WORKDIR /opt/deepstream

# #RUN apt-get -y update
RUN apt-get -y install \
libssl1.0.0 \
libgstreamer1.0-0 \
gstreamer1.0-tools \
gstreamer1.0-plugins-good \
gstreamer1.0-plugins-bad \
gstreamer1.0-plugins-ugly \
gstreamer1.0-libav \
libgstrtspserver-1.0-0 \
libjansson4=2.11-1

WORKDIR /opt/tmp

RUN apt-get -y install python-gi-dev
RUN export GST_LIBS="-lgstreamer-1.0 -lgobject-2.0 -lglib-2.0"
RUN export GST_CFLAGS="-pthread -I/usr/include/gstreamer-1.0 -I/usr/include/glib-2.0 -I/usr/lib/x86_64-linux-gnu/glib-2.0/include"
RUN git clone https://github.com/GStreamer/gst-python.git
RUN cd gst-python \
    git checkout 1a8f48a \
    ./autogen.sh PYTHON=python3 \
    ./configure PYTHON=python3 \
    make \
    make install

RUN wget https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/releases/download/v1.1.1/pyds-1.1.1-py3-none-linux_x86_64.whl \
     && pip3 install pyds-1.1.1-py3-none-linux_x86_64.whl \
     && rm pyds-1.1.1-py3-none-linux_x86_64.whl

WORKDIR /opt/nvidia/deepstream/deepstream/sources

RUN git clone https://github.com/NVIDIA-AI-IOT/deepstream_python_apps

RUN apt-get install -y librdkafka1=0.11.3-1build1
RUN pip3 install kafka-python

ADD apps /opt/nvidia/deepstream/deepstream/sources/python/apps

WORKDIR /opt/nvidia/deepstream/deepstream/sources/python/apps/deepstream/

#CMD ["bash"]
#ENTRYPOINT python3 deepstream_test_3.py "$STREAM0" "$STREAM1"
#ENTRYPOINT python3 deepstream_test_1.py ../../../../samples/streams/sample_720p.h264
ENTRYPOINT GST_DEBUG=3 python3 deepstream_kafka.py "$STREAM0" "$STREAM1" 
