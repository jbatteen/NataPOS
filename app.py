# import libraries
from flask import Flask, render_template, request, redirect, jsonify, make_response
import time
import bcrypt
import ipaddress
import os
import csv
from werkzeug.utils import secure_filename

from datetime import date
from pymongo.mongo_client import MongoClient


# import local files
from config import db_name, mongo_url, assets_url
from authentication_functions import validate_login, validate_session_key, create_user
from calculations_and_conversions import calculate_worked_hours, price_to_float, percent_to_float, float_to_price
from is_valid import is_valid_username, is_valid_password, is_valid_date, is_date_within_range, is_valid_pay_period_rollover, is_date_in_future, is_valid_string, is_valid_price, is_valid_float, is_valid_int, is_valid_percent, is_allowed_file
from inventory_functions import get_item_group_list, get_supplier_list, get_supplier_collection, get_location_list, get_item_locations_collection, get_locations_collection, calculate_item_locations_collection, beautify_item, get_department_list, get_department_collection, get_brand_collection, get_brand_list, print_shelf_tag


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
    db.natapos.insert_one({'config': 'global', 'instance_name': 'NataPOS', 'current_pay_period_start': date.today().strftime('%m/%d/%y'), 'timesheets_locked': False, 'employee_discount': 0.2})

  
# begin app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/var/www/NataPOS/uploads'

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
       
        db.natapos.update_one({'config': 'global'}, {'$set': {'instance_name': instance_name, 'phone': '', 'address':'', 'taxes': [{'tax_id': 'exempt', 'rate': 0.0}], 'default_taxes': []}})
        creation_check = {}
        creation_check = create_user(db, username, password, ['superuser'], '', '', '', '', '', '', '')
        if creation_check['success'] == True:
          result = {}


          if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            source_ip = request.environ['REMOTE_ADDR']
          else:
            source_ip = request.environ['HTTP_X_FORWARDED_FOR']
          result = validate_login(db, username=username, password=password, source_ip=source_ip)
          if result['success'] == True:
            response = redirect('/global_config/')
            response.set_cookie('natapos_session_key', result['session_key'])
            return response
          else:
            return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message='validation error')
        else:
          return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url, message=creation_check['error'])
      else: # if it does exist and someone called this page anyway
        return('nice try') # someone spoofed
  else:
    return render_template('create_first_user.html', instance_name=instance_name, assets_url=assets_url)

@app.route('/global_config/', methods=['POST', 'GET'])
def global_config():
  message = None
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/global_config/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions:
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
    elif request.form['function'] == 'change_current_pay_period_start':
      if is_valid_date(request.form['current_pay_period_start']) == False:
        message = 'Error: invalid date'
      elif is_date_within_range(request.form['current_pay_period_start'], 13) == True and is_date_in_future(request.form['current_pay_period_start']) == False:
        db.natapos.update_one({'config': 'global'}, {'$set': {'current_pay_period_start': request.form['current_pay_period_start']}})
      else:
        message = 'Error: date out of range'
        
    elif request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'change_employee_discount':
      if is_valid_percent(request.form['employee_discount']) == False:
        message = 'invalid percentage'
      else:
        new_employee_discount = percent_to_float(request.form['employee_discount'])
        if new_employee_discount < 0:
          message = 'percentage must be non-negative'
        else: db.natapos.update_one({'config': 'global'}, { '$set': {'employee_discount': new_employee_discount}})
    elif request.form['function'] == 'remove_default_tax':
      default_taxes = config['default_taxes']
      default_taxes.remove(request.form['tax_id'])
      result = db.natapos.update_one({'config': 'global'}, {'$set': {'default_taxes': default_taxes}})   
    elif request.form['function'] == 'add_default_tax':
      default_taxes = []
      if request.form['tax_id'] == 'exempt':
        default_taxes = ['exempt']
      else:
        default_taxes = config['default_taxes']
        if default_taxes == ['exempt']:
          default_taxes = []
        default_taxes.append(request.form['tax_id'])
      result = db.natapos.update_one({'config': 'global'}, {'$set': {'default_taxes': default_taxes}})
    elif request.form['function'] == 'create_tax':
      if is_valid_percent(request.form['tax_rate']) == False:
        message = 'Invalid percentage'
      elif is_valid_string(request.form['tax_id']) == False:
        message = 'Invalid tax ID'
      elif request.form['tax_id'].casefold() == 'exempt':
        message = 'exempt is a special keyword, choose another name'
      else:
        taxes = []
        taxes = config['taxes']
        valid = True
        for i in taxes:
          if i['tax_id'] == request.form['tax_id']:
            message = 'tax already exists'
            valid = False
        if valid == True:
          new_tax = {}
          new_tax['tax_id'] = request.form['tax_id']
          tax_rate = 0.0
          tax_rate = percent_to_float(request.form['tax_rate'])
          new_tax['rate'] = tax_rate
          taxes.append(new_tax)
          result = db.natapos.update_one({'config': 'global'}, {'$set': {'taxes': taxes}})
    elif request.form['function'] == 'delete_tax':
      if request.form['tax_id'].casefold() == 'exempt':
        message = 'cannot delete exempt'
      else:
        result = db.natapos.update_one({'config': 'global'}, {'$pullAll': {'taxes': [{'tax_id': request.form['tax_id'], 'rate': float(request.form['rate'])}]}})
    elif request.form['function'] == 'change_tax_rate':
      if is_valid_percent(request.form['rate']) == False:
        message = 'invalid tax rate'
      else:
        new_rate = percent_to_float(request.form['rate'])
        if new_rate <= 0:
          message = 'tax rate must be above zero'
        else:
          taxes = config['taxes']
          new_taxes = []
          for i in taxes:
            if i['tax_id'] == request.form['tax_id']:
              new_taxes.append({'tax_id': request.form['tax_id'], 'rate': new_rate})
            else:
              new_taxes.append(i)
          result = db.natapos.update_one({'config': 'global'}, {'$set': {'taxes': new_taxes}})

    elif request.form['function'] == 'change_phone':
      if is_valid_string(request.form['phone']) == True:
        db.natapos.update_one({'config': 'global'}, {'$set': {'phone': request.form['phone']}})
      else:
        message = 'invalid phone number'
    elif request.form['function'] == 'change_address':
      if is_valid_string(request.form['address']) == True:
        db.natapos.update_one({'config': 'global'}, {'$set': {'address': request.form['address']}})
      else:
        message = 'invalid address'
    config = db.natapos.find_one({'config': 'global'})
  employee_discount = str(round((config['employee_discount'] * 100), 5))
  employee_discount = employee_discount + '%'
  return render_template('global_config.html', instance_name=config['instance_name'], assets_url=assets_url, session_key=session_key, current_pay_period_start=config['current_pay_period_start'], employee_discount=employee_discount, message=message, taxes=config['taxes'], default_taxes=config['default_taxes'], phone=config['phone'], address=config['address'])
    

