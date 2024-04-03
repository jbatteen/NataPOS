import bcrypt
from pymongo.mongo_client import MongoClient

def create_user(db, username, password, admin=False):
  bytes = password.encode('utf-8')
  salt = bcrypt.gensalt()
  hash = bcrypt.hashpw(bytes, salt)
  result = db.employees.insert_one({'username': username, 'password': hash, 'admin': admin, 'status': 'current'})
  return {'success' : True}
