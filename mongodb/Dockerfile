FROM mongo:4.4
RUN apt-get update && \
    apt-get install -y cron && \
    echo DONE
COPY crontab.txt .
RUN crontab crontab.txt
