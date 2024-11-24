from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, render_template, request
import pandas as pd
from datetime import datetime, timedelta
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
redirect_uri = 'http://127.0.0.1:5000/auth/callback'
#redirect_uri = 'https://45.63.19.39/auth/callback'

today = datetime.today()
last_year = today - timedelta(days=365)
last_year = last_year.strftime("%Y-%m-%d")

one_week_ago = today - timedelta(days=7)
one_week_ago = one_week_ago.strftime("%Y-%m-%d")

def division(x, y):
    return x/y if y else 0

def getRecentActivites(time):
    client = stravalib.Client(access_token=session['access_token'])
    activities = client.get_activities(after=time)
    return activities

def generate_table():
    activities = getRecentActivites(one_week_ago)

    id = []
    name = []
    start_date_local = []
    elapsed_time_seconds = []
    moving_time_seconds = []
    average_speed_mph = []
    max_speed_mph = []
    average_speed_kmh = []
    max_speed_kmh = []
    average_watts = []
    max_watts = []
    average_cadence = []
    distance_miles = []
    distance_kilometers = []
    sport_type = []
    average_heartrate = []
    max_heartrate = []
    total_elevation_gain_feet = []
    total_elevation_gain_meters = []
    suffer_score = []
    minutes_per_mile_pace = []
    minutes_per_kilometer_pace = []

    #Should probably make this a seperate module in flask app that the flask app calls in.
    for results in activities:
      id.append(results.id)
      name.append(results.name)
      start_date_local.append(results.start_date_local)
      elapsed_time_seconds.append(results.elapsed_time)
      moving_time_seconds.append(results.moving_time)
      average_watts.append(results.average_watts)
      max_watts.append(results.max_watts)
      average_cadence.append(results.average_cadence)
      distance_miles.append(round(float(unithelper.miles(results.distance).magnitude),2))
      distance_kilometers.append(round(float(unithelper.kilometers(results.distance).magnitude),2))
      minutes_per_mile_pace.append(round(division(((results.moving_time)/60),float(unithelper.miles(results.distance).magnitude)),2))
      minutes_per_kilometer_pace.append(round(division(((results.moving_time)/60),float(unithelper.kilometers(results.distance).magnitude)),2))
      sport_type.append(results.sport_type.root)
      average_heartrate.append(results.average_heartrate)
      max_heartrate.append(results.max_heartrate)
      total_elevation_gain_feet.append(round(float(unithelper.feet(results.total_elevation_gain).magnitude),2))
      total_elevation_gain_meters.append(round(float(unithelper.meters(results.total_elevation_gain).magnitude),2))
      suffer_score.append(results.suffer_score)
      average_speed_mph.append(round(float(unithelper.miles_per_hour(results.average_speed).magnitude),2))
      max_speed_mph.append(round(float(unithelper.miles_per_hour(results.max_speed).magnitude),2))
      average_speed_kmh.append(round(float(unithelper.kilometers_per_hour(results.average_speed).magnitude),2))
      max_speed_kmh.append(round(float(unithelper.kilometers_per_hour(results.max_speed).magnitude),2))

    my_dict = {'id':id, 'name':name,'start_date_local':start_date_local, 'elapsed_time_seconds':elapsed_time_seconds, 'moving_time_seconds':moving_time_seconds
               , 'sport_type': sport_type, 'distance_miles': distance_miles, 'distance_kilometers': distance_kilometers
               , 'average_speed_mph':average_speed_mph, 'max_speed_mph':max_speed_mph, 'average_speed_kmh':average_speed_kmh
               , 'max_speed_kmh':max_speed_kmh
               , 'average_watts': average_watts, 'max_watts':max_watts
               , 'average_cadence':average_cadence
               , 'average_heartrate':average_heartrate, 'max_heartrate': max_heartrate
               , 'total_elevation_gain_feet': total_elevation_gain_feet, 'total_elevation_gain_meters':total_elevation_gain_meters
               , 'suffer_score':suffer_score
               , 'minutes_per_mile_pace':minutes_per_mile_pace, 'minutes_per_kilometer_pace':minutes_per_kilometer_pace
               }

    df = pd.DataFrame(my_dict)
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
        session['data_type'] = request.form['data_type']
        session['date_range'] = request.form['date_range']
        session['measurment_system'] = request.form['measurment_system']
        return redirect(url_for('planning'))
    else:
        pass

    return render_template('intake.html', athlete_name=session['athlete_name'])

#This will be page after intake
@app.route('/planning')
def planning():
    #Form data
    data_type = session['data_type']
    training_type = session['training_type']
    supplied_data = data_type
    print(data_type)


    template = render_template('planning.html', supplied_data=supplied_data)
    return template

@app.route('/')
def index():
    if 'access_token' in session:
        print("redirect")
        return redirect(url_for('intake'))
    else:
        pass

    #activity = client.get_activity(most_recent_activity_id)
    #kudoscount = activity.kudos_count

    return render_template('index.html')

#Currently unused.
@app.route('/get_data/<activity_type>')
def get_data(activity_type):
    if activity_type == 'ride':
        data = get_distance_data(session['ride_miles'])
    elif activity_type == 'run':
        data = get_distance_data(session['run_miles'])
    elif activity_type == 'all':
        data = get_distance_data(session['total_distance'])
    else:
        return 'Error'

    return data

@app.route('/authorize')
def authorize():
    client = stravalib.Client()
    url = client.authorization_url(client_id, redirect_uri, scope='activity:read')
    print("redirect2")
    return redirect(url)

@app.route('/auth/callback')
def callback():
    print("Callback accesed")

    current_url = request.url
    parsed_url = urlparse(current_url)
    query_params = parse_qs(parsed_url.query)
    code = query_params['code'][0]
    print(code)
    client = stravalib.Client()
    access_token = client.exchange_code_for_token(client_id, client_secret, code)
    #Only print for troubleshooting, dont use in dev.
    #print(access_token)
    session['access_token'] = access_token['access_token']
    return redirect(url_for('intake'))

@app.route('/logout')
def logout():
    session.pop('access_token', None)
    session.pop('athlete_initialized', None)
    session.pop('athlete_type',None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
