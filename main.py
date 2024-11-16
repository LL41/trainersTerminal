from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, render_template, request
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import stravalib
from stravalib import unithelper
import requests
import os
import sys
import google.generativeai as genai
import markdown

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Replace with a strong secret key

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
data_storage = []

# GENAI Setup
genai.configure(api_key=os.getenv("GENAI_KEY"))  
# Instantiate the Gemini model
model = genai.GenerativeModel('gemini-1.5-flash')

# Redirect URI for OAuth
redirect_uri = 'https://trainer-terminal-9206aadf1c4e.herokuapp.com/auth/callback'
#redirect_uri = 'https://127.0.0.1:5000/auth/callback'

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
    #Need to add in error han dling for error code 500 when code being used is old, should redirect to auth if code is old and log user out.
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
        session['athlete_type'] = request.form['athlete_type']
        session['training_type'] = request.form['training_type']
        session['message'] = request.form['message']
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
    athlete_type = session['athlete_type']
    training_type = session['training_type']
    form_message = session['message']
    print(athlete_type)

    athlete_data_list = [ride_miles,run_miles,swim_miles,athlete_name,total_distance]
    athlete_form_list = [athlete_type,training_type,form_message]
    #It will probably make the most sense to naviagte away from using list and create a pretty large prompt in which I format all of this data very clearly for gemeni.
    #Gemeni seems to really care that run/swim data is included. Either need to tell to ignore or just leave it out based on athlete type.

    #GenAI
    #Generate text
    response = model.generate_content(f"Here is a list containing data from an athlete using the app Strava:{athlete_data_list}. This data is in the format: bike ride miles, run miles, swim miles, athlete name, total distance.\n"
    +f"Here is a list of data froma form the athlete filled out {athlete_form_list}. The order of the data is athlete type, athlete training type (chosen from pyramidal, polarized, or not sure), and an optional message from the athlete.\n"
    +"You are tasked with generating a training plan for this athlete.\n"
    +"Use knowledge from the internet and training plans as well as scientific reasearch to determine how their training should be planned. Guess the experience of the athlete too.\n"
    +"Do not assume the athelte is a triathlete unless they specify that on the intake form.\n"
    +"Format the response in the most readable way possible for the athlete.\n"
    +"Always say this at the end: Remember: This is a basic plan to get you started. If you have any specific goals or concerns, consult a certified coach or professional for a personalized training plan.")

    gemeni_response = markdown.markdown(response.text)

    template = render_template(
        'planning.html'
        #, athlete_name=athlete_name
        #, ride_miles=ride_miles
        #, swim_miles=swim_miles
        #, run_miles=run_miles
        #, total_distance=total_distance
        , gemeni_response=gemeni_response)
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
    session['access_token'] = access_token['access_token']
    return redirect(url_for('intake'))

@app.route('/logout')
def logout():
    session.pop('access_token', None)
    session.pop('athlete_initialized', None)
    session.pop('athlete_type',None)
    return redirect(url_for('index'))
