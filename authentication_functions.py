from pymongo.mongo_client import MongoClient
import bcrypt
import random
import time


def get_employee_collection(db):
  try:
    db.validate_collection("employees")
  except:
    return []
  employee_collection = []
  collection = db.employees.find({'type': 'user'})
  for employee in collection:
    del employee['_id']
    employee_collection.append(employee)
  return employee_collection
def validate_login(db, username, password, source_ip):
  document = db.employees.find_one({'type': 'user', 'username' : username})
  if document is not None:
    check_hash = password.encode('utf-8')
    hash = document['password']
    password_ok = bcrypt.checkpw(check_hash, hash)
    if password_ok == True:
      current_keys = db.session_keys.find({'username': username})
      current_time = int(round(time.time()))
      for key in current_keys:
        if current_time - key['time_stamp'] > 3600:
          db.session_keys.delete_one({'session_key': key['session_key']})

      session_key = ''.join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890") for _ in range(40))
      time_int = int(round(time.time()))
      db.session_keys.insert_one({'session_key': session_key, 'time_stamp': time_int, 'username': username, 'source_ip': source_ip, 'last_shelf_tag_printer': ''})
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
    if current_time - document['time_stamp'] < 3600:
      db.session_keys.update_one({'session_key': session_key}, {'$set': {'time_stamp': current_time}})
      return({'success': True, 'username': document['username'], 'last_shelf_tag_printer': document['last_shelf_tag_printer']})
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