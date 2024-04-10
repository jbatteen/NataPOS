# import libraries
from flask import Flask, render_template, request, redirect
import random
import os
import sys
import subprocess
import string
import time
from datetime import date, timedelta, datetime
from pymongo.mongo_client import MongoClient


# import local files
from config import db_name, mongo_url, assets_url
from authentication_functions import validate_login, validate_session_key, create_user
from calculations_and_conversions import calculate_worked_hours, price_to_float
from is_valid import is_valid_username, is_valid_password, is_valid_date, is_date_within_range, is_valid_pay_period_rollover, is_date_in_future, is_valid_string, is_valid_price, is_valid_float, is_valid_int
from inventory_functions import get_item_group_list, get_supplier_list, get_supplier_collection, get_location_list, get_item_locations_collection, get_locations_collection, calculate_item_locations_collection, beautify_item




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
    instance_name = 'NataPOS'
    most_recent_sunday = date.today() + timedelta(days=(0 - int(date.today().isoweekday())))
    two_weeks_from_then = most_recent_sunday + timedelta(days=14)
    current_pay_period = most_recent_sunday.strftime('%m/%d/%y') + "-" + str(two_weeks_from_then.strftime('%m/%d/%y'))
    db.natapos.insert_one({'config': 'global', 'instance_name': 'NataPOS', 'pay_period_type': 'biweekly', 'current_pay_period': current_pay_period, 'pay_period_rollover': 15, 'timesheets_locked': False, 'employee_discount': 0.2})



  
# begin app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def login():
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # no collection, create first user. logically this shouldn't ever happen but it's here in case a session dies in the middle or something
        return redirect('/create_first_user')
      login_check = {}
      login_check = validate_login(db, username, password)
      if login_check['success'] == False: # invalid combo, send back to main page
        return render_template('login.html', instance_name=instance_name, assets_url=assets_url, error=login_check['error'])
      else:
        return redirect('/landing/' + login_check['session_key'])
    else: # this shouldn't ever happen but it's here in case i decide to add/change anything later
      return render_template('login.html', instance_name=instance_name, assets_url=assets_url)

  else: # if method == GET
    try:
      db.validate_collection("employees")
    except:
      return redirect('/create_first_user')
  return render_template('login.html', instance_name=instance_name, assets_url=assets_url)


@app.route('/create_first_user', methods=['POST', 'GET'])
def create_first_user():
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  if request.method == 'POST':
    if request.form['function'] == 'create_first_user': # create first user form submitted
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # if it doesn't which it shouldn't
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        if username == '':
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message="Error: blank username")
        if is_valid_username(username) == False:
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message="Error: Invalid username. Allowed characters: \"A-Z\", \"a-z\", \"0-9\", \" .,()-+\"")
        if password != password2:
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message="Error: passwords didn't match")
        elif password == '':
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message="Error: blank password")

        instance_name = request.form['instance_name']
        if len(instance_name) < 4:
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message='Error: Instance name must be 4 characters or more')
        else:
          if is_valid_string(request.form['instance_name']) == False:
            return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message='Error: invalid name.  Allowed characters: \"A-Z\", \"a-z\", \"0-9\", \" .,()-+\"')
        location_id = request.form['location_id']
        if len(location_id) < 1:
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message='Error: Location name must be 1 character or more')
        else:
          if is_valid_string(request.form['location_id']) == False:
            return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message='Error: invalid name.  Allowed characters: \"A-Z\", \"a-z\", \"0-9\", \" .,()-+\"')            
  
        db.natapos.update_one({'config': 'global'}, {'$set': {'instance_name': instance_name}})
        db.inventory_management.insert_one({'type': 'location', 'location_id': location_id, 'phone': '', 'address':'', 'taxes': [], 'default_taxes': []})
        creation_check = {}
        creation_check = create_user(db, username, password, ['superuser'])
        if creation_check['success'] == True:
          result = {}
          result = validate_login(db, username=username, password=password)
          session_key = ''
          if result['success'] == True:
            session_key = result['session_key']
            return redirect('/global_config/' + session_key)
          else:
            return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message='validation error')
        else:
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message=creation_check['error'])
      else: # if it does exist and someone called this page anyway
        return('nice try') # someone spoofed
  else:
    return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url)

