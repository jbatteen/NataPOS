
import socket
import zpl
from calculations_and_conversions import float_to_price
from datetime import date
from pymongo.mongo_client import MongoClient



def print_shelf_tag(db, item_id='', hardware_id=''):
  if item_id == '':
    return({'success': False, 'message': 'bad item_id'})
  item = db.inventory.find_one({'item_id': item_id})
  if item == None:
    return({'success': False, 'message': 'item not found in inventory'})
  if hardware_id == '':
    return({'success': False, 'message': 'bad hardware_id'})
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

  price = float_to_price(item['regular_price'])
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
  
  printer_document = db.natapos.find_one({'type': 'hardware', 'hardware_id': hardware_id})

  mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
  try:
    mysocket.connect((printer_document['location'], 9100))
    mysocket.send(label.dumpZPL().encode('utf-8'))
    mysocket.close ()
  except:
    return({'success': False, 'message': 'Error with the connection'})

  return ({'success': True})

def get_shelf_tag_printer_list(db):
  printer_collection = db.natapos.find({'type': 'hardware', 'hardware_type': 'shelf_tag_printer'})
  printer_list = []
  for printer in printer_collection:
    printer_list.append(printer['hardware_id'])
  return printer_list

def get_shelf_tag_printer_collection(db):
  printer_collection = db.natapos.find({'type': 'hardware', 'hardware_type': 'shelf_tag_printer'})
  new_collection = []
  for printer in printer_collection:
    del printer['_id']
    new_collection.append(printer)
  return new_collection