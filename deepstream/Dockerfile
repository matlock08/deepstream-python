FROM nvcr.io/nvidia/deepstream:6.0.1-samples

RUN apt-get -y update
RUN apt install -y \
    libssl1.0.0 \
    libgstreamer1.0-0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstrtspserver-1.0-0 \
    libjansson4 \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    python-gi-dev \
    python3-pip \
    python3-numpy \
    python3-opencv \
    wget


WORKDIR /opt/tmp

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

RUN pip3 install paho-mqtt

ADD apps /opt/nvidia/deepstream/deepstream/sources/python/apps

WORKDIR /opt/nvidia/deepstream/deepstream/sources/python/apps

ENTRYPOINT ./wait-for-it.sh mqtt:1883 -- python3 -u ds_mqtt.py 

