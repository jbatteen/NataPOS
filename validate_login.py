from pymongo.mongo_client import MongoClient
import bcrypt
import random
import time

def validate_login(db, username, password):
  document = db.employees.find_one({'username' : username})
  if document is not None:
    check_hash = password.encode('utf-8')
    hash = document['password']
    password_ok = bcrypt.checkpw(check_hash, hash)
    if password_ok == True:
      db.session_keys.delete_many({'username': username})
      session_key = ''.join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890") for _ in range(40))
      time_int = int(round(time.time()))
      result = db.session_keys.insert_one({'session_key': session_key, 'time_stamp': time_int, 'username': username})
      return {'success': True, 'session_key': session_key}
    else:
      return {'success': False, 'error': 'wrong password'}
  else:
    return {'success': False, 'error': 'no such user in system'}
