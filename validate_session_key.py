from pymongo.mongo_client import MongoClient

def validate_session_key(db, session_key):
  try:  # if natapos config collection exists
    db.validate_collection("natapos")
  except: # no collection, fail
    return [False, '']
  else: # load config
    print('validate login')
    return [True, 'sample user']
