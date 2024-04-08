from pymongo.mongo_client import MongoClient

def get_supplier_list(db):
  try:
    db.validate_collection("suppliers")
  except:
    return []
  suppliers_collection = db.suppliers.find({})
  supplier_list= []
  for i in suppliers_collection:
    supplier_list.append(i['supplier_id'])
  return supplier_list


def get_inventories(db):
  collection_list = db.list_collection_names()
  inventory_list = []
  for collection in collection_list:
    if "inventory" in collection:
      inventory_split = collection.split('_', 1)
      if inventory_split[0] == 'inventory':        
        inventory_list.append(inventory_split[1])
  return inventory_list

def get_suppliers_collection(db):
  try:
    db.validate_collection("suppliers")
  except:
    return []
  sanitized_suppliers_collection = []
  suppliers_collection = db.suppliers.find({})
  for supplier in suppliers_collection:
    del supplier['_id']
    sanitized_suppliers_collection.append(supplier)
  return sanitized_suppliers_collection