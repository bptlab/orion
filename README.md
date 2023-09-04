# Orion: Discovering and Exploring Change Patterns in Dynamic Event Attributes

This repository provides orion, a tool to discover and explore change patterns in dynamic event attributes. It includes the source code, as well as the docker container, to run the application. Further, two analysis use cases are presented.

## Setup

The easiest way to setup orion is to use [docker](https://hub.docker.com/r/jcremerius/orion/tags). Just pull the image using the following command:
```docker pull jcremerius/orion:latest``` and run it by executing ```docker run -p 8000:8000 -d jcremerius/orion:latest```. After that, a docker container is created and shall run. The application can be accessed via a webbrowser under the following address [http://127.0.0.1:8000](http://127.0.0.1:8000).


## Alternative Anaconda Setup

Alternatively, it is possible to setup the tool without docker locally using Anaconda. Install [Anaconda](https://anaconda.org/) and run the following command in this folder: ```conda env create --name env --file=environment_packages.yml```. Then, replace the pm4py package in the environment with the pm4py package included in this repository. After that, activate the enviroment by executing ```conda activate env``` and run the django server in the orion folder with: ```python manage.py runserver 0.0.0.0:8000 --insecure```. The application is then accessible via webbrwoser under the following address: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Tool Usage + Video
The tool can be used with any event log, provided as a .csv file. Please be aware, that event logs should include dynamic event attributes. Else, this tool provides no new insights for the given event log. We recommend the Sepsis Event Log, which can be found [here](https://github.com/bptlab/orion/tree/master/Demonstration/Sepsis).


A demonstration of the tool on a healthcare dataset, extracted from MIMIC-IV can be viewed via the following link: [https://www.youtube.com/watch?v=CIwaCuSN03s](https://www.youtube.com/watch?v=CIwaCuSN03s). The dataset was also used by us for evaluating the research contributions.

Further, a demonstration on the Sepsis event log can be found [here](https://github.com/bptlab/orion/tree/master/Demonstration/Sepsis).

Please be aware, that the server (or the docker container) needs to be restarted, if one wants to upload a new event log. We are working on fixing this issue.


## Source Code
The application is written within the Django framework, where the project is stored [here](https://github.com/bptlab/orion/tree/master/orion). It utilizes the python package, also called orion, which can be found [here](https://github.com/bptlab/orion/tree/master/orion/orion), which provides all functionalities without the frontend.