@app.route('/', methods=['POST', 'GET'])
def landing():
  message = ''
  config = db.natapos.find_one({'config': 'global'})
  session_key = request.cookies.get('natapos_session_key')
  if request.method == 'GET':
    try:
      db.validate_collection("employees")
    except:
      return redirect('/create_first_user')
  if request.method == 'POST':
    
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False: # invalid combo, send back to main page
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  
  username = result['username']
  if request.method == 'POST':
    if request.form['function'] == 'clock_in':
      while config['timesheets_locked'] == True:
        time.sleep(1)
        config = db.natapos.find_one({'config': 'global'})

      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
      if timesheet is not None:
        db.timesheets.update_one({'username': username, 'pay_period': 'current'}, {'$set': {str(current_time): 'in'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': 'current', str(current_time): 'in'})
    if request.form['function'] == 'clock_out':
      while config['timesheets_locked'] == True:
        time.sleep(1)
        config = db.natapos.find_one({'config': 'global'})
      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
      if timesheet is not None:
        db.timesheets.update_one({'username': username, 'pay_period': 'current'}, {'$set': {str(current_time): 'out'}})
      else:
        db.timesheets.insert_one({'username': username, 'pay_period': 'current', str(current_time): 'out'})
    if request.form['function'] == 'open_register':
      return 'open register'
    if request.form['function'] == 'admin':
      return redirect('/admin/')
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
  employee_document = db.employees.find_one({'type': 'user', 'username': username})
  message = employee_document['login_message']
  timesheet = db.timesheets.find_one({'username': username, 'pay_period': 'current'})
  if timesheet is not None:
    del timesheet['username']
    del timesheet['_id']
    del timesheet['pay_period']
    timestamps = sorted(timesheet)
    last_punch = timesheet[timestamps[-1]]
    
    if len(timesheet) > 1:
      second_to_last_punch = timesheet[timestamps[-2]]
      if last_punch == second_to_last_punch:
        message = message + "<br><br>Missing punch, see a manager.<br><br>Second to last punch: " + second_to_last_punch + " " + time.ctime(int(timestamps[-2]))
    message = message + '<br/><br/>Last punch: ' + last_punch + " " + time.ctime(int(timestamps[-1]))
    if last_punch == 'in':
      timesheet[str(int(round(time.time())))] = 'out'
    message = message + '<br/><br/>' + str(round(calculate_worked_hours(timesheet), 2)) + ' hours on this pay period'
  else:
    message = message + '<br/><br/>First day on this pay period'
  

  return render_template('landing.html', instance_name=config['instance_name'], assets_url=assets_url, username=username, session_key=session_key, message=message)

@app.route('/admin/', methods=['POST', 'GET'])
def admin():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/admin/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:    
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  username = result['username']
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'change_password':
      return redirect('/change_password/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'employee_management':
      return redirect('/employee_management/')
    elif request.form['function'] == 'global_config':
      return redirect('/global_config/')
    elif request.form['function'] == 'supplier_management':
      return redirect('/supplier_management/')
    elif request.form['function'] == 'department_list':
      return redirect('/department_list/')
    elif request.form['function'] == 'brand_management':
      return redirect('/brand_management/')
    elif request.form['function'] == 'import_data':
      return redirect('/import_data/')
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  return render_template('admin.html', instance_name=instance_name, assets_url=assets_url, username=result['username'], session_key=session_key, permissions=permissions)  


@app.route('/inventory_management/', methods=['POST', 'GET'])
def scan_search():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/inventory_management/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  message = None
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url,)
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  username = result['username']
  permissions = []
  permissions = employee_info['permissions']
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'scan':
      return redirect('/edit_item/' + request.form['scan'] + '/')
  return render_template('scan_item.html', instance_name=instance_name, assets_url=assets_url, username=username, permissions=permissions, message=message)

@app.route('/inventory_management/<item_id>/', methods=['POST', 'GET'])
def inventory_management(item_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/inventory_management/' + item_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  username = result['username']
  message = None
  supplier_list= []
  cost_per = 0.0
  suggested_margin = 0.0
  supplier_list= get_supplier_list(db)
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  locations_collection = []
  permissions = []
  permissions = employee_info['permissions']
  if 'inventory_management' not in permissions and 'superuser' not in permissions:
    return redirect('/')
  scanned_item = db.inventory.find_one({'item_id' : item_id})
  if scanned_item is None:
    return redirect('/create_item/' + item_id + '/')
  item_group_list = get_item_group_list(db)
  not_carried_location_list = []
  #location_list = get_location_list(db)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'scan':
      scanned_item = db.inventory.find_one({'item_id' : request.form['scan']})
      if scanned_item is None:
        return redirect('/create_item/' + request.form['scan'] + '/')
      else:
        return redirect('/inventory_management/' + request.form['scan'] + '/')
    elif request.form['function'] == 'delete_item':
      db.inventory.delete_one({'item_id': item_id})
    elif request.form['function'] == 'change_name':
      if is_valid_string(request.form['name']) == False:
        message = 'Invalid name'
      elif len(request.form['name']) < 6:
        message = 'Name too short, must be 6 or more characters'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'name': request.form['name']}})
    elif request.form['function'] == 'change_description':
      if is_valid_string(request.form['description']) == False:
        message = 'Invalid description'
      elif len(request.form['description']) < 6:
        message = 'Description too short, must be 6 or more characters'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'description': request.form['description']}})
    elif request.form['function'] == 'change_receipt_alias':
      if is_valid_string(request.form['receipt_alias']) == False:
        message = 'Invalid receipt alias'
      elif len(request.form['receipt_alias']) < 3:
        message = 'Receipt alias too short, must be 3 or more characters'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'receipt_alias': request.form['receipt_alias']}})
    elif request.form['function'] == 'change_memo':
      if is_valid_string(request.form['memo']) == False:
        message = 'Invalid memo'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'memo': request.form['memo']}})
    elif request.form['function'] == 'change_case_cost':
      if is_valid_price(request.form['case_cost']) == False:
        message = 'Invalid price'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'case_cost': price_to_float(request.form['case_cost'])}})
    elif request.form['function'] == 'change_case_quantity':
      valid = False
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
        case_quantity = float(request.form['case_quantity'])
        if case_quantity <= 0.0:
          message = 'case quantity must be above zero'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'case_quantity': case_quantity}})
      scanned_item = db.inventory.find_one({'item_id' : item_id})
    elif request.form['function'] == 'change_suggested_retail_price':
      if is_valid_price(request.form['suggested_retail_price']) == False:
        message = 'Invalid price'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'suggested_retail_price': price_to_float(request.form['suggested_retail_price'])}})
    elif request.form['function'] == 'change_regular_price':
      if is_valid_price(request.form['regular_price']) == False:
        message = 'Invalid price'
      else:
        locations_collection = get_item_locations_collection(db, item_id)
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['regular_price'] = price_to_float(request.form['regular_price'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_quantity_on_hand':
      valid = False
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
        locations_collection = get_item_locations_collection(db, item_id)
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['quantity_on_hand'] = float(request.form['quantity_on_hand'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_most_recent_delivery':
      if is_valid_date(request.form['most_recent_delivery']) == False:
        message = 'Invalid date'
      else:
        locations_collection = get_item_locations_collection(db, item_id)
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['most_recent_delivery'] = request.form['most_recent_delivery']
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_quantity_low':
      valid = False
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
        locations_collection = get_item_locations_collection(db, item_id)
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['quantity_low'] = float(request.form['quantity_low'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_quantity_high':
      valid = False
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
        locations_collection = get_item_locations_collection(db, item_id)
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['quantity_high'] = float(request.form['quantity_high'])
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_item_location':
      if is_valid_string(request.form['item_location']) == False:
        message = 'Invalid string'
      else:
        locations_collection = get_item_locations_collection(db, item_id)
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['item_location'] = request.form['item_location']
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_backstock_location':
      if is_valid_string(request.form['backstock_location']) == False:
        message = 'Invalid string'
      else:
        locations_collection = get_item_locations_collection(db, item_id)
        new_locations_collection = []
        for i in locations_collection:
          if i['location_id'] == request.form['location_id']:
            i['backstock_location'] = request.form['backstock_location']
          new_locations_collection.append(i)
        db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_active':
      if request.form['active'] == 'True':
        active_bool = True
      else:
        active_bool = False
      locations_collection = get_item_locations_collection(db, item_id)
      new_locations_collection = []
      for i in locations_collection:
        if i['location_id'] == request.form['location_id']:
          i['active'] = active_bool
        new_locations_collection.append(i)
      db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'remove_tax':
      locations_collection = get_item_locations_collection(db, item_id)
      new_locations_collection = []
      for i in locations_collection:
        if i['location_id'] == request.form['location_id']:
          tax_list = i['taxes']
          tax_list.remove(request.form['tax_id'])
          i['taxes'] = tax_list
        new_locations_collection.append(i)
      db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'add_tax':
      locations_collection = get_item_locations_collection(db, item_id)
      new_locations_collection = []      
      for i in locations_collection:
        if i['location_id'] == request.form['location_id']:
          if request.form['tax_id'] == 'exempt':
            i['taxes'] = ['exempt']
          else:
            tax_list = i['taxes']
            if 'exempt' in tax_list:
              tax_list.remove('exempt')
            tax_list.append(request.form['tax_id'])
            i['taxes'] = tax_list
        new_locations_collection.append(i)
      db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    elif request.form['function'] == 'change_unit':
      db.inventory.update_one({'item_id': item_id}, {'$set': {'unit': request.form['unit']}})
    elif request.form['function'] == 'change_supplier':
      db.inventory.update_one({'item_id': item_id}, {'$set': {'supplier': request.form['supplier_id']}})
    elif request.form['function'] == 'change_order_code':
      if is_valid_string(request.form['order_code']) == False:
        message = 'Invalid order code'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'order_code': request.form['order_code']}})
    elif request.form['function'] == 'change_department':
      db.inventory.update_one({'item_id': item_id}, {'$set': {'department': request.form['department_id']}})
      db.inventory.update_one({'item_id': item_id}, {'$set': {'category': ''}})
      db.inventory.update_one({'item_id': item_id}, {'$set': {'subcategory': ''}})
    elif request.form['function'] == 'change_category':
      db.inventory.update_one({'item_id': item_id}, {'$set': {'category': request.form['category_id']}})
      db.inventory.update_one({'item_id': item_id}, {'$set': {'subcategory': ''}})
    elif request.form['function'] == 'change_subcategory':
      db.inventory.update_one({'item_id': item_id}, {'$set': {'subcategory': request.form['subcategory_id']}})
    elif request.form['function'] == 'change_brand':
      db.inventory.update_one({'item_id': item_id}, {'$set': {'brand': request.form['brand_id']}})
    elif request.form['function'] == 'create_new_item_group':
      if is_valid_string(request.form['item_group_id']) == False:
        message = 'invalid group name'
      elif request.form['item_group_id'] in item_group_list:
        message = 'group already exists'
      else:
        itemlist = []
        itemlist.append(item_id)
        db.inventory_management.insert_one({'type': 'item_group', 'item_group_id': request.form['item_group_id'], 'items': itemlist})
        grouplist = []
        grouplist = scanned_item['item_groups']
        grouplist.append(request.form['item_group_id'])
        item_group_list.append(request.form['item_group_id'])
        db.inventory.update_one({'item_id': item_id}, {'$set': {'item_groups': grouplist}})
 
    elif request.form['function'] == 'remove_from_item_group':
      grouplist = []
      grouplist = scanned_item['item_groups']
      grouplist.remove(request.form['item_group_id'])
      db.inventory.update_one({'item_id': item_id}, {'$set': {'item_groups': grouplist}})
      document = db.inventory_management.find_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']})
      item_list = []
      item_list = document['items']
      item_list.remove(item_id)
      db.inventory_management.update_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']}, {'$set': {'items': item_list}})
    elif request.form['function'] == 'add_to_item_group':
      grouplist = []
      grouplist = scanned_item['item_groups']
      grouplist.append(request.form['item_group_id'])
      db.inventory.update_one({'item_id': item_id}, {'$set': {'item_groups': grouplist}})
      document = db.inventory_management.find_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']})
      item_list = []
      item_list = document['items']
      item_list.append(item_id)
      db.inventory_management.update_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']}, {'$set': {'items': item_list}})

    elif request.form['function'] == 'change_local':
      if request.form['local'] == 'True':
        local_bool = True
      else:
        local_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'local': local_bool}})
    elif request.form['function'] == 'change_organic':
      if request.form['organic'] == 'True':
        organic_bool = True
      else:
        organic_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'organic': organic_bool}})

    elif request.form['function'] == 'change_consignment':
      if request.form['consignment'] == 'True':
        consignment_bool = True
      else:
        consignment_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'consignment': consignment_bool}})
    elif request.form['function'] == 'change_online_ordering':
      locations_collection = get_item_locations_collection(db, item_id)
      new_locations_collection = []
      for i in locations_collection:
        if i['location_id'] == request.form['location_id']:
          i['online_ordering'] = request.form['online_ordering']
        new_locations_collection.append(i)
      db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})

    elif request.form['function'] == 'change_discontinued':
      if request.form['discontinued'] == 'True':
        discontinued_bool = True
      else:
        discontinued_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'discontinued': discontinued_bool}})
    elif request.form['function'] == 'change_food_item':
      if request.form['food_item'] == 'True':
        food_item_bool = True
      else:
        food_item_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'food_item': food_item_bool}})
    elif request.form['function'] == 'change_random_weight_per':
      if request.form['random_weight_per'] == 'True':
        random_weight_per_bool = True
      else:
        random_weight_per_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'random_weight_per': random_weight_per_bool}})
    elif request.form['function'] == 'change_ebt_eligible':
      if request.form['ebt_eligible'] == 'True':
        ebt_eligible_bool = True
      else:
        ebt_eligible_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'ebt_eligible': ebt_eligible_bool}})
    elif request.form['function'] == 'change_wic_eligible':
      if request.form['wic_eligible'] == 'True':
        wic_eligible_bool = True
      else:
        wic_eligible_bool = False
      db.inventory.update_one({'item_id': item_id}, {'$set': {'wic_eligible': wic_eligible_bool}})
    elif request.form['function'] == 'change_age_restricted':
      if is_valid_int(request.form['age_restricted']) == False:
        message = 'invalid age'
      else:
        age_int = int(request.form['age_restricted'])
        if age_int < 0 or age_int > 21:
          message = 'invalid age'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'age_restricted': age_int}})
    elif request.form['function'] == 'change_break_pack_item_id':
      if request.form['break_pack_item_id'] == '':
        db.inventory.update_one({'item_id': item_id}, {'$set': {'break_pack_item_id': request.form['break_pack_item_id']}})
      else:
        break_pack_item = db.inventory.find_one({'item_id': request.form['break_pack_item_id']})
        if break_pack_item == None:
          message = 'Item not in system'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'break_pack_item_id': request.form['break_pack_item_id']}})
    elif request.form['function'] == 'change_break_pack_quantity':
      valid = False
      break_pack_item = db.inventory.find_one({'item_id' : request.form['break_pack_item_id']})
      if break_pack_item['unit'] == 'each':
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
        db.inventory.update_one({'item_id': item_id}, {'$set': {'break_pack_quantity': float(request.form['break_pack_quantity'])}})
    elif request.form['function'] == 'add_to_location':

      collection = db.inventory_management.find_one({'type': 'location', 'location_id': request.form['location_id']})
      default_taxes = collection['default_taxes']
      collection = db.inventory.find_one({'item_id': item_id})
      locations_collection = collection['locations']

      today = date.today()
      today_string = today.strftime('%m/%d/%y')
      locations_collection.append({'location_id': request.form['location_id'], 'quantity_on_hand': 1.0, 'quantity_low': 0.0, 'quantity_high': 1.0, 'most_recent_delivery': today_string, 'regular_price': 0.01, 'taxes': default_taxes, 'item_location': '', 'backstock_location': '', 'last_sold': '', 'active': True})
      result = db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': locations_collection}})
    elif request.form['function'] == 'change_price_by_margin':
      if is_valid_percent(request.form['margin']) == False:
        message = 'Invalid percentage'
      else:
        margin_input = percent_to_float(request.form['margin'])
        if margin_input < 0:
          message = 'margin must be 0 or higher'
        else:
          locations_collection = get_item_locations_collection(db, item_id)
          new_locations_collection = []
          for i in locations_collection:
            if i['location_id'] == request.form['location_id']:
              cost_per = round((scanned_item['case_cost'] / scanned_item['case_quantity']), 2)
              if cost_per == 0.0:
                i['reqular_price'] = 0.0
              else:
                regular_price = round((cost_per + (margin_input * cost_per)), 2)
              i['regular_price'] = regular_price
            new_locations_collection.append(i)
          db.inventory.update_one({'item_id': item_id}, {'$set': {'locations': new_locations_collection}})
    
    elif request.form['function'] == 'change_package_size':
      if is_valid_string(request.form['package_size']) == False:
        message = 'Invalid package size'
      else:
        db.inventory.update_one({'item_id': item_id}, {'$set': {'package_size': request.form['package_size']}})
    if request.form['function'] == 'print_shelf_tag':
      print_shelf_tag(scanned_item, request.form['location_id'])
    else:
      scanned_item = db.inventory.find_one({'item_id' : item_id})
  groups_item_is_in = []
  groups_item_is_in = scanned_item['item_groups']
  for group in groups_item_is_in:
    item_group_list.remove(group)
  scanned_item = beautify_item(db, scanned_item)
  categories = []
  subcategories = []
  if scanned_item['department'] != '':
    department_collection = db.inventory_management.find_one({'type': 'department', 'department_id': scanned_item['department']})
    categories_list = department_collection['categories']
    
    for category in categories_list:
      categories.append(category['category_id'])
      if scanned_item['category'] == category['category_id']:
        subcategories = category['subcategories']
        




  return render_template('inventory_management.html', departments=get_department_list(db), categories=categories, subcategories=subcategories, instance_name=config['instance_name'], assets_url=assets_url, username=username, session_key=session_key, scanned_item=scanned_item, supplier_list=supplier_list, item_group_list=item_group_list, permissions=permissions, cost_per=cost_per, suggested_margin=suggested_margin, message=message, brands=get_brand_list(db), available_taxes=config['taxes'])

