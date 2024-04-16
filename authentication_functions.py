from pymongo.mongo_client import MongoClient
import bcrypt
import random
import time
import ipaddress
from inventory_functions import get_locations_collection

def validate_login(db, username, password, source_ip):
  document = db.employees.find_one({'type': 'user', 'username' : username})
  if document is not None:
    check_hash = password.encode('utf-8')
    hash = document['password']
    password_ok = bcrypt.checkpw(check_hash, hash)
    if password_ok == True:
      db.session_keys.delete_many({'username': username})
      session_key = ''.join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890") for _ in range(40))
      time_int = int(round(time.time()))
      locations_collection = get_locations_collection(db)
      ip_address = ipaddress.ip_address(source_ip)
      login_location = 'external'
      for location in locations_collection:
        ip_range = ipaddress.ip_network(location['ip_range'])
        if ip_address in ip_range:
          login_location = location['location_id']
      result = db.session_keys.insert_one({'session_key': session_key, 'time_stamp': time_int, 'username': username, 'login_location': login_location})
      return {'success': True, 'session_key': session_key}
    else:
      return {'success': False, 'error': 'wrong password'}
  else:
    return {'success': False, 'error': 'no such user in system'}

def validate_session_key(db, session_key):
  if session_key == '':
    return({'success': False})
  document = db.session_keys.find_one({'session_key': session_key})
  if document is not None:
    current_time = int(round(time.time()))
    time_stamp = int(document['time_stamp'])
    if current_time - time_stamp < 3600:
      db.session_keys.update_one({'session_key': session_key}, {'$set': {'time_stamp': current_time}})
      return({'success': True, 'username': document['username'], 'login_location': document['login_location']})
    else:
      db.session_keys.delete_one({'session_key': session_key})
      return({'success': False})
  else:
    return({'success': False})
  

def end_session(db, session_key):
  db.session_keys.delete_one({'session_key': session_key})

def create_user(db, username, password, permissions=[], address='', name='', short_name='', title='', phone='', email='', hire_date='', login_message=''):
  bytes = password.encode('utf-8')
  salt = bcrypt.gensalt()
  hash = bcrypt.hashpw(bytes, salt)
  result = db.employees.insert_one({'type': 'user', 'username': username, 'password': hash, 'address': address, 'permissions': permissions, 'status': 'current', 'name': name, 'short_name': short_name, 'title': title, 'phone': phone, 'email': email, 'hire_date': hire_date, 'login_message': login_message})
  return {'success' : True}