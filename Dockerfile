FROM continuumio/miniconda3
EXPOSE 8000
WORKDIR /app
# Create the environment:
COPY . /app
#RUN conda init
RUN conda env create --name env --file=environment_packages.yml
RUN conda init bash
RUN cp pm4py /opt/conda/envs/env/lib/python3.1/site-packages -r
RUN cp pm4py /opt/conda/envs/env/lib/python3.10/site-packages -r
WORKDIR /app/orion
SHELL ["conda", "run", "-n", "env", "/bin/bash", "-c"]
CMD ["conda", "run", "-n", "env", "python", "manage.py", "runserver", "0.0.0.0:8000", "--insecure"]