@app.route('/edit_item/<item_id>/', methods=['POST', 'GET'])
def edit_item(item_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/edit_item/' + item_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  username = result['username']
  supplier_list= []
  cost_per = 0.0
  suggested_margin = 0.0
  supplier_list= get_supplier_list(db)
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'inventory_management' not in permissions and 'superuser' not in permissions:
    return redirect('/')
  message = ''
  scanned_item = db.inventory.find_one({'item_id' : item_id})
  if scanned_item is None:
    return redirect('/create_item/' + item_id + '/')
  item_group_list = get_item_group_list(db)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'scan':
      scanned_item = db.inventory.find_one({'item_id' : request.form['scan']})
      if scanned_item is None:
        return redirect('/create_item/' + request.form['scan'] + '/')
      else:
        return redirect('/edit_item/' + request.form['scan'] + '/')
    elif request.form['function'] == 'delete_item':
      db.inventory.delete_one({'item_id': item_id})
    elif request.form['function'] == 'update':
      success = False
      beautified = ''
      if request.form['property'] == 'name':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid name'
        elif len(request.form['new_data']) < 6:
          print(request.form['new_data'])
          message = 'Name too short, must be 6 or more characters'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'name': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'memo':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid memo'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'memo': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'case_cost':
        if is_valid_price(request.form['new_data']) == False:
          message = 'Invalid price'
        else:
          price_float = price_to_float(request.form['new_data'])
          db.inventory.update_one({'item_id': item_id}, {'$set': {'case_cost': price_float}})
          success = True
          beautified = float_to_price(price_float)
      elif request.form['property'] == 'case_quantity':
        valid = False
        if scanned_item['unit'] == 'each':
          if is_valid_int(request.form['new_data']) == False:
            message = 'Invalid quantity, must be whole number'
          else:
            valid = True
        else:
          if is_valid_float(request.form['new_data']) == False:
            message = 'Invalid quantity, must be a valid number'
          else:
            valid = True
        if valid == True:
          case_quantity = float(request.form['new_data'])
          if case_quantity <= 0.0:
            message = 'case quantity must be above zero'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'case_quantity': case_quantity}})
            success = True
            beautified = request.form['new_data']
          
      return make_response(jsonify({'success': success, 'message': message, 'beautified': beautified}))
  groups_item_is_in = []
  groups_item_is_in = scanned_item['item_groups']
  for group in groups_item_is_in:
    item_group_list.remove(group)
  scanned_item = beautify_item(db, scanned_item)
  categories = []
  subcategories = []
  if scanned_item['department'] != '':
    department_collection = db.inventory_management.find_one({'type': 'department', 'department_id': scanned_item['department']})
    categories_list = department_collection['categories']
    
    for category in categories_list:
      categories.append(category['category_id'])
      if scanned_item['category'] == category['category_id']:
        subcategories = category['subcategories']
        




  return render_template('edit_item.html',  departments=get_department_list(db), categories=categories, subcategories=subcategories, instance_name=config['instance_name'], assets_url=assets_url, username=username, session_key=session_key, scanned_item=scanned_item, supplier_list=supplier_list, item_group_list=item_group_list, permissions=permissions, cost_per=cost_per, suggested_margin=suggested_margin, message=message, brands=get_brand_list(db), available_taxes=config['taxes'])

