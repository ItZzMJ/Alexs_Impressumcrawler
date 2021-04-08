FROM selenium/standalone-chrome:89.0

USER root
RUN apt-get update && apt-get -y install python3-pip
RUN pip3 install --upgrade pip
COPY requirements.txt /requirements.txt
RUN pip3 install -r ./requirements.txt