# Deepstream 6.0.1 with Python on Docker Compose

This project uses deepstream 6.0.1 running on a docker compose environment with mqtt from mosquitto
the project is developed in python and reads messages from mqtt to pause, play or stop 
the pipeline as well as to disable or enable inference.

Also support to add probe callback to get access to images in pipeline or to send messages



                       ┌ queue - valve - nvinfer -nvtracker - nvinfer - nvinfer -nvinfer ┐ 
                       |                                                                 |
    src - streammux - tee                                                              funnel - nvvideoconvert - capsfilter - nvmultistreamtiler - nvvideoconvert - nvosd - nveglglessink
                       |                                                                 |
                       └ queue - valve --------------------------------------------------┘


## Run project

To run the project you need to create a deepstream.env file with below keys.

STREAMS is an array of sources rtsp or files

```
MQTT_BROKER=mqtt
MQTT_PORT=1883
MQTT_TOPIC_COMMAND=/deepstream/command
MQTT_TOPIC_MESSAGES=/deepstream/message
STREAMS="rtsp://url:port/ rtsp://url:port"
SHOW_ON_SCREEN=1
PYTHONUNBUFFERED=1
```

Then you can build the images by running

```
docker-compose build
```

And finally run it by 

```
xhost +
docker-compose up
```

Once the two instances are running you can connect to the mqtt server on localhost 1883 with
any mqtt client and send commands

| topics | message | description |
| --- | ----------- | ----------- |
| /deepstream/command | {"command": "play"} | Sets play status to pipeline (Default state) |
| /deepstream/command | {"command": "pause"} | Sets pause status to pipeline |
| /deepstream/command | {"command": "stop"} | Sets stop status to pipeline |
| /deepstream/command | {"inference": "enabled"} | Enables the inference flow (Default state) |
| /deepstream/command | {"inference": "disable"} | Disable the inference flow still image visible on sync |