@app.route('/global_config/<session_key>', methods=['POST', 'GET'])
def global_config(session_key):
  message = None
  current_pay_period_start = None
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')

  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions:
    return redirect('/landing/' + session_key)
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
    elif request.form['function'] == 'change_pay_period_type':
      db.natapos.update_one({'config': 'global'}, {'$set': {'pay_period_type': request.form['pay_period_type']}})
    elif request.form['function'] == 'change_current_pay_period_start':
      if is_valid_date(request.form['current_pay_period_start']) == True:
        config = db.natapos.find_one({'config': 'global'})
        pay_period_type = config['pay_period_type']
        if pay_period_type == 'weekly':
          if is_date_within_range(request.form['current_pay_period_start'], 6) == True and is_date_in_future(request.form['current_pay_period_start']) == False:
            date_split = request.form['current_pay_period_start'].split('/')
            current_pay_period_start_time_object = date(int(date_split[2]), int(date_split[0]), int(date_split[1]))
            one_week_from_then = current_pay_period_start_time_object + timedelta(days=7)
            current_pay_period = current_pay_period_start_time_object.strftime('%m/%d/%y') + "-" + str(one_week_from_then.strftime('%m/%d/%y'))
            db.natapos.update_one({'config': 'global'}, {'$set': {'current_pay_period': current_pay_period}})
          else:
            message = 'Error: date out of range'
        elif pay_period_type == 'biweekly':
          if is_date_within_range(request.form['current_pay_period_start'], 13) == True and is_date_in_future(request.form['current_pay_period_start']) == False:
            date_split = request.form['current_pay_period_start'].split('/')
            current_pay_period_start_time_object = date(int(date_split[2]), int(date_split[0]), int(date_split[1]))
            two_weeks_from_then = current_pay_period_start_time_object + timedelta(days=14)
            current_pay_period = current_pay_period_start_time_object.strftime('%m/%d/%y') + "-" + str(two_weeks_from_then.strftime('%m/%d/%y'))
            db.natapos.update_one({'config': 'global'}, {'$set': {'current_pay_period': current_pay_period}})
          else:
            message = 'Error: date out of range'
      else:
        message = 'Error: invalid date'
    elif request.form['function'] == 'change_pay_period_rollover':
      if is_valid_pay_period_rollover(request.form['pay_period_rollover']) == True:
        db.natapos.update_one({'config': 'global'}, {'$set': {'pay_period_rollover': request.form['pay_period_rollover']}})
      else: message = 'Error: invalid pay period rollover'
    elif request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/landing/' + session_key)
    elif request.form['function'] == 'admin':
      return redirect('/admin/' + session_key)
    elif request.form['function'] == 'create_location':
      if is_valid_string(request.form['location_id']) == False:
        message = 'invalid location name'
      else:
        db.inventory_management.insert_one({'type': 'location', 'location_id': request.form['location_id'], 'phone': '', 'address':'', 'taxes': [], 'default_taxes': []})

    elif request.form['function'] == 'remove_default_tax':
      location_document = db.inventory_management.find_one({'type': 'location', 'location_id': request.form['location_id']})
      location_default_taxes = []
      location_default_taxes = location_document['default_taxes']
      location_default_taxes.remove(request.form['tax_id'])
      result = db.inventory_management.update_one({'type': 'location', 'location_id': request.form['location_id']}, {'$set': {'default_taxes': location_default_taxes}})
    
    elif request.form['function'] == 'add_default_tax':
      location_document = db.inventory_management.find_one({'type': 'location', 'location_id': request.form['location_id']})
      location_default_taxes = []
      location_default_taxes = location_document['default_taxes']
      location_default_taxes.append(request.form['tax_id'])
      result = db.inventory_management.update_one({'type': 'location', 'location_id': request.form['location_id']}, {'$set': {'default_taxes': location_default_taxes}})
    elif request.form['function'] == 'create_tax':
      if is_valid_float(request.form['tax_rate']) == False:
        message = 'Invalid tax rate.  Enter a number with no percent sign'
      elif is_valid_string(request.form['tax_id']) == False:
        message = 'Invalid tax ID'
      else:
        location_document = db.inventory_management.find_one({'type': 'location', 'location_id': request.form['location_id']})
        location_taxes = []
        location_taxes = location_document['taxes']
        valid = True
        for i in location_taxes:
          if i['tax_id'] == request.form['tax_id']:
            message = 'tax already exists'
            valid = False
        if valid == True:
          new_tax = {}
          new_tax['tax_id'] = request.form['tax_id']
          tax_rate = 0.0
          tax_rate = float(request.form['tax_rate']) / 100
          new_tax['rate'] = tax_rate
          location_taxes.append(new_tax)
          result = db.inventory_management.update_one({'type': 'location', 'location_id': request.form['location_id']}, {'$set': {'taxes': location_taxes}})
  config = db.natapos.find_one({'config': 'global'})
  pay_period_type = config['pay_period_type']
  instance_name = config['instance_name']
  current_pay_period = config['current_pay_period']
  pay_period_rollover = config['pay_period_rollover']
  return render_template('global_config.html', instance_name=instance_name, assets_url=assets_url, session_key=session_key, pay_period_type=pay_period_type, current_pay_period=current_pay_period, current_pay_period_start=current_pay_period.split('-')[0], pay_period_rollover=pay_period_rollover, message=message, locations_collection=get_locations_collection(db))
    

