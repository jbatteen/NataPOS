# import libraries
from flask import Flask, render_template, request, redirect
import random
import os
import sys
import subprocess
import time
from pymongo.mongo_client import MongoClient


# import local files
from load_config import load_config
from validate_login import validate_login
from validate_session_key import validate_session_key
from create_user import create_user


# variable config section
dbname = 'testpos'
mongouri = 'mongodb://localhost:27017'

# begin app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def login():
  # load config
  config = []
  config = load_config(dbname, mongouri)
  business_name = config[0]
  assets_url = config[1]
  client = MongoClient(mongouri)
  db = client[dbname]
  if request.method == 'POST':
    print('post')
    print('function :' + request.form['function'])
    if request.form['function'] == 'create_first_user':
      username = request.form['username']
      password = request.form['password']
      password2 = request.form['password']
      if password != password2:
        return render_template('create_first_user.html', business_name=business_name, assets_url=assets_url, message="Error: passwords didn't match")
      else:
        creation_check = []
        creation_check = create_user(db, username, password, True)
        if creation_check == True:
          return render_template('login.html', business_name=business_name, assets_url=assets_url, message="User created successfully.  You may now log in.")
        else:
          return 'error creating user'

    elif request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # no collection, try default password
        if username == "admin":
          if password == "admin": # default works, send to create first user page
            print('admin:admin')
            return render_template('create_first_user.html', business_name=business_name, assets_url=assets_url)
      else: # collection exists, validate
        print('collection exists')
        login_check = []
        login_check = validate_login(db, username, password)
        if login_check[0] == False: # invalid combo, send back to main page
          return render_template('login.html', business_name=business_name, assets_url=assets_url, error=login_check[1])
        else:
          session_key = login_check[1]
          return render_template('landing.html', business_name=business_name, assets_url=assets_url, username=username, session_key=session_key)
    else:


    # everything failed, send base page
      return render_template('login.html', business_name=business_name, assets_url=assets_url)

  else: # if method == GET
    return render_template('login.html', business_name=business_name, assets_url=assets_url)
@app.route('/landing', methods=['POST'])
def landing(business_name, assets_url, username, session_key):
      if request.form['function'] == 'landing':
        return render_template('landing.html', business_name=business_name, assets_url=assets_url, username=username, session_key=session_key)
      if request.form['function'] == 'clock_in':
        return 'clock in'
      if request.form['function'] == 'clock_out':
        return 'clock out'
      if request.form['function'] == 'open_register':
        return 'open register'
      if request.form['function'] == 'admin':
        return 'admin'


