#!/bin/bash

update-rc.d postgresql enable

/etc/init.d/postgresql start

su postgres -c psql <<-EOSQL
    CREATE DATABASE yueapp;
    CREATE USER yueapp WITH ENCRYPTED PASSWORD 'CHANGEME';
    GRANT ALL PRIVILEGES ON DATABASE yueapp TO yueapp;
EOSQL

mkdir crypt
python3 -m yueserver.tools.manage --profile docker generate_keypair --outdir crypt rsa
chmod 600 crypt/rsa{.pem,.pub}

python3 -m yueserver.tools.manage --profile docker create
