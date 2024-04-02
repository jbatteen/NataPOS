from pymongo.mongo_client import MongoClient
import bcrypt

def validate_login(db, username, password):
  try:  # if employee collection exists
    db.validate_collection("employees")
  except: # no collection, fail
    return [False, "error: sample error"]
  else: # validate login
    document = db.employees.find_one({"username" : username})
    print('validate login')
    check_hash = password.encode('utf-8')
    hash = document['password']
    password_ok = bcrypt.checkpw(check_hash, hash)
    print('password_ok: ' + str(password_ok))
    if password_ok == True:
      return [True, "sample_session_key"]
    else:
      return [False, "wrong password"]
