from pymongo.mongo_client import MongoClient
from calculations_and_conversions import float_to_price, price_to_float, float_to_percent

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
  if cost_per == 0.0:
    cost_per = 0.01
  for i in incoming_collection:
    i['margin'] = round(100 * ((i['regular_price'] / cost_per) - 1.0), 1)
    calculated_collection.append(i)
  return calculated_collection

def beautify_item(input_item):
  beautified = {}
  cost_per = round((input_item['case_cost'] / input_item['case_quantity']), 2)
  if cost_per == 0.0:
    cost_per = 0.01
  beautified['cost_per'] = float_to_price(cost_per)
  beautified['suggested_margin'] = float_to_percent((input_item['suggested_retail_price'] / cost_per) - 1)
  for i in input_item:
    if i == 'item_id':
      beautified[i] = input_item[i]
    if i == 'name':
      beautified[i] = input_item[i]
    elif i == 'description':
      beautified[i] = input_item[i]
    elif i == 'receipt_alias':
      beautified[i] = input_item[i]
    elif i == 'memo':
      beautified[i] = input_item[i]
    elif i == 'case_cost':
      beautified[i] = float_to_price(input_item[i])
    elif i == 'case_quantity':
      if input_item['unit'] == 'each':
        beautified[i] = str(int(input_item[i]))
      else:
        beautified[i] = str(input_item[i])
    elif i == 'employee_discount':
      beautified[i] = float_to_percent(input_item[i])
    elif i == 'suggested_retail_price':
      beautified[i] = float_to_price(input_item[i])


    elif i == 'locations':
      new_locations_collection = []
      old_locations_collection = input_item[i]
      for j in old_locations_collection:
        new_location = {}
        new_location['margin'] = float_to_percent((j['regular_price'] / cost_per) - 1)
        for k in j:
          if k == 'location_id':
            new_location[k] = j[k]
          elif k == 'regular_price':
            new_location[k] = float_to_price(j[k])
          elif k == 'quantity_on_hand':
            if input_item['unit'] == 'each':
              new_location[k] = str(int(j[k]))
            else:
              new_location[k] = str(j[k])
          elif k == 'most_recent_delivery':
            new_location[k] = j[k]
          elif k == 'quantity_low':
            if input_item['unit'] == 'each':
              new_location[k] = str(int(j[k]))
            else:
              new_location[k] = str(j[k])
          elif k == 'quantity_high':
            if input_item['unit'] == 'each':
              new_location[k] = str(int(j[k]))
            else:
              new_location[k] = str(j[k])
        new_locations_collection.append(new_location)
      beautified[i] = new_locations_collection
    elif i == 'unit':
      beautified[i] = input_item[i]
    elif i == 'supplier':
      beautified[i] = input_item[i]
    elif i == 'order_code':
      beautified[i] = input_item[i]
    elif i == 'department':
      beautified[i] = input_item[i]
    elif i == 'category':
      beautified[i] = input_item[i]
    elif i == 'brand':
      beautified[i] = input_item[i]
    elif i == 'item_groups':
      beautified[i] = input_item[i]
    elif i == 'local':
      beautified[i] = str(input_item[i])
    elif i == 'discontinued':
      beautified[i] = str(input_item[i])
    elif i == 'age_restricted':
      beautified[i] = str(input_item[i])
  return beautified

