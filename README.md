

# Yue React Flask

Yue is a self hosted music streaming platform and SPA.
It provides tools to manage a music library and a web interface to create and listen to playlists.

## Development Builds

##### Install
```bash
npm install
pip install -r requirements.txt
```

##### Create a development database:
```bash
python manage.py create
```

##### Start the frontend
```bash
npm start
```

##### Start the backend
Run this in a separate terminal
```bash
python -m server.app --profile development
```
The front end is listening on port 4100 and the backend is listening on port 4200.
Open http://localhost:4100 in your browser.

##### Point frontend at a different backend
By default in development mode the frontend assumes the backend
is running on localhost:4200. This can be changed with an environment
variable

```bash
BACKEND_PATH=http://localhost:1234 npm start
```

## Production Builds

Build the bundle and serve via the Flask application.
```bash
npm run build
python -m server.app --profile production
```

Browse to http://localhost:4200. The React bundle is served by the Flask server.

## Test

### Frontend Unit Test
```bash
npm test
```

### Backend Unit Tests
```bash
python util/test.py
```

## Profiles

The backend configuration comes from the profile that is used when the application is started.
A profile contains an application config (application.yml) and an environment config (env.yaml).
The name of the profile is the name of the directory these files reside in.
The config directory contains several sample profiles.

#### Environment config

The environment config defines the set of features, roles, and domains for the application.
It also lists the default set of users.


initialize a sqlite or PostgreSQL database with a given environment
```bash
python manage.py create --db sqlite:///database.sqlite --profile <profile>
```

update the database environment a given environment

```bash
python manage.py update --db sqlite:///database.sqlite --profile <profile>
```

#### Application config

todo

## Import Music

A json file containing a list of song objects can be imported.
At minimum the Artist, Title, and Album must be set.
See the Song object in server/dao/library.py for the complete list of keys.

If the reference id is set, the import can be run again to update
the song instead of creating a new entry. The reference id is an unique
integer id that you provide, and is not used by the application for
any other purpose

```bash

$ cat music.json
  [ {"artist": "The White Stripes",
     "title": "Seven Nation Army",
     "album": "Elephant",
     "genre": "rock",
     "path": "/mnt/data/music/The White Stripes/Elephant/Seven Nation Army.mp3",
     "ref_id": 1
    },
  ]
$ python -u manage.py import music.json
```