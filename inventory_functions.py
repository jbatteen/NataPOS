from pymongo.mongo_client import MongoClient

def get_suppliers(db):
  try:
    db.validate_collection("suppliers")
  except:
    return []
  suppliers_collection = db.suppliers.find({})
  suppliers = []
  for i in suppliers_collection:
    suppliers.append(i['supplier_id'])
  return suppliers


def get_inventories(db):
#  config = db.natapos.find_one({'config': 'global'})
#  inventory_list = config['inventories']


  collection_list = db.list_collection_names()
  inventory_list = []
  for collection in collection_list:
    if "inventory" in collection:
      inventory_split = collection.split('_', 1)
      if inventory_split[0] == 'inventory':        
        inventory_list.append(inventory_split[1])
  return inventory_list