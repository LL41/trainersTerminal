from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, render_template, request
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

#Redirect URI for OAuth
redirect_uri = 'http://127.0.0.1:5000/auth/callback'
#redirect_uri = 'https://45.63.19.39/auth/callback'

def trips_around_world(distance):
  earth_circumference = 24901  # miles
  return round((distance / earth_circumference)*100,2)

today = datetime.today()
tomorrow = today + timedelta(days=1)
tomorrow = tomorrow.strftime("%Y-%m-%d")

def get_all_activity_data():
    client = stravalib.Client(access_token=session['access_token'])
    most_recent_activity = client.get_activities(before=tomorrow)
    distance = 0
    for data in most_recent_activity:
        #most_recent_activity_id = data.id
        #full_data = data
        #elapsed_time = data.elapsed_time
        #distance = data.distance
        distance = distance + float(unithelper.miles(data.distance))
    return distance

def get_distance_data(distance):
    distance_data = {
        "total_distance": round(distance),
        "progress_percentage": trips_around_world(distance),
        "miles_left": 24901 - round(distance,2)
    }
    return distance_data


def get_initial_athlete():
    client = stravalib.Client(access_token=session['access_token'])
    athlete = client.get_athlete()
    athlete_stats = client.get_athlete_stats()
    ride_miles = round(float(unithelper.miles(athlete_stats.all_ride_totals.distance).magnitude),2)
    run_miles = round(float(unithelper.miles(athlete_stats.all_run_totals.distance).magnitude),2)
    swim_miles = round(float(unithelper.miles(athlete_stats.all_swim_totals.distance).magnitude),2)
    athlete_name = athlete.firstname
    total_distance = get_all_activity_data()
    session['athlete_initialized'] = 'True'
    return ride_miles, run_miles, swim_miles, athlete_name, total_distance


########FLASK APP

@app.route('/intake', methods=['GET', 'POST'])
def intake():
    if 'access_token' not in session:
        print("redirect")
        return redirect(url_for('index'))
    #Need to add in error handling for error code 500 when code being used is old, should redirect to auth if code is old and log user out.
    #Get name
    
     #Load athlete data.
    if 'athlete_initialized' not in session:
        session['ride_miles'], session['run_miles'], session['swim_miles'], session['athlete_name'], session['total_distance'] = get_initial_athlete()
    else:
        pass
    
    try:
        ride_miles = session['ride_miles']
        run_miles = session['run_miles']
        swim_miles = session['swim_miles']
        athlete_name = session['athlete_name']
        total_distance = session['total_distance']
    except KeyError:
        session.pop('athlete_initialized', None)
        return redirect(url_for('index'))

    #Get form information.
    if request.method == 'POST':
        session['data_type'] = request.form['data_type']
        session['date_range'] = request.form['date_range']
        session['hr_checkbox'] = request.form['hr_checkbox']
        return redirect(url_for('planning'))
    else:
        pass

    return render_template('intake.html', athlete_name=athlete_name)

#This will be page after intake
@app.route('/planning')
def planning():
    ride_miles = round(session['ride_miles'])  
    run_miles = round(session['run_miles'])
    swim_miles = round(session['swim_miles'])
    athlete_name = session['athlete_name']
    total_distance = round(session['total_distance'])

    #From data
    athlete_type = session['data_type']
    training_type = session['training_type']
    hr_checkbox = session['hr_checkbox']
    print(athlete_type)
    print(hr_checkbox)


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
