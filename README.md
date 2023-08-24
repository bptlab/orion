# Orion: Discovering and Exploring Change Patterns in Dynamic Event Attributes

This repository provides orion, a tool to discover and explore change patterns in dynamic event attributes. It includes the source code, as well as the docker container, to run the applications. Further, two analysis use cases are presented.

## Setup

The easiest way to setup orion is to use [docker](https://hub.docker.com/r/jcremerius/orion/tags). Just pull the image using the following command:
```docker pull jcremerius/orion:latest``` and run it by executing ```docker run -p 8000:8000 -it jcremerius/orion:latest bin/bash```. After that, a docker container is created and shall run. The application can be accessed via a webbrowser under the following address [http://127.0.0.1:8000](http://127.0.0.1:8000)


