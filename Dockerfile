FROM ubuntu:19.10

RUN apt-get update                 && \
    apt-get upgrade -y             && \
    apt-get install -y python3     && \
    apt-get install -y python3-pip && \
    echo DONE apt-get

WORKDIR /opt
COPY requirements.txt /opt/
RUN pip3 install -r /opt/requirements.txt

#CMD FLASK_APP=app FLASK_DEBUG=1 flask run --host 0.0.0.0 --port 5000