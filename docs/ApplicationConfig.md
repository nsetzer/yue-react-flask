
The application configuration is a yaml document.
the keys which can be used are given in bold below.

**_encryption_mode_**
options: none, rsa, ssm
* rsa: use a public/private keypair to encrypt/decrypt secrets in this configuration
`mysecret: ENC:<bas64endoded string>`
* ssm: use AWS parameter store to retrieve secrets
`mysecret: ENC:<parameter store path>`

> note: when using rsa encryption, the private key must be passed in via stdin
> when the server starts, for example:
`cat ./crypto/rsa.pem | python3 wsgi.py`

**_server.host_**
in development this is the hostname to listen on, e.g. `localhost`
set to '0.0.0.0' to access the server on the local network

**_server.port_**
in development this is the port to listen on, e.g. `4200`

**_server.env_**

**_server.secret_key_**

**_server.cors.origins_**

**_server.database.kind_**
options: sqlite, postgresql
* sqlite: use a local sqlite database
* postgresql: use a PostgreSQL database

**_server.database.path_**
if the database kind is set to sqlite, this is the path to that database

**_server.database.hostname_**
for postgresql, the hostname and port of the database

**_server.database.username_**
for postgresql, the username to use when connecting

**_server.database.password_**
for postgresql, the password to use when connecting

**_server.database.database_**
for postgresql, the name of the database to connect to

**_server.ssl.private_key_**
**_server.ssl.certificate_**

**_server.logging.directory_**
**_server.logging.filename_**
**_server.logging.max_size_**
**_server.logging.num_backups_**
**_server.logging.level_**

**_server.filesystem.media_root_**
**_server.filesystem.other_**

**_server.transcode.audio.bin_path_**
**_server.transcode.audio.tmp_path_**
**_server.transcode.image_**