from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, render_template, request, Response
import pandas as pd
from datetime import datetime, timedelta, date
from urllib.parse import urlparse, parse_qs
import stravalib
from stravalib import unithelper
import requests
import os
import sys
import markdown

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Replace with a strong secret key

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
data_storage = []
checkbox_list = ['hr_checkbox','power_checkbox','speed_checkbox'
                     ,'sufferscore_checkbox','GPS_checkbox'
                     ,'pacedata_checkbox','elevationdata_checkbox']

#Redirect URI for OAuth
#redirect_uri = 'http://127.0.0.1:5000/auth/callback'
redirect_uri = 'https://45.63.19.39/auth/callback'

today = datetime.today()
last_year = today - timedelta(days=365)
last_year = last_year.strftime("%Y-%m-%d")

one_week_ago = today - timedelta(days=7)
one_week_ago = one_week_ago.strftime("%Y-%m-%d")

one_month_ago = today - timedelta(days=30)
one_month_ago = one_month_ago.strftime("%Y-%m-%d")

def division(x, y):
    return x/y if y else 0

def getRecentActivites(time):
    client = stravalib.Client(access_token=session['access_token'])
    activities = client.get_activities(after=time)
    return activities

def generate_table(date_range,data_type,measurment_system):
    activities = getRecentActivites(date_range)

    data = [
    (result.id, result.name, result.start_date_local, result.elapsed_time, result.moving_time,
     result.average_watts, result.max_watts, result.average_cadence,
     round(float(unithelper.miles(result.distance).magnitude), 2),
     round(float(unithelper.kilometers(result.distance).magnitude), 2),
     division(((result.moving_time)/60), float(unithelper.miles(result.distance).magnitude)),
     division(((result.moving_time)/60), float(unithelper.kilometers(result.distance).magnitude)),
     result.sport_type, result.average_heartrate, result.max_heartrate,
     round(float(unithelper.feet(result.total_elevation_gain).magnitude), 2),
     round(float(unithelper.meters(result.total_elevation_gain).magnitude), 2),
     result.suffer_score,
     round(float(unithelper.miles_per_hour(result.average_speed).magnitude), 2),
     round(float(unithelper.miles_per_hour(result.max_speed).magnitude), 2),
     round(float(unithelper.kilometers_per_hour(result.average_speed).magnitude), 2),
     round(float(unithelper.kilometers_per_hour(result.max_speed).magnitude), 2))
     for result in activities
    ]

    df = pd.DataFrame(data, columns=[
        'id', 'name', 'start_date_local', 'elapsed_time_seconds', 'moving_time_seconds',
        'average_watts', 'max_watts', 'average_cadence', 'distance_miles', 'distance_kilometers',
        'minutes_per_mile_pace', 'minutes_per_kilometer_pace', 'sport_type', 'average_heartrate',
        'max_heartrate', 'total_elevation_gain_feet', 'total_elevation_gain_meters', 'suffer_score',
        'average_speed_mph', 'max_speed_mph', 'average_speed_kmh', 'max_speed_kmh'
    ])

    if data_type == 'Cycling':
        df = df.query('sport_type.str.contains("Ride")')
    elif data_type == 'Running':
        df = df.query('sport_type.str.contains("Run")')
    elif data_type == 'Swimming':
        df = df.query('sport_type.str.contains("Swim")')
    else:
        df = df

    if measurment_system == 'imperial':
        df = df.drop(['distance_kilometers', 'minutes_per_kilometer_pace'
                      ,'total_elevation_gain_meters','average_speed_kmh','max_speed_kmh'], axis=1)
    else:
        df = df.drop(['distance_miles', 'minutes_per_mile_pace'
                      ,'total_elevation_gain_feet','average_speed_mph','max_speed_mph'], axis=1)

    return df


def get_initial_athlete():
    client = stravalib.Client(access_token=session['access_token'])
    athlete = client.get_athlete()
    athlete_name = athlete.firstname
    session['athlete_initialized'] = 'True'
    return athlete_name


########FLASK APP

@app.route('/intake', methods=['GET', 'POST'])
def intake():
    if 'access_token' not in session:
        print("redirect")
        return redirect(url_for('index'))
    #Need to add in error handling for error code 500 when code being used is old, should redirect to auth if code is old and log user out.
    
    #Initialize athlete. Get name.
    if 'athlete_initialized' not in session:
        session['athlete_name'] = get_initial_athlete()
    else:
        pass

    #Get form information.
    if request.method == 'POST':
        data_type = request.form['data_type']
        date_range = request.form['date_range']
        measurment_system = request.form['measurment_system']

        date_ranges = {
        'last_year': last_year,
        'last_month': one_month_ago,
        'last_week': one_week_ago,
        'All':None
        }

        df = generate_table(date_ranges[f'{date_range}'],data_type,measurment_system)

        csv_data = df.to_csv(index=False)

        #Send the CSV data as a response with appropriate headers
        return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=trainersterminal_data.csv"}
        )
    else:
        pass

    return render_template('intake.html', athlete_name=session['athlete_name'])

@app.route('/')
def index():
    if 'access_token' in session:
        return redirect(url_for('intake'))
    else:
        pass

    return render_template('index.html')

@app.route('/authorize')
def authorize():
    client = stravalib.Client()
    url = client.authorization_url(client_id, redirect_uri, scope='activity:read')
    return redirect(url)

@app.route('/auth/callback')
def callback():
    current_url = request.url
    parsed_url = urlparse(current_url)
    query_params = parse_qs(parsed_url.query)
    code = query_params['code'][0]
    client = stravalib.Client()
    access_token = client.exchange_code_for_token(client_id, client_secret, code)
    session['access_token'] = access_token['access_token']
    return redirect(url_for('intake'))

@app.route('/logout')
def logout():
    session.pop('access_token', None)
    session.pop('athlete_initialized', None)
    session.pop('athlete_name', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
