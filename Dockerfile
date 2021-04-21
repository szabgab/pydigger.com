FROM python:3.9

WORKDIR /opt
COPY requirements.txt /opt/
RUN pip install -r /opt/requirements.txt

#ENV PYDIGGER_TEST=1
ENV PYDIGGER_CONFIG=dev.yml
ENV FLASK_APP=PyDigger.website
ENV FLASK_DEBUG=1
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000"]
