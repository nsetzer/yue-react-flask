
This guide will walk through the installation process of the web app
on Ubuntu 18.04. Including installing a flask server using gunicorn,
NginX, and PostgreSQL. Let's Encrypt will be used for generating SLL
certificates

This guide is based on the following two articals:

* [Digital Ocean Initial Setup](https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-18-04)
* [Serve Flask Apps with Digital Ocean](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04)
* [Install PostgreSQL on Ubuntu 18.04](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-18-04)

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
 apt install ffmpeg

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

### Base Application Config

Create the following config files, or copy existing ones from the repository. The
directory that the yaml files lives in is used as the name of the profile.

`./config/production/application.yml`
`./config/production/env.yml`

#### Encryption for Application Config values

Two methods for encrypting values in the application config are provided.
An RSA mode uses a public and private keypair for encryption and decryption.

Note that any string value can be encrypted. Encrypting of the application secret,
which is used for generating session tokens is demonstrated below.

#### SSM Encryption
Not Implemented at this time.
Ensure IAM roles are configured correctly.
An attempt to retrieve the given key from parameter store will be made.

Make the following changes to the application config
```json
encryption_mode: ssm
server:
  secret_key: "SSM:/ssm/key/path"
```

#### RSA Encryption
Generate a keypair used for encrypting and decrypting application secrets.
Make sure that the public and private key files are only readable
by the root user

```bash
mkdir /opt/yueserver/crypt
python -m server.tools.manage generate_keypair --outdir /opt/yueserver/crypt rsa
chmod chmod 600 crypt/rsa{.pem,.pub}
```

```bash
$ ls -la ./crypt
drwxr-xr-x 2 root root 4096 Sep 16 09:49 .
-rw------- 1 root root 1674 Sep 16 09:50 rsa.pem
-rw------- 1 root root  450 Sep 16 09:50 rsa.pub
```

Running the encrypt64 command will produce a base64 string containing the AES encrypted secret:
```bash
python -m server.tools.manage encrypt64  /opt/yueserver/crypt/rsa.pub "mysecret"
```

Add the encrypted value to the application configuration:

```json
encryption_mode: rsa
server:
  secret_key: "RSA:<hash>"
```

### Install PostgreSQL

```bash
    sudo apt update
    sudo apt install postgresql postgresql-contrib

```
### Configure PostgreSQL

PostgreSQL can be used in place of sqlite. A database and user must first be
created in postgres, then the connection settings can be added to the
application configuration.

Method 1:

```bash
sudo -u postgres createuser yueapp
sudo -u postgres createdb yueapp
sudo -u postgres psql
    psql=# alter user yueapp with encrypted password 'CHANGEME';
    psql=# grant all privileges on database yueapp to yueapp;
    psql=# \q
```

Method 2:

Execute the following SQL:
```bash
sudo -u postgres psql
    CREATE DATABASE yueapp;
    CREATE USER yueapp WITH ENCRYPTED PASSWORD 'CHANGEME';
    GRANT ALL PRIVILEGES ON DATABASE yueapp TO yueapp;
```

Then make the following changes to the application config.

`./config/production/application.yml`
```json

server:
  database:
    kind: "postgresql"
    hostname: "localhost:5432"
    username: "yueapp"
    password: "<password>"
    database: "yueapp"

```

#### Suggested Postgres Configuration

These settings were chosen for a server with 1 core and 1GB of available memory.
The values where generated using pgTune.

```bash
psql -U postgres
postgres=# SHOW config_file;
```

`/etc/postgresql/9.5/main/postgresql.conf`

```bash
max_connections = 10
shared_buffers = 128MB
effective_cache_size = 450MB
maintenance_work_mem = 48MB
checkpoint_completion_target = 0.7
wal_buffers = 5.0MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 15MB
min_wal_size = 80MB
max_wal_size = 1GB
```

restart postgres for changes to take effect

#### Browse PostgresSQL Schema

* \c <dbname> : connect to database
* \dt : list tables

> Note: 'user' is a special word in PostgreSQL, and also a default table
> in the application. the string must be double quoted in a command
> `select * from "user";`

### Initialize the database

The connection settings defined in the application config will be used
to connect to the database, and the environment config will be used
to configure the database for first use.

```bash
python -m server.tools.manage --profile production create
```

Test that the application can start. As the root user run:

```bash
sudo -u yueapp python3 wsgi.py
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


### PostgreSQL backup and restore


Backup:
```bash
pg_dump yueapp | gzip | split -d -b 512M - backup.gz.
```

Restore:
```bash
python3 -m yueserver.tools.manage -pproduction drop
cat backup.gz.* | gunzip | psql yueapp
```

### PostgreSQL Change Password

Method1:

```
sudo -u yueapp psql
\password
```

Method2:

```
sudo -u postgres psql
ALTER USER yueapp WITH ENCRYPTED PASSWORD 'CHANGEME';
```

### PostgreSQL Health Checks

Execute the following SQL to create two tables used for querying the
status of the postgres server

```bash

    CREATE EXTENSION file_fdw;
    CREATE SERVER fileserver FOREIGN DATA WRAPPER file_fdw;

    CREATE FOREIGN TABLE loadavg
    (one text, five text, fifteen text, scheduled text, pid text)
    SERVER fileserver
    OPTIONS (filename '/proc/loadavg', format 'text', delimiter ' ');

    CREATE FOREIGN TABLE meminfo
    (stat text, value text)
    SERVER fileserver
    OPTIONS (filename '/proc/meminfo', format 'csv', delimiter ':');

    GRANT ALL PRIVILEGES ON TABLE meminfo TO yueapp;
    GRANT ALL PRIVILEGES ON TABLE loadavg TO yueapp;

```
