# Deepstream 6.0.1 with Python on Docker Compose

This project uses deepstream 6.0.1 running on a docker compose with mqtt from mosquitto
the projcet is develop in python and reads messages from mqqt to pause, play or stop 
the pipeline as well as to send images from pipeline or messages



                       ┌ queue - valve - nvinfer ┐ 
                       |                         |
    src - streammux - tee                      funnel - nvvideoconvert - capsfilter - nvmultistreamtiler - nvvideoconvert - nvosd - nveglglessink
                       |                         |
                       └ queue - valve ----------┘


## Run project

To run the project you need to create a deepstream.env file with below keys.

STREAMS is an array of sources rtsp or files

```
STREAMS="rtsp://url:port/ rtsp://url:port"
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