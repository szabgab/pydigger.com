#!/usr/bin/bash
#export PATH=$PATH:/home/gabor/docker-compose/bin

if [ "$1" == "stop" ];
then
  echo "stop"
  docker compose stop
  exit 0
fi

if [ "$1" == "deploy" ];
then
  echo "deploy"
  git pull
  docker compose build
fi

if [ "$1" == "deploy" ] || [ "$1" == "restart" ];
then
  echo "restart"
  docker compose stop --timeout 0
  docker compose up --detach --timeout 0 --remove-orphans
  docker image prune -f
else

  echo "Usage: $0 [deploy|restart|stop]"
fi
