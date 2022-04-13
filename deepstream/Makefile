# make traffic
.PHONY: default image

default: image

image: 
	docker build -t matlock08/kubeedge-deepstream:0.0.2 . 
	docker image push matlock08/kubeedge-deepstream:0.0.2

