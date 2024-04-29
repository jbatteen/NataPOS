# import libraries
from flask import Flask, render_template, request, redirect, jsonify, make_response
import time
import bcrypt
import os
import csv
from werkzeug.utils import secure_filename
from threading import Thread
from datetime import date
from pymongo.mongo_client import MongoClient


# import local files
from config import db_name, mongo_url, assets_url
from authentication_functions import validate_login, validate_session_key, create_user, get_employee_collection
from calculations_and_conversions import calculate_worked_hours, price_to_float, percent_to_float, float_to_price, float_to_percent
from is_valid import is_valid_username, is_valid_password, is_valid_date, is_date_within_range, is_date_in_future, is_valid_string, is_valid_price, is_valid_float, is_valid_int, is_valid_percent, is_allowed_file, is_valid_ip_address
from inventory_functions import get_item_group_list, get_supplier_list, get_supplier_collection, beautify_item, get_department_list, get_brand_collection, get_brand_list
from hardware_functions import get_shelf_tag_printer_collection, get_shelf_tag_printer_list, print_shelf_tag

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
    db.natapos.insert_one({'config': 'global', 'instance_name': 'NataPOS', 'current_pay_period_start': date.today().strftime('%m/%d/%y'), 'timesheets_locked': False, 'employee_discount': 0.2, 'taxes': [{'tax_id': 'exempt', 'rate': 0.0}], 'default_taxes': [], 'phone': '', 'address': ''})
db.inventory_management.update_one({'type':'allbid_upload'}, {'$set': {'complete': True}}, upsert=True)
  
# begin app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/var/www/NataPOS/uploads'

@app.route('/create_first_user', methods=['POST', 'GET'])
def create_first_user():
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'create_first_user': # create first user form submitted
      try: # if employees collection exists
        db.validate_collection("employees")
      except: # if it doesn't which it shouldn't
        if request.form['username'] == '':
          return render_template('create_first_user.html', instance_name=config['instance_name'], assets_url=assets_url, message="Error: blank username")
        if is_valid_username(request.form['username']) == False:
          return render_template('create_first_user.html', instance_name=config['instance_name'], assets_url=assets_url, message="Error: Invalid username. Allowed characters: \"A-Z\", \"a-z\", \"0-9\", \" .,()-+\"")
        if request.form['password'] != request.form['password2']:
          return render_template('create_first_user.html', instance_name=config['instance_name'], assets_url=assets_url, message="Error: passwords didn't match")
        elif request.form['password'] == '':
          return render_template('create_first_user.html', instance_name=config['instance_name'], assets_url=assets_url, message="Error: blank password")

        if len(request.form['instance_name']) < 4:
          return render_template('create_first_user.html', instance_name=request.form['instance_name'], assets_url=assets_url, message='Error: Instance name must be 4 characters or more')
        else:
          if is_valid_string(request.form['instance_name']) == False:
            return render_template('create_first_user.html', instance_name=request.form['instance_name'], assets_url=assets_url, message='Error: invalid name.  Allowed characters: \"A-Z\", \"a-z\", \"0-9\", \" .,()-+\"')
       
        db.natapos.update_one({'config': 'global'}, {'$set': {'instance_name': request.form['instance_name']}})
        creation_check = {}
        creation_check = create_user(db, request.form['username'], request.form['password'], ['superuser'], '', '', '', '', '', '', '')
        if creation_check['success'] == True:
          result = {}


          if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            source_ip = request.environ['REMOTE_ADDR']
          else:
            source_ip = request.environ['HTTP_X_FORWARDED_FOR']
          result = validate_login(db, username=request.form['username'], password=request.form['password'], source_ip=source_ip)
          if result['success'] == True:
            response = redirect('/global_config/')
            response.set_cookie('natapos_session_key', result['session_key'])
            return response
          else:
            return render_template('create_first_user.html', instance_name=request.form['instance_name'], assets_url=assets_url, message='validation error')
        else:
          return render_template('create_first_user.html', instance_name=request.form['instance_name'], assets_url=assets_url, message=creation_check['error'])
      else: # if it does exist and someone called this page anyway
        return('nice try') # someone spoofed
  else:
    return render_template('create_first_user.html', instance_name=config['instance_name'], assets_url=assets_url)

