
This guide will walk through the installation process of the web app
on Ubuntu 18.04. Including installing a flask server using gunicorn,
NginX, and PostgreSQL. Let's Encrypt will be used for generating SLL
certificates

This guide is based on the following two articals:

* [Digital Ocean Initial Setup](https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-18-04)
* [Serve Flask Apps with Digital Ocean ](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04)

## Initial Configuration for a Digital Ocean Droplet

The first time you log in to a droplet, you may need to configure a default
user. Create a standard admin user (name it whatever you want) and give
it sudo access. Then create a daemon user for running the app named 'yueapp'

```bash
ssh root@publicIP

sudo adduser adminuser
sudo useradd -r -s /bin/false yueapp

sudo usermod -aG sudo adminuser
sudo usermod -aG yueapp adminuser
```

 > Note: you may need to update ~/.ssh/authorized_keys for the new admin user.



### Basic Installation

```bash
 apt update
 apt install build-essential libssl-dev libffi-dev
 apt install python3-pip python3-dev python3-venv python3-setuptools
 apt install nginx

```

### Install the Application

extract the tar file containing a release build of the application

```bash
mkdir /opt/yueserver
cd /opt/yueserver
tar -xvf ~/yueserver-0.0.0.tar.gz
python3 -m venv yueserverenv
source yueserverenv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install wheel
python3 -m pip install -r requirements.txt
python3 -m pip install gunicorn

```

The service will run under the previously created yueapp user.
Change the directory permissions so that user has read and write
access to files and folders where the service is installed

```bash
sudo chmod yueapp .
sudo chmod -R yueapp *

sudo chgrp yueapp .
sudo chgrp -R yueapp *
```

Generate a keypair used for encrypting and decrypting application secrets.
Make sure that the public and private key files are only readable
by the root user

> You can skip this step if using parameter store to manage secrets

```bash
mkdir /opt/yueserver/crypt
python -m server.tools.manage generate_keypair --outdir /opt/yueserver/crypt rsa
chmod chmod 600 crypt/rsa{.pem,.pub}
```

```bash
$ ls -la ./crypt
-rw------- 1 root root 1674 Sep 16 09:50 rsa.pem
-rw------- 1 root root  450 Sep 16 09:50 rsa.pub
```

### Base Application Config

todo: how to create a basic application config using sqlite

```bash
python -m server.tools.manage --profile production create
```

Test that the application can start. As the root user run:

```bash
cat ./crypt/rsa.pem | sudo -u yueapp python3 wsgi.py
```

### Application Service

create the following file:

`/etc/systemd/system/yueserver.service`

```
[Unit]
Description=Gunicorn instace to serve yueserver
After=network.target

[Service]
User=yueapp
Group=yueapp
WorkingDirectory=/opt/yueserver
Environment="PATH=/opt/yueserver/yueserverenv/bin:/bin:/usr/bin:/usr/local/bin"
ExecStart=/opt/yueserver/start.sh production

[Install]
WantedBy=multi-user.target
```

The first positional argument to start.sh is the profile to run.
The default value is production

Enable and Start the service

```
sudo systemctl start yueserver
sudo systemctl enable yueserver
```

Check server status
```
sudo systemctl status yueserver
```

Check server logs.

> Useful if the server fails to start

```
sudo journalctl -u yueserver
```

### Firewall Configuration

todo: notes on ufw, or use digital ocean firewall
open 80 and 443
### NginX Configuration

```
server {
    listen 80;
    server_name yueapp.duckdns.org 104.248.122.206;

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/yueserver/yueserver.sock;
        client_max_body_size 500M;
    }
}
```

```
sudo ln -s /etc/nginx/sites-available/yueapp /etc/nginx/sites-enabled
```

check syntax

```
sudo nginx -t
```

restart nginx
```
sudo systemctl restart nginx
```

> note this configuration will be automatically updated by the
> Let's Encrypt process when generating a certificate.

### SSL Certificate

```
sudo add-apt-repository ppa:certbot/certbot
sudo apt install python-certbot-nginx

sudo certbot --nginx -d www.domain domain
```

* enter an email
* choose 2 to for redirect to https

### PostgreSQL

todo