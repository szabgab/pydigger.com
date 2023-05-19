ts=$(date "+%Y-%m-%d-%H-%M-%S")
# echo $ts

mongodump -u root -p Secret --out /backup/mongodb-$ts --quiet
cd /backup
tar -czf mongodb-$ts.tar.gz mongodb-$ts/
rm -rf mongodb-$ts

find /backup -mtime +1 -name '*.tar.gz' -exec echo {} \;
#rm $old;

