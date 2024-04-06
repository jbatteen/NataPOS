# import libraries
from flask import Flask, render_template, request, redirect
import random
import os
import sys
import subprocess
import string
from datetime import datetime, timedelta
from pymongo.mongo_client import MongoClient


# import local files
from config import db_name, mongo_url, assets_url
from validate_login import validate_login
from validate_session_key import validate_session_key
from create_user import create_user
from calculate_worked_hours import calculate_worked_hours
from is_valid import is_valid_string, is_valid_password
# open db
try:
  client = MongoClient(mongo_url)
except:
  exit("couldn't connect to database")
else:
  db = client[db_name]
  try:
    db.validate_collection("natapos")
  except:
    first_time = True
    instance_name = 'NataPOS'
    most_recent_sunday = datetime.now() + timedelta(days=(0.0 - float(datetime.now().isoweekday())))
    current_pay_period_start = str(most_recent_sunday.strftime('%y/%m/%d'))
    db.natapos.insert_one({'config': 'global', 'instance_name': 'NataPOS', 'pay_period_type': 'biweekly', 'current_pay_period_start': current_pay_period_start, 'tax_types': ['Sales Tax', 'Alcohol Tax']})
  else:
    config = db.natapos.find_one({'config': 'global'})
    instance_name = config['instance_name']


  
# begin app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    if request.form['function'] == 'login':  # log in function
      username = request.form['username']
      password = request.form['password']
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # no collection, try default password
        if username == "admin" and password == "admin": # default works, send to create first user page
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url) # default credentials to create first user page
        else:
          return render_template('login.html', instance_name=instance_name, assets_url=assets_url)
      else: # collection exists, validate
        login_check = {}
        login_check = validate_login(db, username, password)
        if login_check['success'] == False: # invalid combo, send back to main page
          return render_template('login.html', instance_name=instance_name, assets_url=assets_url, error=login_check['error'])
        else:
          return redirect('/landing/' + login_check['session_key'])
#          return render_template('landing.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=login_check['session_key'])
    else:


    # plain old index for the first time
      return render_template('login.html', instance_name=instance_name, assets_url=assets_url)

  else: # if method == GET
    if first_time == True:
      return redirect('/create_first_user')
    
    return render_template('login.html', instance_name=instance_name, assets_url=assets_url)


@app.route('/create_first_user', methods=['POST', 'GET'])
def create_first_user():
  if request.method == 'POST':
    if request.form['function'] == 'create_first_user': # create first user form submitted
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # if it doesn't which it shouldn't
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password']
        if username == '':
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message="Error: blank username")
        if password != password2:
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message="Error: passwords didn't match")
        elif password == '':
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message="Error: blank password")

        else:
          creation_check = {}
          creation_check = create_user(db, username, password, {'superuser': True})
          if creation_check['success'] == True:
            result = {}
            print('username: '+ username + 'password: ' + password)
            result = validate_login(db, username=username, password=password)
            print('result: ' + str(result))
            session_key = ''
            if result['success'] == True:
              session_key = result['session_key']
              print('successful creation, session_key: ' + session_key)
              return redirect('/instance_config/' + session_key)
            else:
              return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message='validation error')
          else:
            return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message=creation_check['error'])
      else: # if it does exist and someone called this page anyway
        return('nice try') # someone spoofed
  else:
    return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url)

@app.route('/instance_config/<session_key>', methods=['POST', 'GET'])
def instance_config(session_key):
  message = None
  current_pay_period_start = None
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')
  if request.method == 'POST':
    if request.form['function'] == 'change_instance_name':
      if len(request.form['instance_name']) < 4:
        message = 'Error: name must be 4 characters or more'
      else:
        if is_valid_string(request.form['instance_name']) == False:
          message = 'Error: invalid name.  Allowed characters: \"A-Z\", \"a-z\", \"0-9\", \" .,()-+\"'
        else:
          instance_name = request.form['instance_name']
          db.natapos.update_one({'config': 'global'}, {'$set': {'instance_name': instance_name}})
  else:
    print('method GET')
  config = db.natapos.find_one({'config': 'global'})
  tax_types = []
  tax_types = config['tax_types']
  pay_period_type = config['pay_period_type']
  instance_name = config['instance_name']
  return render_template('instance_config.html', instance_name=instance_name, assets_url=assets_url, session_key=session_key, pay_period_type=pay_period_type, current_pay_period_start=current_pay_period_start, message=message, tax_types=tax_types)
    

@app.route('/landing/<session_key>', methods=['POST', 'GET'])
def landing(session_key):
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')
  
  username = result['username']

  if request.method == 'POST':
    if request.form['function'] == 'clock_in':
      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
      if timesheet is not None:
        timesheet[str(current_time)] = 'in'
        db.timesheets.update_one({'username': username, 'pay_period': 'current'}, {'$set': {str(current_time): 'in'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': 'current', 'worked_hours': 0.0, str(current_time): 'in'})
    if request.form['function'] == 'clock_out':
      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
      if timesheet is not None:
        timesheet[str(current_time)] = 'out'
        db.timesheets.update_one({'username': username, 'pay_period': 'current'}, {'$set': {str(current_time): 'out'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': 'current', 'worked_hours': 0.0, str(current_time): 'out'})
    if request.form['function'] == 'open_register':
      return 'open register'
    if request.form['function'] == 'admin':
      return redirect('/admin/' + session_key)

  timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
  if timesheet is not None:
    worked_hours = str(calculate_worked_hours(timesheet))
    del timesheet['username']
    del timesheet['pay_period']
    del timesheet['_id']
    timestamps = sorted(timesheet)
    last_punch = timesheet[timestamps[-1]]
    message = 'Last punch: ' + last_punch + " " + time.ctime(int(timestamps[-1]))
    if len(timesheet) > 1:
      second_to_last_punch = timesheet[timestamps[-2]]
      if last_punch == second_to_last_punch:
        message = message + "<br><br>Missing punch, see a manager.<br><br>Second to last punch: " + second_to_last_punch + " " + time.ctime(int(timestamps[-2]))
    message = message + '<br><br>Hours on this time sheet: ' + worked_hours
  else:
    message = 'First day worked in the pay period!'


  return render_template('landing.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, message=message)

@app.route('/admin/<session_key>', methods=['POST', 'GET'])
def admin(session_key):
  result = validate_session_key(db, session_key)
  if result == False:
    return redirect('/')
  return render_template('admin.html', instance_name=instance_name, assets_url=assets_url, username=result['username'], session_key=session_key)  
