

# React Flask

This repository contains an example Single Page Application (SPA) using Flask and React. SQLAlchemy is used for the database connection, allowing for SQLite or PostgreSQL.

The app demonstrates basic concepts such as:
* User Account Management (login , register, protecting views behind authentication)
* Exposing a server api, enabling CORS
* Database models, and interacting with the database to display messages.


https://github.com/wmonk/create-react-app-typescript

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
```bash
python app.py
```
Browse to http://localhost:4100. The front end is listening on port 4100 and the backend is listening on port 4200

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
python app.py
```

Browse to http://localhost:4200. The React bundle is served by the Flask server.

Environment variables are used to control several features.

set `PORT` to the desired port to run the Flask application on.

set `DATABASE_URL` to `sqlite:///path/to/database.db` to use a SQLite database. Alternativley set it to `postgresql://localhost` for PostgreSQL.

set `SECRET_KEY` to a randomly generated string. This key is used for user authentication.


## Test

### Frontend Unit Test
```bash
npm test
```

### Backend Unit Tests
```bash
python test.py
```