@app.route('/global_config/', methods=['POST', 'GET'])
def global_config():
  message = None
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/global_config/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions']:
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
  return render_template('global_config.html', instance_name=config['instance_name'], assets_url=assets_url, current_pay_period_start=config['current_pay_period_start'], employee_discount=employee_discount, message=message, taxes=config['taxes'], default_taxes=config['default_taxes'], phone=config['phone'], address=config['address'])
    

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
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False: # invalid combo, send back to main page
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  
  if request.method == 'POST':
    if request.form['function'] == 'clock_in':
      while config['timesheets_locked'] == True:
        time.sleep(1)
        config = db.natapos.find_one({'config': 'global'})

      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': result['username'], 'pay_period': 'current'})
      if timesheet is not None:
        db.timesheets.update_one({'username': result['username'], 'pay_period': 'current'}, {'$set': {str(current_time): 'in'}})
      else:
        db.timesheets.insert_one({'username': result['username'], 'pay_period': 'current', str(current_time): 'in'})
    if request.form['function'] == 'clock_out':
      while config['timesheets_locked'] == True:
        time.sleep(1)
        config = db.natapos.find_one({'config': 'global'})
      current_time = int(round(time.time()))
      timesheet = db.timesheets.find_one({'username': result['username'], 'pay_period': 'current'})
      if timesheet is not None:
        db.timesheets.update_one({'username': result['username'], 'pay_period': 'current'}, {'$set': {str(current_time): 'out'}})
      else:
        db.timesheets.insert_one({'username': result['username'], 'pay_period': 'current', str(current_time): 'out'})
    if request.form['function'] == 'open_register':
      return 'open register'
    if request.form['function'] == 'admin':
      return redirect('/admin/')
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
  employee_document = db.employees.find_one({'type': 'user', 'username': result['username']})
  message = employee_document['login_message']
  timesheet = db.timesheets.find_one({'username': result['username'], 'pay_period': 'current'})
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
  

  return render_template('landing.html', instance_name=config['instance_name'], assets_url=assets_url, username=result['username'], message=message)

@app.route('/admin/', methods=['POST', 'GET'])
def admin():
  session_key = request.cookies.get('natapos_session_key')
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/admin/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'change_password':
      return redirect('/change_password/')
    elif request.form['function'] == 'edit_item':
      return redirect('/edit_item/')
    elif request.form['function'] == 'employee_management':
      return redirect('/employee_management/')
    elif request.form['function'] == 'hardware':
      return redirect('/hardware/')
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
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  return render_template('admin.html', assets_url=assets_url, permissions=employee_info['permissions'])  


@app.route('/edit_item/', methods=['POST', 'GET'])
def edit_item_scan_search():
  session_key = request.cookies.get('natapos_session_key')
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/edit_item/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  message = None
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url,)
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
  return render_template('scan_item.html', assets_url=assets_url, message=message)

