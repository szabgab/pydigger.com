git pull
docker-compose build
docker-compose stop --time 0
docker-compose up --detach --time 0 --remove-orphans
docker image prune -f
