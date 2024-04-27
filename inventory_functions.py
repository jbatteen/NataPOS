from pymongo.mongo_client import MongoClient
from calculations_and_conversions import float_to_price, price_to_float, float_to_percent
import socket
import zpl
from datetime import date

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

def get_brand_list(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  collection = db.inventory_management.find({'type': 'brand'})
  brand_list= []
  for brand in collection:
    brand_list.append(brand['brand_id'])
  return brand_list


def get_brand_collection(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  brand_collection = []
  collection = db.inventory_management.find({'type': 'brand'})
  for brand in collection:
    del brand['_id']
    brand_collection.append(brand)
  return brand_collection
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


def beautify_item(db, input_item):
  beautified = {}
  cost_per = round((input_item['case_cost'] / input_item['case_quantity']), 2)
  if cost_per == 0.0:
    cost_per = 0.01
  beautified['cost_per'] = float_to_price(cost_per)
  beautified['suggested_margin'] = float_to_percent((input_item['suggested_retail_price'] / cost_per) - 1)
  beautified['margin'] = float_to_percent((input_item['regular_price'] / cost_per) - 1)
  for i in input_item:
    if i == 'item_id':
      beautified[i] = input_item[i]
    if i == 'name':
      beautified[i] = input_item[i]
    elif i == 'description':
      beautified[i] = input_item[i]
    elif i == 'package_size':
      beautified[i] = input_item[i]
    elif i == 'receipt_alias':
      beautified[i] = input_item[i]
    elif i == 'memo':
      beautified[i] = input_item[i]
    elif i == 'case_cost':
      beautified[i] = float_to_price(input_item[i])
    elif i == 'case_quantity':
      if input_item[i] % 1 == 0.0:
        beautified[i] = str(int(input_item[i]))
      else:
        beautified[i] = str(input_item[i])
    elif i == 'employee_discount':
      beautified[i] = float_to_percent(input_item[i])
    elif i == 'suggested_retail_price':
      beautified[i] = float_to_price(input_item[i])
    elif i == 'taxes':
      beautified[i] = input_item[i]
    elif i == 'item_location':
      beautified[i] = input_item[i]
    elif i == 'backstock_location':
      beautified[i] = input_item[i]
    elif i == 'last_sold':
      beautified[i] = input_item[i]
    elif i == 'active':
      beautified[i] = str(input_item[i])
    elif i == 'regular_price':
      beautified[i] = float_to_price(input_item[i])
    elif i == 'most_recent_delivery':
      beautified[i] = input_item[i]
    elif i == 'quantity_on_hand':
      if input_item[i] % 1 == 0.0:
        beautified[i] = str(int(round(input_item[i])))
      else:
        beautified[i] = str(input_item[i])
    elif i == 'quantity_low':
      if input_item[i] % 1 == 0.0:
        beautified[i] = str(int(round(input_item[i])))
      else:
        beautified[i] = str(input_item[i])
    elif i == 'quantity_high':
      if input_item[i] % 1 == 0.0:
        beautified[i] = str(int(round(input_item[i])))
      else:
        beautified[i] = str(input_item[i])
    elif i == 'unit':
      beautified[i] = input_item[i]
    elif i == 'supplier':
      beautified[i] = input_item[i]
    elif i == 'order_code':
      beautified[i] = input_item[i]
    elif i == 'department':
      beautified[i] = input_item[i]
    elif i == 'break_pack_quantity':
      if round((input_item[i] % 1), 3) == 0.0:
        beautified[i] = str(int(input_item[i]))
      else:
        beautified[i] = str(input_item[i])
    elif i == 'break_pack_item_id':
      if input_item[i] != '':
        break_pack_item = db.inventory.find_one({'item_id': input_item[i]})
        beautified[i] = break_pack_item['name']
      else:
        beautified[i] = ''
    elif i == 'category':
      beautified[i] = input_item[i]
    elif i == 'subcategory':
      beautified[i] = input_item[i]
    elif i == 'brand':
      beautified[i] = input_item[i]
    elif i == 'item_groups':
      beautified[i] = input_item[i]
    elif i == 'local':
      beautified[i] = str(input_item[i])
    elif i == 'organic':
      beautified[i] = str(input_item[i])
    elif i == 'wic_eligible':
      beautified[i] = str(input_item[i])
    elif i == 'ebt_eligible':
      beautified[i] = str(input_item[i])
    elif i == 'consignment':
      beautified[i] = str(input_item[i])
    elif i == 'date_added':
      beautified[i] = input_item[i]
    elif i == 'discontinued':
      beautified[i] = str(input_item[i])
    elif i == 'food_item':
      beautified[i] = str(input_item[i])
    elif i == 'random_weight_per':
      beautified[i] = str(input_item[i])
    elif i == 'age_restricted':
      beautified[i] = str(input_item[i])
  return beautified


def get_item_group_list(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  item_group_list = []
  collection = db.inventory_management.find({'type': 'item_group'})
  for item_group in collection:
    item_group_list.append(item_group['item_group_id'])
  return item_group_list


def get_department_list(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  collection = db.inventory_management.find({'type': 'department'})
  department_list= []
  for department in collection:
    department_list.append(department['department_id'])
  return department_list


def get_department_collection(db):
  try:
    db.validate_collection("inventory_management")
  except:
    return []
  department_collection = []
  collection = db.inventory_management.find({'type': 'department'})
  for department in collection:
    del department['_id']
    department_collection.append(department)
  return department_collection



def print_shelf_tag(item = None, location_id=''):
  if item == None:
    return()
  if location_id == '':
    return ()
  label = zpl.Label(30, 60, 8)
  label.origin(4,4)
  label.write_text(item['receipt_alias'][:28], char_height=6, char_width=4, line_width=55, justification='L')
  label.endorigin()

  label.origin(4, 10)
  label.write_text(item['brand'], char_height=5, char_width=3, line_width=25, justification='L')
  label.endorigin()



  label.origin(3, 20)
  if item['local'] == True:
    label.write_text('Local', char_height=6, char_width=3, line_width=16, justification='L')
  label.endorigin()

  if item['food_item'] == True:
    label.origin(11, 20)
    if item['organic'] == True:
      label.write_text('Organic', char_height=6, char_width=5, line_width=20, justification='L')
    else:
      label.write_text('Conventional', char_height=6, char_width=3, line_width=20, justification='L')
    label.endorigin()


  locations_list = item['locations']
  price = ''
  for location in locations_list:
    if location['location_id'] == location_id:
      price = float_to_price(location['regular_price'])

  label.origin(25, 10)
  if len(price) <= 5:
    label.write_text(price, char_height=12, char_width=12, line_width=35, justification='L')
  elif len(price) == 6:
    label.write_text(price, char_height=12, char_width=10, line_width=35, justification='L')
  elif len(price) >= 7:
    label.write_text(price, char_height=12, char_width=8, line_width=35, justification='L')
  label.endorigin()

  label.origin(5, 26)
  label.barcode('U', item['item_id'], height=30, check_digit='Y')
  label.endorigin()

  label.origin(28, 27)
  label.write_text(item['department'][:15], char_height=4, char_width=3, line_width=27, justification='C')
  label.endorigin()


  today = date.today()
  today_string = today.strftime('%m/%d/%y')
  label.origin(30, 22)
  label.write_text(today_string, char_height=4, char_width=3, line_width=20, justification='L')
  label.endorigin()

  label.origin(45, 20)
  if item['unit'] == 'each':
    label.write_text('/ea', char_height=5, char_width=3, line_width=10, justification='L')
  if item['unit'] == 'ounces':
    label.write_text('/oz', char_height=5, char_width=3, line_width=10, justification='L')
  if item['unit'] == 'pounds':
    label.write_text('/lb', char_height=5, char_width=3, line_width=10, justification='L')
  if item['unit'] == 'gallon':
    label.write_text('/gal', char_height=5, char_width=3, line_width=10, justification='L')
  


  mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)         
  host = "192.168.1.159" 
  port = 9100   
  try:           
    mysocket.connect((host, port)) #connecting to host
    mysocket.send(label.dumpZPL().encode('utf-8'))
    
    mysocket.close () #closing connection
  except:
    print("Error with the connection")

  return ()