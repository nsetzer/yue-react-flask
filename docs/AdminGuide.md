

sudo nginx -t
sudo systemctl restart nginx

/etc/nginx/sites-available/yueapp

/var/log/nginx/error.log
/var/log/nginx/access.log
/opt/yueserver/logs/server.log


sudo systemctl restart yueserver


sudo -u yueapp psql   # connect to postgres db
\c yueapp             # connect to yeuapp db
\dt                   # list all tables
select * from 'user'; # list users


# upgrade
sudo systemctl stop yueserver
sudo bash yueserver-0.0.0.tar.gz
sudo systemctl start yueserver
