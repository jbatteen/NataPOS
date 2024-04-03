# import libraries
from flask import Flask, render_template, request, redirect
import random
import os
import sys
import subprocess
import time
from pymongo.mongo_client import MongoClient


# import local files
from validate_login import validate_login
from validate_session_key import validate_session_key
from create_user import create_user
from config import db_name, mongo_uri, assets_url, business_name

# open db
try:
  client = MongoClient(mongo_uri)
except:
  exit('could not connect to database server') # console
db = client[db_name]

# begin app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    if request.form['function'] == 'create_first_user': # create first user form submitted
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # if it doesn't which it shouldn't
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password']
        if username == '':
          return render_template('create_first_user.html', business_name=business_name, assets_url=assets_url, message="Error: blank username")
        if password != password2:
          return render_template('create_first_user.html', business_name=business_name, assets_url=assets_url, message="Error: passwords didn't match")
        elif password == '':
          return render_template('create_first_user.html', business_name=business_name, assets_url=assets_url, message="Error: blank password")

        else:
          creation_check = {}
          creation_check = create_user(db, username, password, True)
          if creation_check['success'] == True:
            return render_template('login.html', business_name=business_name, assets_url=assets_url, message="User created successfully.  You may now log in.")
          else:
            return render_template('create_first_user.html', business_name=business_name, assets_url=assets_url, message=creation_check['error'])
      else: # if it does exist and someone called this page anyway
        return('nice try') # someone spoofed
    elif request.form['function'] == 'login':  # log in function
      username = request.form['username']
      password = request.form['password']
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # no collection, try default password
        if username == "admin":
          if password == "admin": # default works, send to create first user page
            return render_template('create_first_user.html', business_name=business_name, assets_url=assets_url) # default credentials to create first user page
      else: # collection exists, validate
        login_check = {}
        login_check = validate_login(db, username, password)
        if login_check['success'] == False: # invalid combo, send back to main page
          return render_template('login.html', business_name=business_name, assets_url=assets_url, error=login_check['error'])
        else:
          return redirect('/landing/' + login_check['session_key'])
#          return render_template('landing.html', business_name=business_name, assets_url=assets_url, username=username, session_key=login_check['session_key'])
    else:


    # plain old index for the first time
      return render_template('login.html', business_name=business_name, assets_url=assets_url)

  else: # if method == GET
    return render_template('login.html', business_name=business_name, assets_url=assets_url)



@app.route('/landing/<session_key>', methods=['POST', 'GET'])
def landing(session_key):
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')
  else:
    username = result['username']

    if request.method == 'GET':
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
      if timesheet is not None:
        worked_hours = float(timesheet['worked_hours'])
        del timesheet['username']
        del timesheet['pay_period']
        del timesheet['worked_hours']
        del timesheet['_id']
        timestamps = sorted(timesheet)
        last_punch = timesheet[timestamps[-1]]
        message = 'Last punch: ' + last_punch + " " + time.ctime(int(timestamps[-1]))
        if len(timesheet) > 1:
          second_to_last_punch = timesheet[timestamps[-2]]
          if last_punch == second_to_last_punch:
            message = message + "<br>Missing punch, see a manager.<br>Second to last punch: " + second_to_last_punch + " " + time.ctime(int(timestamps[-2]))
      else:
        message = 'First day worked in the pay period!'


      return render_template('landing.html', business_name=business_name, assets_url=assets_url, username=username, session_key=session_key, message=message)


    if request.form['function'] == 'clock_in':
      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
      if timesheet is not None:
        db.timesheets.update_one({'username': username, 'pay_period': 'current'}, {'$set': {str(current_time): 'in'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': 'current', 'worked_hours': 0.0, str(current_time): 'in'})
      return redirect('/landing/' + session_key)
    if request.form['function'] == 'clock_out':
      return 'clock out'
    if request.form['function'] == 'open_register':
      return 'open register'
    if request.form['function'] == 'admin':
      return 'admin'