@app.route('/create_item/<item_id>/', methods=['POST', 'GET'])
def create_item(item_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/create_item/' + item_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'inventory_management' not in permissions and 'superuser' not in permissions:
    return redirect('/')
  scanned_item = db.inventory.find_one({'item_id' : item_id})
  if scanned_item is not None:
    return redirect('/edit_item/' + item_id + '/')
  
  if request.method == 'POST':
    if request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    if request.form['function'] == 'create_new_item':
      today = date.today()
      today_string = today.strftime('%m/%d/%y')
      if request.form['department_id'] != '':
        department_document = db.inventory_management.find_one({'type': 'department', 'department_id': request.form['department_id']})
        default_employee_discount = department_document['default_employee_discount']
        default_ebt_eligible = department_document['default_ebt_eligible']
        default_food_item = department_document['default_food_item']
        default_taxes = department_document['default_taxes']
      else:
        default_employee_discount = config['employee_discount']
        default_ebt_eligible = False
        default_food_item = True
        default_taxes = config['default_taxes']
      
      if request.form['use_allbid_data'] == 'True':
        allbid_document = db.allbid.find_one({'item_id': item_id})
        scanned_item = {'item_id': item_id, 'name': allbid_document['description'], 'description': allbid_document['description'], 'receipt_alias': allbid_document['description'], 'memo': '', 'unit': 'each', 'supplier': 'UNFI', 'order_code': allbid_document['order_code'], 'consignment': False, 'case_quantity': allbid_document['case_quantity'], 'case_cost': allbid_document['case_cost'], 'item_groups': [], 'department': request.form['department_id'], 'category': '', 'subcategory': '', 'brand': '', 'local': False, 'discontinued': False, 'employee_discount': default_employee_discount, 'suggested_retail_price': allbid_document['suggested_retail_price'], 'age_restricted': 0, 'food_item': default_food_item, 'date_added': today_string, 'random_weight_per': False, 'break_pack_item_id': '', 'break_pack_quantity': 0.0, 'wic_eligible': False, 'ebt_eligible': default_ebt_eligible, 'package_size': allbid_document['package_size'], 'organic': False, 'quantity_on_hand': 1.0, 'quantity_low': 0.0, 'quantity_high': 1.0, 'most_recent_delivery': today_string, 'regular_price': 0.01, 'taxes': default_taxes, 'item_location': '', 'backstock_location': '', 'last_sold': '', 'active': True}
      else:
        scanned_item = {'item_id': item_id, 'name': 'New Item Name', 'description': 'New Item Description', 'receipt_alias': 'New Item Receipt Alias', 'memo': '', 'unit': 'each', 'supplier': '', 'order_code': '', 'consignment': False, 'case_quantity': 1, 'case_cost': 0.01, 'item_groups': [], 'department': request.form['department_id'], 'category': '', 'subcategory': '', 'brand': '', 'local': False, 'discontinued': False, 'employee_discount': default_employee_discount, 'suggested_retail_price': 0.01, 'age_restricted': 0, 'food_item': default_food_item, 'date_added': today_string, 'random_weight_per': False, 'break_pack_item_id': '', 'break_pack_quantity': 0.0, 'wic_eligible': False, 'ebt_eligible': default_ebt_eligible, 'package_size': '', 'organic': False, 'quantity_on_hand': 1.0, 'quantity_low': 0.0, 'quantity_high': 1.0, 'most_recent_delivery': today_string, 'regular_price': 0.01, 'taxes': default_taxes, 'item_location': '', 'backstock_location': '', 'last_sold': '', 'active': True}
      
      db.inventory.insert_one(scanned_item)
      return redirect('/edit_item/' + item_id + '/')
  in_allbid = False
  allbid_document = db.allbid.find_one({'item_id': item_id})
  if allbid_document != None:
    in_allbid = True
  return render_template('create_new_item.html', instance_name=config['instance_name'], assets_url=assets_url, username=username, session_key=session_key, scan=item_id, supplier_list=get_supplier_list(db), location_list=get_location_list(db), department_list=get_department_list(db), permissions=employee_info['permissions'], in_allbid=in_allbid)   

@app.route('/supplier_management/', methods=['POST', 'GET'])
def supplier_management():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/supplier_management/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'suppliers_departments_brands' not in permissions:
    return redirect('/')
  suppliers_collection = []
  suppliers_collection = get_supplier_collection(db)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'change_website':
      supplier_id = request.form['supplier_id']
      website = request.form['website']
      if is_valid_string(website) == True:
      # TO DO: VALIDATE THIS INPUT
        db.inventory_management.update_one({'type': 'supplier', 'supplier_id': supplier_id}, {'$set': {'website': website}})
        suppliers_collection = get_supplier_collection(db)
      else:
        message = 'Error: invalid characters in website'
    elif request.form['function'] == 'change_account':
      supplier_id = request.form['supplier_id']
      account = request.form['account']
      if is_valid_string(account) == True:
      # TO DO: VALIDATE THIS INPUT
        db.inventory_management.update_one({'type': 'supplier', 'supplier_id': supplier_id}, {'$set': {'account': account}})
        suppliers_collection = get_supplier_collection(db)
      else:
        message = 'Error: invalid characters in account'
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
      account = request.form['account']
      website = request.form['website']
      phone = request.form['phone']
      address = request.form['address']
      contact_name = request.form['contact_name']
      email = request.form['email']
      if len(supplier_id) < 2:
        message = 'Error: Supplier name must be 2 or more characters'
      elif is_valid_string(supplier_id) == False:
        message = 'Error: invalid character in supplier name'
      elif is_valid_string(account) == False:
        message = 'Error: invalid character in account'
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
          db.inventory_management.insert_one({'type': 'supplier', 'supplier_id': supplier_id, 'account': account, 'website': website, 'phone': phone, 'address': address, 'contact_name': contact_name, 'email': email})
        except:
          message = 'Error inserting document into collection'
        else:
          suppliers_collection = get_supplier_collection(db)
  return render_template('supplier_management.html', instance_name=config['instance_name'], assets_url=assets_url, username=username, session_key=session_key, permissions=permissions, suppliers_collection=suppliers_collection, message=message)



@app.route('/department_list/', methods=['POST', 'GET'])
def department_list():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/department_list/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'suppliers_departments_brands' not in permissions:
    return redirect('/')
  department_list = get_department_list(db)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'go_to_department':
      return redirect('/department_management/' + request.form['department_id'] + '/')
    elif request.form['function'] == 'create_department':
      if is_valid_string(request.form['department_id']) == False:
        message = "Invalid name"
      elif len(request.form['department_id']) < 3:
        message = "Department name must be longer than 3 characters"
      elif request.form['department_id'] in department_list:
        message = "Department already exists"
      else:
        db.inventory_management.insert_one({'type': 'department', 'department_id': request.form['department_id'], 'categories': [], 'default_margin': 0.3, 'default_food_item': True, 'default_ebt_eligible': True, 'default_taxes': config['default_taxes'], 'default_employee_discount': config['employee_discount']})
        department_list = get_department_list(db)
  return render_template('department_list.html', instance_name=config['instance_name'], assets_url=assets_url, username=username, session_key=session_key, permissions=permissions, message=message, department_list=department_list)


@app.route('/department_management/<department_id>/', methods=['POST', 'GET'])
def department_management(department_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/department_management/'+ department_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'suppliers_departments_brands' not in permissions:
    return redirect('/')
  
  selected_category = ''
  selected_subcategory = ''
  categories_list = []
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'department_list':
      return redirect('/department_list/')
    elif request.form['function'] == 'go_to_category':
      return redirect('/category_management/' + department_id + '/' + request.form['category_id'] + '/')
    elif request.form['function'] == 'set_default_employee_discount':
      if is_valid_percent(request.form['default_employee_discount']) == False:
        message = 'invalid percentage'
      else:
        new_default_employee_discount = percent_to_float(request.form['default_employee_discount'])
        if new_default_employee_discount < 0:
          message = 'percentage must be positive'
        else:
          db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_employee_discount': new_default_employee_discount}})
    elif request.form['function'] == 'set_default_margin':
      if is_valid_percent(request.form['default_margin']) == False:
        message = 'invalid percentage'
      else:
        new_default_margin = percent_to_float(request.form['default_margin'])
        db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_margin': new_default_margin}})
    elif request.form['function'] == 'set_default_food_item':
      if request.form['default_food_item'] == "True":
        db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_food_item': True}})
      else:
        db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_food_item': False}})
    elif request.form['function'] == 'set_default_ebt_eligible':
      if request.form['default_ebt_eligible'] == "True":
        db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_ebt_eligible': True}})
      else:
        db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_ebt_eligible': False}})
    elif request.form['function'] == 'remove_tax':
      department_document = db.inventory_management.find_one({'type': 'department', 'department_id': request.form['department_id']})
      department_document['default_taxes'].remove(request.form['tax_id'])
      db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_taxes': department_document['default_taxes']}})
    elif request.form['function'] == 'add_tax':
      department_document = db.inventory_management.find_one({'type': 'department', 'department_id': request.form['department_id']})
      if request.form['tax_id'] == 'exempt':
        department_document['default_taxes'] = ['exempt']
      else:
        if department_document['default_taxes'] == ['exempt']:
          department_document['default_taxes'] = []
        department_document['default_taxes'].append(request.form['tax_id'])
      db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$set': {'default_taxes': department_document['default_taxes']}})
    elif request.form['function'] == 'add_category':
      department_document = db.inventory_management.find_one({'type': 'department', 'department_id': department_id})
      categories_list = department_document['categories']
      category_id_list = []
      for category in categories_list:
        category_id_list.append(category['category_id'])
      if is_valid_string(request.form['category_id']) == False:
        message = 'Invalid category name'
      elif request.form['category_id'] in category_id_list:
        message = 'category already exists'
      else:
        db.inventory_management.update_one({'type': 'department', 'department_id': request.form['department_id']}, {'$push': {'categories': {'category_id': request.form['category_id'], 'subcategories': []}}})



  department_document = db.inventory_management.find_one({'type': 'department', 'department_id': department_id})
  





  return render_template('department_management.html', department_document=department_document, selected_category=selected_category, selected_subcategory=selected_subcategory, categories_list=department_document['categories'], instance_name=instance_name, assets_url=assets_url, username=username, session_key=session_key, permissions=permissions, message=message, taxes=config['taxes'])



@app.route('/category_management/<department_id>/<category_id>/', methods=['POST', 'GET'])
def category_management(department_id, category_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/category_management/'+ department_id + '/' + category_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'suppliers_departments_brands' not in permissions:
    return redirect('/')
  subcategories = []
  department_document = db.inventory_management.find_one({'type': 'department', 'department_id': department_id})
  categories = department_document['categories']
  for category in categories:
    if category['category_id'] == category_id:
      subcategories = category['subcategories']
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'department_list':
      return redirect('/department_list/')
    elif request.form['function'] == 'go_to_department':
      return redirect('/department_management/' + department_id + '/')
    elif request.form['function'] == 'add_subcategory':
      if is_valid_string(request.form['subcategory_id']) == False:
        message = "Invalid name"
      elif len(request.form['subcategory_id']) < 3:
        message = "Subcategory name must be 3 or more characters"
      elif request.form['subcategory_id'] in subcategories:
        message = "Subcategory already exists"
      else:
        subcategories.append(request.form['subcategory_id'])
        new_categories = []
        for category in categories:
          if category['category_id'] == category_id:
            category['subcategories'] = subcategories
          new_categories.append(category)
        db.inventory_management.update_one({'type': 'department', 'department_id': department_id}, {'$set': {'categories': new_categories}})
  return render_template('category_management.html', instance_name=instance_name, assets_url=assets_url, username=username, permissions=permissions, message=message, category_id=category_id, department_id=department_id, subcategories=subcategories)

@app.route('/brand_management/', methods=['POST', 'GET'])
def brand_management():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/brand_management/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'suppliers_departments_brands' not in permissions:
    return redirect('/')
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'inventory_management':
      return redirect('/inventory_management/')
    elif request.form['function'] == 'create_brand':
      if request.form['local'] == True:
        local_bool = True
      else:
        local_bool = False
      db.inventory_management.insert_one({'type': 'brand', 'brand_id': request.form['brand_id'], 'website': request.form['website'], 'supplier': request.form['supplier_id'], 'local': local_bool})
    elif request.form['function'] == 'change_website':
      if is_valid_string(request.form['website']) == True:
        db.inventory_management.update_one({'type': 'brand', 'brand_id': request.form['brand_id']}, {'$set': {'website': request.form['website']}})
    elif request.form['function'] == 'change_local':
      if request.form['local'] == True:
        local_bool = True
      else:
        local_bool = False
      db.inventory_management.update_one({'type': 'brand', 'brand_id': request.form['brand_id']}, {'$set': {'local': local_bool}})
    elif request.form['function'] == 'change_supplier':
      db.inventory_management.update_one({'type': 'brand', 'brand_id': request.form['brand_id']}, {'$set': {'supplier': request.form['supplier_id']}})
  return render_template('brand_management.html', instance_name=config['instance_name'], assets_url=assets_url, username=username, supplier_list=get_supplier_list(db), session_key=session_key, permissions=permissions, message=message, brand_collection=get_brand_collection(db))



@app.route('/employee_management/', methods=['POST', 'GET'])
def employee_management():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/employee_management/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'employee_management' not in permissions:
    return redirect('/')
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    
    elif request.form['function'] == 'change_name':
      if is_valid_string(request.form['name']) == False:
        message = 'invalid string'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'name': request.form['name']}})
    elif request.form['function'] == 'change_short_name':
      if is_valid_string(request.form['short_name']) == False:
        message = 'invalid string'
      elif len(request.form['short_name']) > 15:
        message = 'name must not be more than 15 characters'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'short_name': request.form['short_name']}})
    elif request.form['function'] == 'change_title':
      if is_valid_string(request.form['title']) == False:
        message = 'invalid string'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'title': request.form['title']}})
    elif request.form['function'] == 'change_phone':
      if is_valid_string(request.form['phone']) == False:
        message = 'invalid string'
      elif len(request.form['phone']) > 15:
        message = 'phone number must not be more than characters'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'phone': request.form['phone']}})
    elif request.form['function'] == 'change_address':
      if is_valid_string(request.form['address']) == False:
        message = 'invalid string'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'address': request.form['address']}})
    
    elif request.form['function'] == 'change_email':
      if is_valid_string(request.form['email']) == False:
        message = 'invalid string'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'email': request.form['email']}})
    elif request.form['function'] == 'change_date':
      if is_valid_date(request.form['hire_date']) == False:
        message = 'invalid date'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'hire_date': request.form['hire_date']}})
    elif request.form['function'] == 'change_status':
      db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'status': request.form['status']}})
    elif request.form['function'] == 'modify_permissions':
      new_permissions = request.form.getlist('permissions[]')
      if 'superuser' in new_permissions:
        new_permissions = ['superuser']      
      db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'permissions': new_permissions}})
    elif request.form['function'] == 'reset_password':
      if is_valid_password(request.form['password1']) == False:
        message = 'invalid password'
      elif request.form['password1'] != request.form['password2']:
        message = 'passwords do not match'
      else:
        bytes = request.form['password1'].encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'password': hash}})
    elif request.form['function'] == 'change_login_message':
      if is_valid_string(request.form['login_message']) == False:
        message = 'invalid login message'
      else:
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'login_message': request.form['login_message']}})
    elif request.form['function'] == 'create_employee':
      if is_valid_string(request.form['username']) == False:
        message = 'invalid username'
      elif len(request.form['username']) > 20:
        message = 'username must not be longer than 20 characters'
      elif is_valid_password(request.form['password1']) == False:
        message = 'invalid password'
      elif request.form['password1'] != request.form['password2']:
        message = 'passwords do not match'
      elif is_valid_string(request.form['name']) == False:
        message = 'invalid full name'
      elif is_valid_string(request.form['short_name']) == False:
        message = 'invalid short name'
      elif len(request.form['short_name']) > 15:
        message = 'short name must be 15 characters or less'
      elif is_valid_string(request.form['title']) == False:
        message = 'invalid title'
      elif is_valid_string(request.form['phone']) == False:
        message = 'invalid phone'
      elif len(request.form['phone']) > 15:
        message = 'phone number must not be longer than 15 characters'
      elif is_valid_string(request.form['address']) == False:
        message = 'invalid address'
      elif is_valid_string(request.form['email']) == False:
        message = 'invalid email'
      elif request.form['hire_date'] != '' and is_valid_date(request.form['hire_date']) == False:
        message = 'invalid hire date'
      elif is_valid_string(request.form['login_message']) == False:
        message = 'invalid login message'
      else:
        new_permissions = request.form.getlist('permissions[]')
        if 'superuser' in new_permissions:
          new_permissions = ['superuser']      
        create_user(db, request.form['username'], request.form['password1'], new_permissions, request.form['address'], request.form['name'], request.form['short_name'], request.form['title'], request.form['phone'], request.form['email'], request.form['hire_date'], request.form['login_message'])

  employee_collection = db.employees.find({'type': 'user'})
  if 'superuser' not in permissions:
    new_employee_collection = []
    for employee in employee_collection:
      if 'superuser' not in employee['permissions']:
        new_employee_collection.append(employee)
  return render_template('employee_management.html', instance_name=config['instance_name'], assets_url=assets_url, username=username, session_key=session_key, permissions=permissions, employee_collection=employee_collection, message=message)