@app.route('/edit_item/<item_id>/', methods=['POST', 'GET'])
def edit_item(item_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/edit_item/' + item_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'inventory_management' not in employee_info['permissions'] and 'superuser' not in employee_info['permissions']:
    return redirect('/')
  message = ''
  scanned_item = db.inventory.find_one({'item_id' : item_id})
  if scanned_item is None:
    return redirect('/create_item/' + item_id + '/')
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
      return redirect('/edit_item/')
    elif request.form['function'] == 'remove_tax':
      scanned_item['taxes'].remove(request.form['tax_id'])
      db.inventory.update_one({'item_id': item_id}, {'$set': {'taxes': scanned_item['taxes']}})
      return render_template('item_tax_div.html', available_taxes=config['taxes'], scanned_item=scanned_item)
    elif request.form['function'] == 'print_shelf_tag':
      db.session_keys.update_one({'session_key': session_key}, {'$set': {'last_shelf_tag_printer': request.form['hardware_id']}})
      return make_response(jsonify(print_shelf_tag(db, item_id, request.form['hardware_id'])))
    elif request.form['function'] == 'add_tax':
      if request.form['tax_id'] == 'exempt':
        scanned_item['taxes'] = ['exempt']
      else:
        if scanned_item['taxes'] == ['exempt']:
          scanned_item['taxes'] = []
        scanned_item['taxes'].append(request.form['tax_id'])
      db.inventory.update_one({'item_id': item_id}, {'$set': {'taxes': scanned_item['taxes']}})
      return render_template('item_tax_div.html', available_taxes=config['taxes'], scanned_item=scanned_item)
    elif request.form['function'] == 'create_item_group':
      item_group_list = get_item_group_list(db)
      if is_valid_string(request.form['item_group_id']) == False:
        message = 'invalid group name'
      elif request.form['item_group_id'] in item_group_list:
        message = 'group already exists'
      else:
        itemlist = []
        itemlist.append(item_id)
        for group in scanned_item['item_groups']:
          item_group_list.remove(group)
        db.inventory_management.insert_one({'type': 'item_group', 'item_group_id': request.form['item_group_id'], 'items': itemlist})
        scanned_item['item_groups'].append(request.form['item_group_id'])
        db.inventory.update_one({'item_id': item_id}, {'$set': {'item_groups': scanned_item['item_groups']}})
        return render_template('item_group_div.html', item_group_list=item_group_list, scanned_item=scanned_item)
    elif request.form['function'] == 'remove_item_from_group':
      scanned_item['item_groups'].remove(request.form['item_group_id'])
      db.inventory.update_one({'item_id': item_id}, {'$set': {'item_groups': scanned_item['item_groups']}})
      document = db.inventory_management.find_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']})
      document['items'].remove(item_id)
      db.inventory_management.update_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']}, {'$set': {'items': document['items']}})
      item_group_list = get_item_group_list(db)
      for group in scanned_item['item_groups']:
        item_group_list.remove(group)
      return render_template('item_group_div.html', item_group_list=item_group_list, scanned_item=scanned_item)
    elif request.form['function'] == 'add_item_to_group':
      scanned_item['item_groups'].append(request.form['item_group_id'])
      db.inventory.update_one({'item_id': item_id}, {'$set': {'item_groups': scanned_item['item_groups']}})
      document = db.inventory_management.find_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']})
      document['items'].append(item_id)
      db.inventory_management.update_one({'type': 'item_group', 'item_group_id': request.form['item_group_id']}, {'$set': {'items': document['items']}})
      item_group_list = get_item_group_list(db)
      for group in scanned_item['item_groups']:
        item_group_list.remove(group)
      return render_template('item_group_div.html', item_group_list=item_group_list, scanned_item=scanned_item)
    elif request.form['function'] == 'get_info':
      if request.form['property'] == 'cost_per':
        cost_per = round((scanned_item['case_cost'] / scanned_item['case_quantity']), 2)
        if cost_per == 0.0:
          cost_per = 0.01
        return float_to_price(cost_per)
      elif request.form['property'] == 'suggested_margin':
        cost_per = round((scanned_item['case_cost'] / scanned_item['case_quantity']), 2)
        if cost_per == 0.0:
          cost_per = 0.01
        return float_to_percent((scanned_item['suggested_retail_price'] / cost_per) - 1)
      elif request.form['property'] == 'margin':
        cost_per = round((scanned_item['case_cost'] / scanned_item['case_quantity']), 2)
        if cost_per == 0.0:
          cost_per = 0.01
        return float_to_percent((scanned_item['regular_price'] / cost_per) - 1)
      elif request.form['property'] == 'subcategories':
        if scanned_item['department'] == '':
          return render_template('item_subcategory_div.html', subcategories=[])
        else:
          if scanned_item['category'] == '':
            return render_template('item_subcategory_div.html', subcategories=[])
          else:
            department_collection = db.inventory_management.find_one({'type': 'department', 'department_id': scanned_item['department']})
            for category in department_collection['categories']:
              if scanned_item['category'] == category['category_id']:
                return render_template('item_subcategory_div.html', subcategories=category['subcategories'])
      elif request.form['property'] == 'categories':
        if scanned_item['department'] == '':
          return render_template('item_category_div.html', categories=[])
        else:
          department_collection = db.inventory_management.find_one({'type': 'department', 'department_id': scanned_item['department']})
          categories = []
          for category in department_collection['categories']:
            categories.append(category['category_id'])
          return render_template('item_category_div.html', categories=categories)

    elif request.form['function'] == 'update':
      success = False
      beautified = ''
      if request.form['property'] == 'name':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid name'
        elif len(request.form['new_data']) < 6:
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
      elif request.form['property'] == 'employee_discount':
        if is_valid_percent(request.form['new_data']) == False:
          message = 'Invalid percentage'
        else:
          percent_float = percent_to_float(request.form['new_data'])
          success = True
          beautified = float_to_percent(percent_float)
          db.inventory.update_one({'item_id': item_id}, {'$set': {'employee_discount': percent_float}})
      elif request.form['property'] == 'suggested_retail_price':
        if is_valid_price(request.form['new_data']) == False:
          message = 'invalid price'
        else:
          price_float = price_to_float(request.form['new_data'])
          db.inventory.update_one({'item_id': item_id}, {'$set': {'suggested_retail_price': price_float}})
          success = True
          beautified = float_to_price(price_float)
      elif request.form['property'] == 'regular_price':
        if is_valid_price(request.form['new_data']) == False:
          message = 'invalid price'
        else:
          price_float = price_to_float(request.form['new_data'])
          db.inventory.update_one({'item_id': item_id}, {'$set': {'regular_price': price_float}})
          success = True
          beautified = float_to_price(price_float)
      elif request.form['property'] == 'price_by_margin':
        if is_valid_percent(request.form['new_data']) == False:
          message = 'invalid percentage'
        else:
          percent_float = percent_to_float(request.form['new_data'])
          if percent_float < 0:
            message = 'margin must be greater than zero'
          else:
            cost_per = round((scanned_item['case_cost'] / scanned_item['case_quantity']), 2)
            if cost_per == 0.0:
              price_float = 0.0
            else:
              price_float = round((cost_per + (percent_float * cost_per)), 2)
            db.inventory.update_one({'item_id': item_id}, {'$set': {'regular_price': price_float}})  
            return make_response(jsonify({'success': True, 'regular_price': float_to_price(price_float), 'margin': float_to_percent(percent_float)}))
      elif request.form['property'] == 'quantity_on_hand':
        if scanned_item['unit'] == 'each':
          if is_valid_int(request.form['new_data']) == False:
            message = 'Invalid quantity, must be whole number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'quantity_on_hand': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True
        else:
          if is_valid_float(request.form['new_data']) == False:
            message = 'Invalid quantity, must be a valid number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'quantity_on_hand': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True
      elif request.form['property'] == 'most_recent_delivery':
        if is_valid_date(request.form['new_data']) == False:
          message = 'invalid date'
        else:
          success = True
          beautified = request.form['new_data']
          db.inventory.update_one({'item_id': item_id}, {'$set': {'most_recent_delivery': request.form['new_data']}})
      elif request.form['property'] == 'quantity_low':
        if scanned_item['unit'] == 'each':
          if is_valid_int(request.form['new_data']) == False:
            message = 'Invalid quantity, must be whole number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'quantity_low': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True
        else:
          if is_valid_float(request.form['new_data']) == False:
            message = 'Invalid quantity, must be a valid number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'quantity_low': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True
      elif request.form['property'] == 'quantity_high':
        if scanned_item['unit'] == 'each':
          if is_valid_int(request.form['new_data']) == False:
            message = 'Invalid quantity, must be whole number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'quantity_high': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True
        else:
          if is_valid_float(request.form['new_data']) == False:
            message = 'Invalid quantity, must be a valid number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'quantity_high': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True
      elif request.form['property'] == 'item_location':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid memo'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'item_location': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'backstock_location':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid memo'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'backstock_location': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'active':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'active': True}})
          beautified = 'True'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'active': False}})
          beautified = 'False'
        success = True
      elif request.form['property'] == 'unit':
        db.inventory.update_one({'item_id': item_id}, {'$set': {'unit': request.form['new_data']}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'package_size':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid package size'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'package_size': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'break_pack_quantity':
        if scanned_item['unit'] == 'each':
          if is_valid_string(request.form['new_data']) == False:
            message = 'Invalid quantity, must be whole number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'break_pack_quantity': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True
        else:
          if is_valid_float(request.form['new_data']) == False:
            message = 'Invalid quantity, must be a valid number'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'break_pack_quantity': float(request.form['new_data'])}})
            beautified = request.form['new_data']
            success = True  
      elif request.form['property'] == 'break_pack_item_id':
        if request.form['new_data'] == '':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'break_pack_item_id': ''}})
          success = True
        else:
          break_pack_item = db.inventory.find_one({'item_id': request.form['new_data']})
          if break_pack_item == None:
            message = 'Item not in system'
          else:
            db.inventory.update_one({'item_id': item_id}, {'$set': {'break_pack_item_id': request.form['new_data']}})
            beautified = request.form['new_data']
            success = True
      elif request.form['property'] == 'supplier':
        db.inventory.update_one({'item_id': item_id}, {'$set': {'supplier': request.form['new_data']}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'order_code':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid order code'
        else:
          success = True
          db.inventory.update_one({'item_id': item_id}, {'$set': {'order_code': request.form['new_data']}})
          beautified = request.form['new_data']

      elif request.form['property'] == 'department':
        success = True
        beautified = request.form['new_data']
        db.inventory.update_one({'item_id': item_id}, {'$set': {'subcategory': ''}})
        db.inventory.update_one({'item_id': item_id}, {'$set': {'category': ''}})
        db.inventory.update_one({'item_id': item_id}, {'$set': {'department': request.form['new_data']}})
      elif request.form['property'] == 'category':
        success = True
        beautified = request.form['new_data']
        db.inventory.update_one({'item_id': item_id}, {'$set': {'subcategory': ''}})
        db.inventory.update_one({'item_id': item_id}, {'$set': {'category': request.form['new_data']}})
      elif request.form['property'] == 'subcategory':
        success = True
        beautified = request.form['new_data']
        db.inventory.update_one({'item_id': item_id}, {'$set': {'subcategory': request.form['new_data']}})
      elif request.form['property'] == 'brand':
        success = True
        beautified = request.form['new_data']
        db.inventory.update_one({'item_id': item_id}, {'$set': {'brand': request.form['new_data']}})
      elif request.form['property'] == 'local':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'local': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'local': False}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'organic':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'organic': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'organic': False}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'consignment':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'consignment': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'consignment': False}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'food_item':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'food_item': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'food_item': False}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'random_weight_per':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'random_weight_per': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'random_weight_per': False}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'discontinued':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'discontinued': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'discontinued': False}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'ebt_eligible':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'ebt_eligible': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'ebt_eligible': False}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'wic_eligible':
        if request.form['new_data'] == 'True':
          db.inventory.update_one({'item_id': item_id}, {'$set': {'wic_eligible': True}})
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'wic_eligible': False}})
        success = True
        beautified = request.form['new_data']

      elif request.form['property'] == 'age_restricted':
        if is_valid_int(request.form['new_data']) == False:
          message = 'invalid integer'
        else:
          age = int(request.form['new_data'])
          if age < 0:
            message = 'age must be positive'
          else:
            success = True
            beautified = request.form['new_data']
            db.inventory.update_one({'item_id': item_id}, {'$set': {'age_restricted': int(request.form['new_data'])}})          
      elif request.form['property'] == 'description':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid description'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'description': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'receipt_alias':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid receipt alias'
        else:
          db.inventory.update_one({'item_id': item_id}, {'$set': {'receipt_alias': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      if success == True:
        return make_response(jsonify({'success': success, 'beautified': beautified}))
      else:
        return make_response(jsonify({'success': success, 'message': message}))
  item_group_list = get_item_group_list(db)
  for group in scanned_item['item_groups']:
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
  shelf_tag_printer_list = get_shelf_tag_printer_list(db)
  if result['last_shelf_tag_printer'] != '' and result['last_shelf_tag_printer'] in shelf_tag_printer_list:
    new_shelf_tag_printer_list = []
    new_shelf_tag_printer_list.append(result['last_shelf_tag_printer'])
    for printer in shelf_tag_printer_list:
      if printer != result['last_shelf_tag_printer']:
        new_shelf_tag_printer_list.append(printer)
    shelf_tag_printer_list = new_shelf_tag_printer_list
  return render_template('edit_item.html',  departments=get_department_list(db), categories=categories, subcategories=subcategories, assets_url=assets_url, scanned_item=scanned_item, supplier_list=get_supplier_list(db), item_group_list=item_group_list, permissions=employee_info['permissions'], message=message, brands=get_brand_list(db), available_taxes=config['taxes'], item_id=item_id, shelf_tag_printers=shelf_tag_printer_list)

@app.route('/create_item/<item_id>/', methods=['POST', 'GET'])
def create_item(item_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/create_item/' + item_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'inventory_management' not in employee_info['permissions'] and 'superuser' not in employee_info['permissions']:
    return redirect('/')
  scanned_item = db.inventory.find_one({'item_id' : item_id})
  if scanned_item is not None:
    return redirect('/edit_item/' + item_id + '/')
  
  if request.method == 'POST':
    if request.form['function'] == 'edit_item':
      return redirect('/edit_item/')
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
  return render_template('create_new_item.html', assets_url=assets_url, scan=item_id, supplier_list=get_supplier_list(db), department_list=get_department_list(db), in_allbid=in_allbid)   

@app.route('/supplier_management/', methods=['POST', 'GET'])
def supplier_management():
  session_key = request.cookies.get('natapos_session_key')
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/supplier_management/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions'] and 'suppliers_departments_brands' not in employee_info['permissions']:
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
    elif request.form['function'] == 'delete_supplier':
      db.inventory_management.delete_one({'type': 'supplier', 'supplier_id': request.form['supplier_id']})
    elif request.form['function'] == 'create_supplier':
      if len(request.form['supplier_id']) < 2:
        message = 'Error: Supplier name must be 2 or more characters'
      elif is_valid_string(request.form['supplier_id']) == False:
        message = 'Error: invalid character in supplier name'
      elif is_valid_string(request.form['account']) == False:
        message = 'Error: invalid character in account'
      elif is_valid_string(request.form['website']) == False:
        message = 'Error: invalid character in website'
      elif is_valid_string(request.form['phone']) == False:
        message = 'Error: invalid character in phone'
      elif is_valid_string(request.form['address']) == False:
        message = 'Error: invalid character in address'
      elif is_valid_string(request.form['contact_name']) == False:
        message = 'Error: invalid character in contact name'
      elif is_valid_string(request.form['email']) == False:
        message = 'Error: invalid character in email'
      else:
        try:
          db.inventory_management.insert_one({'type': 'supplier', 'supplier_id': request.form['supplier_id'], 'account': request.form['account'], 'website': request.form['website'], 'phone': request.form['phone'], 'address': request.form['address'], 'contact_name': request.form['contact_name'], 'email': request.form['email']})
        except:
          message = 'Error inserting document into collection'
    elif request.form['function'] == 'update':
      success = False
      beautified = ''
      if request.form['property'] == 'account':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid account'
        elif len(request.form['new_data']) < 2:
          message = 'account too short'
        else:
          db.inventory_management.update_one({'type': 'supplier', 'supplier_id': request.form['supplier_id']}, {'$set': {'account': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      if request.form['property'] == 'website':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid website'
        elif len(request.form['new_data']) < 5:
          message = 'website too short, must be 5 or more characters'
        else:
          db.inventory_management.update_one({'type': 'supplier', 'supplier_id': request.form['supplier_id']}, {'$set': {'website': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      if request.form['property'] == 'phone':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid phone'
        elif len(request.form['new_data']) < 7:
          message = 'phone number too short'
        else:
          db.inventory_management.update_one({'type': 'supplier', 'supplier_id': request.form['supplier_id']}, {'$set': {'phone': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      if request.form['property'] == 'address':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid address'
        elif len(request.form['new_data']) < 7:
          message = 'address too short'
        else:
          db.inventory_management.update_one({'type': 'supplier', 'supplier_id': request.form['supplier_id']}, {'$set': {'address': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      if request.form['property'] == 'contact_name':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid contact name'
        elif len(request.form['new_data']) < 2:
          message = 'contact name too short'
        else:
          db.inventory_management.update_one({'type': 'supplier', 'supplier_id': request.form['supplier_id']}, {'$set': {'contact_name': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      if request.form['property'] == 'email':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid email'
        elif len(request.form['new_data']) < 2:
          message = 'email too short'
        else:
          db.inventory_management.update_one({'type': 'supplier', 'supplier_id': request.form['supplier_id']}, {'$set': {'email': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      if success == True:
        return make_response(jsonify({'success': success, 'beautified': beautified}))
      else:
        return make_response(jsonify({'success': success, 'message': message}))
  return render_template('supplier_management.html',  assets_url=assets_url, permissions=employee_info['permissions'], suppliers_collection=get_supplier_collection(db), message=message)



@app.route('/department_list/', methods=['POST', 'GET'])
def department_list():
  session_key = request.cookies.get('natapos_session_key')
  
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/department_list/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions'] and 'suppliers_departments_brands' not in employee_info['permissions']:
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
        config = db.natapos.find_one({'config': 'global'})
        db.inventory_management.insert_one({'type': 'department', 'department_id': request.form['department_id'], 'categories': [], 'default_margin': 0.3, 'default_food_item': True, 'default_ebt_eligible': True, 'default_taxes': config['default_taxes'], 'default_employee_discount': config['employee_discount']})

  return render_template('department_list.html', assets_url=assets_url, message=message, department_list=get_department_list(db))


@app.route('/department_management/<department_id>/', methods=['POST', 'GET'])
def department_management(department_id):
  session_key = request.cookies.get('natapos_session_key')
  config = db.natapos.find_one({'config': 'global'})
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
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
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions'] and 'suppliers_departments_brands' not in employee_info['permissions']:
    return redirect('/')
  
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

  

  return render_template('department_management.html', department_document=db.inventory_management.find_one({'type': 'department', 'department_id': department_id}), assets_url=assets_url, message=message, taxes=config['taxes'])



@app.route('/category_management/<department_id>/<category_id>/', methods=['POST', 'GET'])
def category_management(department_id, category_id):
  session_key = request.cookies.get('natapos_session_key')
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/category_management/'+ department_id + '/' + category_id + '/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions'] and 'suppliers_departments_brands' not in employee_info['permissions']:
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
  return render_template('category_management.html', assets_url=assets_url, message=message, category_id=category_id, department_id=department_id, subcategories=subcategories)

@app.route('/brand_management/', methods=['POST', 'GET'])
def brand_management():
  session_key = request.cookies.get('natapos_session_key')
  if request.method == 'POST':
    if request.form['function'] == 'login':

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/brand_management/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions'] and 'suppliers_departments_brands' not in employee_info['permissions']:
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
      if is_valid_string(request.form['brand_id']) == False:
        message = 'invalid brand name'
      else:
        if request.form['brand_id'] in get_brand_list(db):
          message = 'brand already exists'
        else:
          db.inventory_management.insert_one({'type': 'brand', 'brand_id': request.form['brand_id'], 'website': request.form['website'], 'supplier': request.form['supplier_id'], 'local': local_bool})
    elif request.form['function'] == 'update':
      success = False
      beautified = ''
      if request.form['property'] == 'website':
        if is_valid_string(request.form['new_data']) == False:
          message = 'Invalid website'
        elif len(request.form['new_data']) < 5:
          message = 'website too short, must be 5 or more characters'
        else:
          db.inventory_management.update_one({'type': 'brand', 'brand_id': request.form['brand_id']}, {'$set': {'website': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'local':
        beautified = request.form['new_data']
        success = True
        if request.form['new_data'] == 'True':
          db.inventory_management.update_one({'type': 'brand', 'brand_id': request.form['brand_id']}, {'$set': {'local': True}})
        else:
          db.inventory_management.update_one({'type': 'brand', 'brand_id': request.form['brand_id']}, {'$set': {'local': False}})
      elif request.form['property'] == 'supplier':
        beautified = request.form['new_data']
        success = True
        db.inventory_management.update_one({'type': 'brand', 'brand_id': request.form['brand_id']}, {'$set': {'supplier': request.form['new_data']}})
      if success == True:
        return make_response(jsonify({'success': success, 'beautified': beautified}))
      else:
        return make_response(jsonify({'success': success, 'message': message}))
  return render_template('brand_management.html', assets_url=assets_url, supplier_list=get_supplier_list(db), message=message, brand_collection=get_brand_collection(db))



@app.route('/employee_management/', methods=['POST', 'GET'])
def employee_management():
  session_key = request.cookies.get('natapos_session_key')
  
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/employee_management/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  message = None
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions'] and 'employee_management' not in employee_info['permissions']:
    return redirect('/')
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')

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

    elif request.form['function'] == 'update':
      success = False
      beautified = ''
      if request.form['property'] == 'name':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid characters in name'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'name': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'short_name':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid characters in short name'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'short_name': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'title':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid characters in title'
        elif len(request.form['new_data']) < 2 and request.form['new_data'] != '':
          message = 'title too short'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'title': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'phone':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid characters in phone'
        elif len(request.form['new_data']) < 7 and request.form['new_data'] != '':
          message = 'phone too short'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'phone': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'address':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid characters in address'
        elif len(request.form['new_data']) < 5 and request.form['new_data'] != '':
          message = 'address too short'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'address': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'email':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid characters in email'
        elif len(request.form['new_data']) < 7 and request.form['new_data'] != '':
          message = 'email too short'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'email': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'hire_date':
        if is_valid_date(request.form['new_data']) == False and request.form['new_data'] != '':
          message = 'invalid date'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'hire_date': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'status':
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'status': request.form['new_data']}})
        success = True
        beautified = request.form['new_data']
      elif request.form['property'] == 'login_message':
        if is_valid_string(request.form['new_data']) == False:
          message = 'invalid characters in login message'
        else:
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'login_message': request.form['new_data']}})
          success = True
          beautified = request.form['new_data']
      elif request.form['property'] == 'password':
        print('function')
        if is_valid_password(request.form['password1']) == False:
          message = 'invalid password'
        elif request.form['password1'] != request.form['password2']:
          message = 'passwords do not match'
        else:
          bytes = request.form['password1'].encode('utf-8')
          salt = bcrypt.gensalt()
          hash = bcrypt.hashpw(bytes, salt)
          db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'password': hash}})
          return make_response(jsonify({'success': True}))
      elif request.form['property'] == 'permissions':
        if 'superuser' in employee_info['permissions'] and request.form['superuser'] == 'true':
          new_permissions = ['superuser']      
        else:
          new_permissions = []
          if request.form['inventory_management'] == 'true':
            new_permissions.append('inventory_management')
          if request.form['suppliers_departments_brands'] == 'true':
            new_permissions.append('suppliers_departments_brands')
          if request.form['employee_management'] == 'true':
            new_permissions.append('employee_management')
          if request.form['shrink'] == 'true':
            new_permissions.append('shrink')
        db.employees.update_one({'type': 'user', 'username': request.form['username']}, {'$set': {'permissions': new_permissions}})
        return render_template('employee_permissions_div.html',permissions=employee_info['permissions'], new_permissions=new_permissions, username=request.form['username'])
      if success == True:
        return make_response(jsonify({'success': True, 'beautified': beautified}))
      else:
        return make_response(jsonify({'success': False, 'message': message}))
  employee_collection = get_employee_collection(db)
  if 'superuser' not in employee_info['permissions']:
    new_employee_collection = []
    for employee in employee_collection:
      if 'superuser' not in employee['permissions']:
        new_employee_collection.append(employee)
    employee_collection = new_employee_collection
  return render_template('employee_management.html', assets_url=assets_url, permissions=employee_info['permissions'], employee_collection=employee_collection, message=message)


@app.route('/import_data/', methods=['POST', 'GET'])
def import_data():
  session_key = request.cookies.get('natapos_session_key')
  if request.method == 'POST':
    if request.form['function'] == 'login':

      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
  
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/import_data/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'superuser' not in employee_info['permissions'] and 'inventory_management' not in employee_info['permissions']:
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
  return render_template('import_data.html', assets_url=assets_url)


@app.route('/import_unfi_allbid/', methods=['POST', 'GET'])
def import_unfi_allbid():
  session_key = request.cookies.get('natapos_session_key')
  
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
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response = redirect('/import_unfi_allbid/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response

  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url) 
  username = result['username']
  employee_info = db.employees.find_one({'type': 'user', 'username': username})
  if 'superuser' not in employee_info['permissions'] and 'inventory_management' not in employee_info['permissions']:
    return redirect('/admin/')
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
    elif request.form['function'] == 'processing_status':
      upload_document = db.inventory_management.find_one({'type': 'allbid_upload'})
      if upload_document['complete'] == True:
        return make_response(jsonify({'completed': True, 'html': render_template('import_unfi_allbid_complete.html', upload_document=upload_document)}))
      else:
        return make_response(jsonify({'completed': False, 'html': render_template('import_unfi_allbid_progress.html', upload_document=upload_document)}))
    elif request.form['function'] == 'upload_allbid':
      if 'file' not in request.files:
        return make_response(jsonify({'success': False, 'message': 'upload failed'}))
      else:
        file = request.files['file']
        if file.filename == '':
          return make_response(jsonify({'success': False, 'message': 'no selected file'}))
        elif is_allowed_file(file.filename, ['csv', 'CSV']) == False:
          return make_response(jsonify({'success': False, 'message': 'invalid file type'}))
        else:
          filename = secure_filename(file.filename)
          complete_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
          file.save(complete_filename)
          upload_document = db.inventory_management.find_one({'type': 'allbid_upload'})
          if upload_document['complete'] == False:
            return make_response(jsonify({'success': False, 'message': 'another upload already ongoing'}))
          db.inventory_management.update_one({'type':'allbid_upload'}, {'$set': {'processing_time': 0.0, 'complete': False, 'items_processed': 0, 'items_available': 0, 'new_items': 0, 'changed_prices': 0, 'deleted_items': 0}}, upsert=True)
          t = Thread(target=process_allbid, args=(complete_filename,))
          t.start()
          return make_response(jsonify({'success': True}))
  return render_template('import_unfi_allbid.html', assets_url=assets_url)


def process_allbid(filename):
  try:
    process_client = MongoClient(mongo_url)
  except:
    return 'database error'
  else:
    process_db = process_client[db_name]

  starting_time = time.time()
  
  file_in = open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
  new_count = 0
  update_count = 0
  delete_count = 0
  items_processed = 0
  items_available = 0
  reader = csv.reader(file_in, quotechar='\"')
  for row in reader:
    items_processed += 1
    if items_processed % 100 == 0:
      process_db.inventory_management.update_one({'type': 'allbid_upload'}, {'$set': {'items_processed': items_processed, 'items_available': items_available, 'new_items': new_count, 'changed_prices': update_count, 'deleted_items': delete_count, 'processing_time': (time.time() - starting_time)}})
    if 'T' in row[20] or 'P' in row[20]:
      items_available += 1
      APPRV = row[8]
      if APPRV[0:4] == '*DIS':
        process_db.allbid.delete_one({'item_id': row[15].replace('-', '').replace('00', '', 1)})
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
        if APPRV == '*Chg':
          allbid_item['cost_change'] = True
          update_count += 1
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

        process_db.allbid.update_one({'item_id': allbid_item['item_id']}, {'$set': {'case_quantity': allbid_item['case_quantity'], 'package_size': allbid_item['package_size'], 'description': allbid_item['description'], 'new': allbid_item['new'], 'cost_change': allbid_item['cost_change'], 'case_cost': allbid_item['case_cost'], 'suggested_retail_price': allbid_item['suggested_retail_price'], 'order_code': allbid_item['order_code']}}, upsert=True)

        if process_db.inventory.find_one({'item_id': allbid_item['item_id']}) != None:
          process_db.inventory.update_one({'item_id': allbid_item['item_id']}, {'$set': {'case_cost': allbid_item['case_cost'], 'suggested_retail_price': allbid_item['suggested_retail_price'], 'order_code': allbid_item['order_code']}})
  file_in.close()
  process_db.inventory_management.update_one({'type': 'allbid_upload'}, {'$set': {'items_processed': items_processed, 'items_available': items_available, 'new_items': new_count, 'changed_prices': update_count, 'deleted_items': delete_count, 'complete': True, 'processing_time': (time.time() - starting_time)}})
  


@app.route('/hardware/', methods=['POST', 'GET'])
def hardware():
  session_key = request.cookies.get('natapos_session_key')  
  if request.method == 'POST':
    if request.form['function'] == 'login':
      if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        source_ip = request.environ['REMOTE_ADDR']
      else:
        source_ip = request.environ['HTTP_X_FORWARDED_FOR']
      login_check = {}
      login_check = validate_login(db, request.form['username'], request.form['password'], source_ip)
      if login_check['success'] == False:
        config = db.natapos.find_one({'config': 'global'})
        return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url, error=login_check['error'])
      else:
        response =  redirect('/hardware/')
        response.set_cookie('natapos_session_key', login_check['session_key'])
        return response
  result = validate_session_key(db, session_key)
  if result['success'] == False:
    config = db.natapos.find_one({'config': 'global'})
    return render_template('login.html', instance_name=config['instance_name'], assets_url=assets_url)
  employee_info = db.employees.find_one({'type': 'user', 'username': result['username']})
  if 'hardware' not in employee_info['permissions'] and 'superuser' not in employee_info['permissions']:
    return redirect('/')
  if request.method == 'POST':
    if request.form['function'] == 'log_out':
      db.session_keys.delete_one({'session_key': session_key})
      return redirect('/')
    elif request.form['function'] == 'main_menu':
      return redirect('/')
    elif request.form['function'] == 'admin':
      return redirect('/admin/')
    elif request.form['function'] == 'add_shelf_tag_printer':
      if is_valid_string(request.form['hardware_id']) == False:
        return make_response(jsonify({'success': False, 'message': 'invalid name'}))
      if is_valid_ip_address(request.form['location']) == False:
        return make_response(jsonify({'success': False, 'message': 'invalid ip address'}))
      db.natapos.insert_one({'type': 'hardware', 'hardware_id': request.form['hardware_id'], 'hardware_type': 'shelf_tag_printer', 'driver': request.form['driver'], 'location': request.form['location']})
      return make_response(jsonify({'success': True, 'html': render_template('hardware_shelf_tag_printer_list.html', shelf_tag_printers=get_shelf_tag_printer_collection(db))}))
  return render_template('hardware.html', assets_url=assets_url, shelf_tag_printers=get_shelf_tag_printer_collection(db))
