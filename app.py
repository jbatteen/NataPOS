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
from calculations_and_conversions import calculate_worked_hours
from is_valid import is_valid_username, is_valid_password, is_valid_date, is_date_within_range, is_valid_pay_period_rollover, is_date_in_future, is_valid_string
from inventory_functions import get_item_group_list, get_supplier_list, get_supplier_collection, get_location_list, get_item_locations_collection, get_locations_collection, calculate_item_locations_collection




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
    db.natapos.insert_one({'config': 'global', 'instance_name': 'NataPOS', 'pay_period_type': 'biweekly', 'current_pay_period': current_pay_period, 'tax_types': ['Sales Tax', 'Alcohol Tax'], 'pay_period_rollover': 15})



  
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
        db.inventory_management.insert_one({'type': 'location', 'location_id': location_id})
        creation_check = {}
        creation_check = create_user(db, username, password, ['superuser'])
        if creation_check['success'] == True:
          result = {}
          result = validate_login(db, username=username, password=password)
          session_key = ''
          if result['success'] == True:
            session_key = result['session_key']
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
  config = db.natapos.find_one({'config': 'global'})
  tax_types = []
  tax_types = config['tax_types']
  pay_period_type = config['pay_period_type']
  instance_name = config['instance_name']
  current_pay_period = config['current_pay_period']
  pay_period_rollover = config['pay_period_rollover']

  return render_template('instance_config.html', instance_name=instance_name, assets_url=assets_url, session_key=session_key, pay_period_type=pay_period_type, current_pay_period=current_pay_period, current_pay_period_start=current_pay_period.split('-')[0], pay_period_rollover=pay_period_rollover, message=message, tax_types=tax_types)
    

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
      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': current_pay_period})
      if timesheet is not None:
        db.timesheets.update_one({'username': username, 'pay_period': current_pay_period}, {'$set': {str(current_time): 'in'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': current_pay_period, 'worked_hours': 0.0, str(current_time): 'in'})
    if request.form['function'] == 'clock_out':
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
    elif request.form['function'] == 'instance_config':
      return redirect('/instance_config/' + session_key)
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  return render_template('admin.html', instance_name=instance_name, assets_url=assets_url, username=result['username'], session_key=session_key, permissions=permissions)  

@app.route('/item_management/<session_key>', methods=['POST', 'GET'])
def item_management(session_key):
  result = validate_session_key(db, session_key)
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
      scanned_barcode = request.form['scan']
      scanned_item = {'item_id': scanned_barcode, 'name': 'New Item Name', 'description': 'New Item Description', 'receipt_alias': 'New Item Receipt Alias', 'memo': '', 'unit': 'each', 'supplier': '', 'order_code': '', 'case_quantity': 1, 'case_cost': 0.01, 'item_groups': [], 'department': '', 'category': '', 'brand': '', 'local': False, 'discontinued': False, 'employee_discount': 0.3, 'suggested_retail_price': 0.01, 'age_restricted': 0}
      db.inventory.insert_one(scanned_item)
      locations_to_add_to = request.form.getlist('add_to_location[]')
      for i in locations_to_add_to:
        today = date.today()
        today_string = today.strftime('%m/%d/%Y')
        locations_collection.append({'location_id': i, 'quantity_on_hand': 1.0, 'quantity_low': 0.0, 'quantity_high': 1.0, 'most_recent_delivery': today_string, 'regular_price': 0.01})
      scanned_item['locations'] = locations_collection
      db.inventory.update_one({'item_id': scanned_barcode}, {'$set': {'locations': locations_collection}})
    
    elif request.form['function'] == 'delete_item':
      db.inventory.delete_one({'item_id': request.form['item_id']})
  
  if scanned_item is not None:
        cost_per = scanned_item['case_cost'] / scanned_item['case_quantity']
        cost_per = round(cost_per, 2)
        suggested_margin = (scanned_item['suggested_retail_price'] / cost_per) - 1
        locations_collection = calculate_item_locations_collection(scanned_item['locations'], cost_per)


  return render_template('item_management.html', instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, scanned_item=scanned_item, supplier_list=supplier_list, item_group_list=item_group_list, location_list=location_list, permissions=permissions, locations_collection=locations_collection, cost_per=cost_per, suggested_margin=suggested_margin)


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
