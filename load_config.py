from pymongo.mongo_client import MongoClient
def load_config(dbname, mongouri):
  client = MongoClient(mongouri)
  db = client[dbname]
  try:  # if natapos config db exists
    db.validate_collection("config")
  except: # no db, load defaults
    business_name = "NataPOS"
    assets_url = "http://192.168.1.157"
  else: # load config
    print('load config')


  return [business_name, assets_url]





# config[0] = business_name
# config[1] = assets_url

