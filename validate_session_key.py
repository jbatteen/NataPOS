from pymongo.mongo_client import MongoClient
import time

def validate_session_key(db, session_key):
  document = db.session_keys.find_one({'session_key': session_key})
  if document is not None:
    current_time = int(round(time.time()))
    time_stamp = int(document['time_stamp'])
    if current_time - time_stamp < 900:
      db.session_keys.update_one({'session_key': session_key}, {'$set': {'time_stamp': current_time}})
      return({'success': True, 'username': document['username']})
    else:
      db.session_keys.delete_one({'session_key': session_key})
      return({'success': False})
  else:
    return({'success': False})
