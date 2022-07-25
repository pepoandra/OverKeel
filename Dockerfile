FROM ubuntu:18.04

WORKDIR code
RUN apt-get update -y; apt-get install wget ffmpeg python libopenblas-base imagemagick -y
COPY overfeat ./overfeat
COPY overfeat-v04-2.tgz .
COPY install.sh .
COPY project.py .
COPY 420.mp4 .


RUN /bin/bash install.sh

CMD python code/project.py
