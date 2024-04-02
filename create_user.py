import bcrypt
from pymongo.mongo_client import MongoClient

def create_user(db, username, password, admin=False):
  if password != '':
    bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)
    result = db.employees.insert_one({'username': username, 'password': hash, 'admin': admin})
    print(str(result[acknowledged]))
    return True
