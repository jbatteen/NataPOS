from pymongo.mongo_client import MongoClient

def get_supplier_list(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  collection = db.inventory_management.find({'type': 'supplier'})
  supplier_list= []
  for supplier in collection:
    supplier_list.append(supplier['supplier_id'])
  return supplier_list


def get_supplier_collection(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  supplier_collection = []
  collection = db.inventory_management.find({'type': 'supplier'})
  for supplier in collection:
    del supplier['_id']
    supplier_collection.append(supplier)
  return supplier_collection

def get_item_group_list(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  item_group_list = []
  collection = db.inventory_management.find({'type': 'item_group'})
  for item_group in collection:
    del item_group['_id']
    item_group_list.append(item_group['group_id'])
  return item_group_list

def get_location_list(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  location_list = []
  collection = db.inventory_management.find({'type': 'location'})
  for location in collection:
    del location['_id']
    location_list.append(location['location_id'])
  return location_list


def get_locations_collection(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  locations_collection = []
  collection = db.inventory_management.find({'type': 'location'})
  for location in collection:
    del location['_id']
    locations_collection.append(location)
  return locations_collection

def get_item_locations_collection(db, item_id):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  locations_collection = []
  document = db.inventory.find_one({'item_id': item_id})
  locations_collection = document['locations']
  return locations_collection

def calculate_item_locations_collection(incoming_collection=[], cost_per=1.0):
  calculated_collection = []
  for i in incoming_collection:
    i['margin'] = (i['regular_price'] / cost_per) - 1.0
    calculated_collection.append(i)
  return calculated_collection