@app.route('/import_data/', methods=['POST', 'GET'])
def import_data():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/admin/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:    
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'inventory_management' not in permissions:
    return redirect('/admin/')
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'import_unfi_allbid':
      return redirect('/import_unfi_allbid/')
  return render_template('import_data.html', instance_name=instance_name, assets_url=assets_url, username=result['username'], session_key=session_key, permissions=permissions)


@app.route('/import_unfi_allbid/', methods=['POST', 'GET'])
def import_unfi_allbid():
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      username = request.form['username']
      password = request.form['password']

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, username, password, source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/admin/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:    
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  config = db.natapos.find_one({'config': 'global'})
  instance_name = config['instance_name']
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  permissions = []
  permissions = employee_info['permissions']
  if 'superuser' not in permissions and 'inventory_management' not in permissions:
    return redirect('/admin/')
  message = ''
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'import_data':
      return redirect('/import_data/')
    elif request.form['function'] == 'upload_allbid':
      if 'file' not in request.files:
        message = 'upload failed'
      else:
        file = request.files['file']
        if file.filename == '':
          message = 'no selected file'
        elif is_allowed_file(file.filename, ['csv', 'CSV']) == False:
          message = 'invalid file type'
        else:
          starting_time = time.time()
          filename = secure_filename(file.filename)
          file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
          file_in = open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
          new_count = 0
          update_count = 0
          delete_count = 0
          reader = csv.reader(file_in, quotechar='\"')
          for row in reader:
            if 'T' in row[20] or 'P' in row[20]:
              APPRV = row[8]
              if APPRV[0:4] == '*DIS':
                db.allbid.delete_one({'item_id': row[15].replace('-', '').replace('00', '', 1)})
                delete_count += 1
              else:
                allbid_item = {}

                allbid_item['item_id'] = row[15].replace('-', '').replace('00', '', 1)
                if is_valid_float(row[4]) == True:
                  allbid_item['case_quantity'] = float(row[4])
                else:
                  allbid_item['case_quantity'] = 1.0
                allbid_item['package_size'] = row[5]
                allbid_item['description'] = row[7]
                if APPRV == '*New':
                  allbid_item['new'] = True
                  new_count += 1
                else:
                  allbid_item['new'] = False
                  update_count += 1
                if APPRV == '*Chg':
                  allbid_item['cost_change'] = True
                else:
                  allbid_item['cost_change'] = False
                if is_valid_float(row[9]) == True:
                  allbid_item['case_cost'] = float(row[9])
                else:
                  allbid_item['case_cost'] = 0.01
                if is_valid_float(row[17]) == True:
                  allbid_item['suggested_retail_price'] = float(row[17])
                else:
                  allbid_item['suggested_retail_price'] = 0.01
                allbid_item['order_code'] = row[2]
                if db.allbid.find_one({'item_id': allbid_item['item_id']}) == None:
                  db.allbid.insert_one({'item_id': allbid_item['item_id'], 'case_quantity': allbid_item['case_quantity'], 'package_size': allbid_item['package_size'], 'description': allbid_item['description'], 'new': allbid_item['new'], 'cost_change': allbid_item['cost_change'], 'case_cost': allbid_item['case_cost'], 'suggested_retail_price': allbid_item['suggested_retail_price'], 'order_code': allbid_item['order_code']})
                else:
                  db.allbid.update_one({'item_id': allbid_item['item_id']}, {'$set': {'case_quantity': allbid_item['case_quantity'], 'package_size': allbid_item['package_size'], 'description': allbid_item['description'], 'new': allbid_item['new'], 'cost_change': allbid_item['cost_change'], 'case_cost': allbid_item['case_cost'], 'suggested_retail_price': allbid_item['suggested_retail_price'], 'order_code': allbid_item['order_code']}})

                if db.inventory.find_one({'item_id': allbid_item['item_id']}) != None:
                  db.inventory.update_one({'item_id': allbid_item['item_id']}, {'$set': {'case_cost': allbid_item['case_cost'], 'suggested_retail_price': allbid_item['suggested_retail_price'], 'order_code': allbid_item['order_code']}})
          file_in.close()
          time_elapsed = time.time() - starting_time
          message = str(new_count) + ' new items<br/>' + str(update_count) + ' updated items<br/>' + str(delete_count) + ' deleted items<br/>loaded successfully in ' + str(round(time_elapsed,2)) + ' seconds<br/>from ' + filename
  return render_template('import_unfi_allbid.html', instance_name=instance_name, assets_url=assets_url, username=result['username'], session_key=session_key, permissions=permissions, message=message)







