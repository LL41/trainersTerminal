from main import strava_flask_app
from flask import Flask

app = strava_flask_app()

if __name__ == '__main__':
    strava_flask_app.run()