@app.route('/landing/<session_key>', methods=['POST', 'GET'])
def landing(session_key):
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')
  username = result['username']
  config = db.natapos.find_one({'config': 'global'})
  current_pay_period = config['current_pay_period']
  instance_name = config['instance_name']
  if request.method == 'POST':
    if request.form['function'] == 'clock_in':
      while config['timesheets_locked'] == True:
        time.sleep(1)
        config = db.natapos.find_one({'config': 'global'})

      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': current_pay_period})
      if timesheet is not None:
        db.timesheets.update_one({'username': username, 'pay_period': current_pay_period}, {'$set': {str(current_time): 'in'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': current_pay_period, 'worked_hours': 0.0, str(current_time): 'in'})
    if request.form['function'] == 'clock_out':
      while config['timesheets_locked'] == True:
        time.sleep(1)
        config = db.natapos.find_one({'config': 'global'})
      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': current_pay_period})
      if timesheet is not None:
        db.timesheets.update_one({'username': username, 'pay_period': current_pay_period}, {'$set': {str(current_time): 'out'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': current_pay_period, 'worked_hours': 0.0, str(current_time): 'out'})
    if request.form['function'] == 'open_register':
      return 'open register'
    if request.form['function'] == 'admin':
      return redirect('/admin/' + session_key)
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
  timesheet = db.timesheets.find_one({'username': username, 'pay_period': current_pay_period})
  if timesheet is not None:
    worked_hours = str(calculate_worked_hours(timesheet))

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
  if result['success'] == False:
    return redirect('/')
  username = result['username']
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/landing/' + session_key)
    elif request.form['function'] == 'change_password':
      return redirect('/change_password/' + session_key)
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/' + session_key)
    elif request.form['function'] == 'global_config':
      return redirect('/global_config/' + session_key)
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  return render_template('admin.html', instance_name=instance_name, assets_url=assets_url, username=result['username'], session_key=session_key, permissions=permissions)  

@app.route('/item_management/<session_key>', methods=['POST', 'GET'])
def item_management(session_key):
  result = validate_session_key(db, session_key)
  message = None
  scanned_item = None
  supplier_list= []
  locations_collection = []
  cost_per = 0.0
  suggested_margin = 0.0
  supplier_list= get_supplier_list(db)
  if result['success'] == False:
    return redirect('/')
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  username = result['username']
  permissions = []
  permissions = employee_info['permissions']
  item_group_list = get_item_group_list(db)
  location_list = get_location_list(db)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/landing/' + session_key)
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/' + session_key)
    elif request.form['function'] == 'admin':
      return redirect('/admin/' + session_key)
    elif request.form['function'] == 'scan':
      scanned_item = db.inventory.find_one({'item_id' : request.form['scan']})
      if scanned_item is None:
        scanned_barcode = request.form['scan']
        #  TO DO:  VALIDATE THIS INPUT BEFORE ACTING
        return render_template('create_new_item.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, scan=scanned_barcode, supplier_list=supplier_list, location_list=location_list, permissions=permissions)
     
        
    elif request.form['function'] == 'create_new_item':
      today = date.today()
      today_string = today.strftime('%m/%d/%y')
      scanned_barcode = request.form['scan']
      scanned_item = {'item_id': scanned_barcode, 'name': 'New Item Name', 'description': 'New Item Description', 'receipt_alias': 'New Item Receipt Alias', 'memo': '', 'unit': 'each', 'supplier': '', 'order_code': '', 'case_quantity': 1, 'case_cost': 0.01, 'item_groups': [], 'department': '', 'category': '', 'subcategory': '', 'brand': '', 'local': False, 'discontinued': False, 'active': True, 'online_ordering': 'yes', 'employee_discount': config['employee_discount'], 'suggested_retail_price': 0.01, 'age_restricted': 0, 'food_item': True, 'date_added': today_string, 'random_weight_per': False, 'break_pack_upc': '', 'break_pack_quantity': 0.0, 'wic_eligible': False}
      db.inventory.insert_one(scanned_item)
      locations_to_add_to = request.form.getlist('add_to_location[]')
      for i in locations_to_add_to:
        collection = db.inventory_management.find_one({'type': 'location', 'location_id': i})
        default_taxes = collection['default_taxes']
        locations_collection.append({'location_id': i, 'quantity_on_hand': 1.0, 'quantity_low': 0.0, 'quantity_high': 1.0, 'most_recent_delivery': today_string, 'regular_price': 0.01, 'taxes': default_taxes, 'item_location': '', 'backstock_location': ''})
      scanned_item['locations'] = locations_collection
      db.inventory.update_one({'item_id': scanned_barcode}, {'$set': {'locations': locations_collection}})
    
    elif request.form['function'] == 'delete_item':
      db.inventory.delete_one({'item_id': request.form['item_id']})
    elif request.form['function'] == 'change_name':
      if is_valid_string(request.form['name']) == False:
        message = 'Invalid name'
      elif len(request.form['name']) < 6:
        message = 'Name too short, must be 6 or more characters'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'name': request.form['name']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_description':
      if is_valid_string(request.form['description']) == False:
        message = 'Invalid description'
      elif len(request.form['description']) < 6:
        message = 'Description too short, must be 6 or more characters'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'description': request.form['description']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_receipt_alias':
      if is_valid_string(request.form['receipt_alias']) == False:
        message = 'Invalid receipt alias'
      elif len(request.form['receipt_alias']) < 3:
        message = 'Receipt alias too short, must be 3 or more characters'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'receipt_alias': request.form['receipt_alias']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_memo':
      if is_valid_string(request.form['memo']) == False:
        message = 'Invalid memo'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'memo': request.form['memo']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_case_cost':
      if is_valid_price(request.form['case_cost']) == False:
        message = 'Invalid price'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'case_cost': price_to_float(request.form['case_cost'])}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_case_quantity':
      valid = False
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
      if scanned_item['unit'] == 'each':
        if is_valid_int(request.form['case_quantity']) == False:
          message = 'Invalid quantity, must be whole number'
        else:
          valid = True
      else:
        if is_valid_float(request.form['case_quantity']) == False:
          message = 'Invalid quantity, must be a valid number'
        else:
          valid = True
      if valid == True:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'case_quantity': float(request.form['case_quantity'])}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_suggested_retail_price':
      if is_valid_price(request.form['suggested_retail_price']) == False:
        message = 'Invalid price'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'suggested_retail_price': price_to_float(request.form['suggested_retail_price'])}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_regular_price':
      if is_valid_price(request.form['regular_price']) == False:
        message = 'Invalid price'
      else:
        locations_collection = get_item_locations_collection(db, request.form['item_id'])
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['regular_price'] = price_to_float(request.form['regular_price'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'locations': new_locations_collection}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_quantity_on_hand':
      valid = False
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
      if scanned_item['unit'] == 'each':
        if is_valid_int(request.form['quantity_on_hand']) == False:
          message = 'Invalid quantity, must be whole number'
        else:
          valid = True
      else:
        if is_valid_float(request.form['quantity_on_hand']) == False:
          message = 'Invalid quantity, must be a valid number'
        else:
          valid = True
      if valid == True:
        locations_collection = get_item_locations_collection(db, request.form['item_id'])
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['quantity_on_hand'] = float(request.form['quantity_on_hand'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'locations': new_locations_collection}})
        scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_most_recent_delivery':
      if is_valid_date(request.form['most_recent_delivery']) == False:
        message = 'Invalid date'
      else:
        locations_collection = get_item_locations_collection(db, request.form['item_id'])
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['most_recent_delivery'] = request.form['most_recent_delivery']
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'locations': new_locations_collection}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_quantity_low':
      valid = False
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
      if scanned_item['unit'] == 'each':
        if is_valid_int(request.form['quantity_low']) == False:
          message = 'Invalid quantity, must be whole number'
        else:
          valid = True
      else:
        if is_valid_float(request.form['quantity_low']) == False:
          message = 'Invalid quantity, must be a valid number'
        else:
          valid = True
      if valid == True:
        locations_collection = get_item_locations_collection(db, request.form['item_id'])
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['quantity_low'] = float(request.form['quantity_low'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'locations': new_locations_collection}})
        scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_quantity_high':
      valid = False
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
      if scanned_item['unit'] == 'each':
        if is_valid_int(request.form['quantity_high']) == False:
          message = 'Invalid quantity, must be whole number'
        else:
          valid = True
      else:
        if is_valid_float(request.form['quantity_high']) == False:
          message = 'Invalid quantity, must be a valid number'
        else:
          valid = True
      if valid == True:
        locations_collection = get_item_locations_collection(db, request.form['item_id'])
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['quantity_high'] = float(request.form['quantity_high'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'locations': new_locations_collection}})
        scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_item_location':
      if is_valid_string(request.form['item_location']) == False:
        message = 'Invalid string'
      else:
        locations_collection = get_item_locations_collection(db, request.form['item_id'])
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['item_location'] = request.form['item_location']
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'locations': new_locations_collection}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_backstock_location':
      if is_valid_string(request.form['backstock_location']) == False:
        message = 'Invalid string'
      else:
        locations_collection = get_item_locations_collection(db, request.form['item_id'])
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['backstock_location'] = request.form['backstock_location']
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'locations': new_locations_collection}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_unit':
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'unit': request.form['unit']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_supplier':
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'supplier': request.form['supplier_id']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_order_code':
      if is_valid_string(request.form['order_code']) == False:
        message = 'Invalid order code'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'order_code': request.form['order_code']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_department':
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'department': request.form['department']}})
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'category': ''}})
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'subcategory': ''}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_category':
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'category': request.form['category']}})
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'subcategory': ''}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_subcategory':
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'subcategory': request.form['subcategory']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_brand':
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'brand': request.form['brand']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'create_new_item_group':
      if is_valid_string(request.form['item_group_id']) == False:
        message = 'invalid group name'
      elif request.form['item_group_id'] in item_group_list:
        message = 'group already exists'
      else:
        itemlist = []
        itemlist.append(request.form['item_id'])
        db.inventory_management.insert_one({'type': 'item_group', 'item_group_id': request.form['item_group_id'], 'items': itemlist})
        scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
        grouplist = []
        grouplist = scanned_item['item_groups']
        grouplist.append(request.form['item_group_id'])
        item_group_list.append(request.form['item_group_id'])
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'item_groups': grouplist}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
 
    elif request.form['function'] == 'remove_from_item_group':
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
      grouplist = []
      grouplist = scanned_item['item_groups']
      grouplist.remove(request.form['item_group_id'])
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'item_groups': grouplist}})
      document = db.inventory_management.find_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']})
      item_list = []
      item_list = document['items']
      item_list.remove(request.form['item_id'])
      db.inventory_management.update_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']}, {'$set': {'items': item_list}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'add_to_item_group':
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
      grouplist = []
      grouplist = scanned_item['item_groups']
      grouplist.append(request.form['item_group_id'])
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'item_groups': grouplist}})
      document = db.inventory_management.find_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']})
      item_list = []
      item_list = document['items']
      item_list.append(request.form['item_id'])
      db.inventory_management.update_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']}, {'$set': {'items': item_list}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})

    elif request.form['function'] == 'change_local':
      if request.form['local'] == 'True':
        local_bool = True
      else:
        local_bool = False
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'local': local_bool}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_online_ordering':
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'online_ordering': request.form['online_ordering']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_discontinued':
      if request.form['discontinued'] == 'True':
        discontinued_bool = True
      else:
        discontinued_bool = False
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'discontinued': discontinued_bool}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_food_item':
      if request.form['food_item'] == 'True':
        food_item_bool = True
      else:
        food_item_bool = False
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'food_item': food_item_bool}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_random_weight_per':
      if request.form['random_weight_per'] == 'True':
        random_weight_per_bool = True
      else:
        random_weight_per_bool = False
      db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'random_weight_per': random_weight_per_bool}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_age_restricted':
      if is_valid_int(request.form['age_restricted']) == False:
        message = 'invalid age'
      else:
        age_int = int(request.form['age_restricted'])
        if age_int < 0 or age_int > 21:
          message = 'invalid age'
        else:
          db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'age_restricted': age_int}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_break_pack_item_id':
      break_pack_item = db.inventory.find_one({'item_id': request.form['break_pack_item_id']})
      if break_pack_item == None:
        message = 'Item not in system'
      else:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'break_pack_item_id': request.form['break_pack_item_id']}})
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
    elif request.form['function'] == 'change_break_pack_quantity':
      valid = False
      scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})
      if scanned_item['unit'] == 'each':
        if is_valid_int(request.form['break_pack_quantity']) == False:
          message = 'Invalid quantity, must be whole number'
        else:
          valid = True
      else:
        if is_valid_float(request.form['break_pack_quantity']) == False:
          message = 'Invalid quantity, must be a valid number'
        else:
          valid = True
      if valid == True:
        db.inventory.update_one({'item_id': request.form['item_id']}, {'$set': {'break_pack_quantity': float(request.form['break_pack_quantity'])}})
        scanned_item = db.inventory.find_one({'item_id' : request.form['item_id']})

  
  if scanned_item is not None:
    groups_item_is_in = []
    groups_item_is_in = scanned_item['item_groups']
    for group in groups_item_is_in:
      item_group_list.remove(group)
    scanned_item = beautify_item(db, scanned_item)


  return render_template('item_management.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, scanned_item=scanned_item, supplier_list=supplier_list, item_group_list=item_group_list, location_list=location_list, permissions=permissions, locations_collection=locations_collection, cost_per=cost_per, suggested_margin=suggested_margin, message=message)


@app.route('/inventory_management/<session_key>', methods=['POST', 'GET'])
def inventory_management(session_key):
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')
  message = None
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'inventory_management' not in permissions:
    return redirect('/landing/' + session_key)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/landing/' + session_key)
    elif request.form['function'] == 'admin':
      return redirect('/admin/' + session_key)
    elif request.form['function'] == 'item_management':
      return redirect('/item_management/' + '/' + session_key)
    elif request.form['function'] == 'supplier_management':
      return redirect('/supplier_management/' +  session_key)
    elif request.form['function'] == 'department_management':
      return redirect('/department_management/' + session_key)
    elif request.form['function'] == 'brand_management':
      return redirect('/brand_management/' + session_key)
      
  return render_template('inventory_management.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, permissions=permissions, message=message)

@app.route('/supplier_management/<session_key>', methods=['POST', 'GET'])
def supplier_management(session_key):
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')
  message = None
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'inventory_management' not in permissions:
    return redirect('/landing/' + session_key)
  suppliers_collection = []
  suppliers_collection = get_supplier_collection(db)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/landing/' + session_key)
    elif request.form['function'] == 'admin':
      return redirect('/admin/' + session_key)
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/' + session_key)
    elif request.form['function'] == 'change_website':
      supplier_id = request.form['supplier_id']
      website = request.form['website']
      if is_valid_string(website) == True:
      # TO DO: VALIDATE THIS INPUT
        db.inventory_management.update_one({'type': 'supplier', 'supplier_id': supplier_id}, {'$set': {'website': website}})
        suppliers_collection = get_supplier_collection(db)
      else:
        message = 'Error: invalid characters in website'
    elif request.form['function'] == 'change_phone':
      supplier_id = request.form['supplier_id']
      phone = request.form['phone']
      if is_valid_string(phone) == True:
      # TO DO: VALIDATE THIS INPUT
        db.inventory_management.update_one({'type': 'supplier', 'supplier_id': supplier_id}, {'$set': {'phone': phone}})
        suppliers_collection = get_supplier_collection(db)
      else:
        message = 'Error: invalid characters in email'
    elif request.form['function'] == 'change_address':
      supplier_id = request.form['supplier_id']
      address = request.form['address']
      if is_valid_string(address) == True:
      # TO DO: VALIDATE THIS INPUT
        db.inventory_management.update_one({'type': 'supplier', 'supplier_id': supplier_id}, {'$set': {'address': address}})
        suppliers_collection = get_supplier_collection(db)
      else:
        message = 'Error: invalid characters in address'
    elif request.form['function'] == 'change_contact_name':
      supplier_id = request.form['supplier_id']
      contact_name = request.form['contact_name']
      if is_valid_string(contact_name) == True:
      # TO DO: VALIDATE THIS INPUT
        db.inventory_management.update_one({'type': 'supplier', 'supplier_id': supplier_id}, {'$set': {'contact_name': contact_name}})
        suppliers_collection = get_supplier_collection(db)
      else:
        message = 'Error: invalid characters in contact name'
    elif request.form['function'] == 'change_email':
      supplier_id = request.form['supplier_id']
      email = request.form['email']
      if is_valid_string(email) == True:
      # TO DO: VALIDATE THIS INPUT
        db.inventory_management.update_one({'type': 'supplier', 'supplier_id': supplier_id}, {'$set': {'email': email}})
        suppliers_collection = get_supplier_collection(db)
      else:
        message = 'Error: invalid characters in email'
    elif request.form['function'] == 'delete_supplier':
      supplier_id = request.form['supplier_id']
      db.inventory_management.delete_one({'type': 'supplier', 'supplier_id': supplier_id})
      suppliers_collection = get_supplier_collection(db)
    elif request.form['function'] == 'create_supplier':
      supplier_id = request.form['supplier_id']
      website = request.form['website']
      phone = request.form['phone']
      address = request.form['address']
      contact_name = request.form['contact_name']
      email = request.form['email']
      if len(supplier_id) < 6:
        message = 'Error: Supplier name must be 6 or more characters'
      elif is_valid_string(supplier_id) == False:
        message = 'Error: invalid character in supplier name'
      elif is_valid_string(website) == False:
        message = 'Error: invalid character in website'
      elif is_valid_string(phone) == False:
        message = 'Error: invalid character in phone'
      elif is_valid_string(address) == False:
        message = 'Error: invalid character in address'
      elif is_valid_string(contact_name) == False:
        message = 'Error: invalid character in contact name'
      elif is_valid_string(email) == False:
        message = 'Error: invalid character in email'
      else:
        try:
          db.inventory_management.insert_one({'type': 'supplier', 'supplier_id': supplier_id, 'website': website, 'phone': phone, 'address': address, 'contact_name': contact_name, 'email': email})
        except:
          message = 'Error inserting document into collection'
        else:
          suppliers_collection = get_supplier_collection(db)
  return render_template('supplier_management.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, permissions=permissions, suppliers_collection=suppliers_collection, message=message)



@app.route('/department_management/<session_key>', methods=['POST', 'GET'])
def department_management(session_key):
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return redirect('/')
  message = None
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'inventory_management' not in permissions:
    return redirect('/landing/' + session_key)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/landing/' + session_key)
    elif request.form['function'] == 'admin':
      return redirect('/admin/' + session_key)
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/' + session_key)
  return render_template('department_management.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, permissions=permissions, message=message)