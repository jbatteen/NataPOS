def calculate_worked_hours(timesheet):
  del timesheet['username']
  del timesheet['pay_period']
  del timesheet['worked_hours']
  del timesheet['_id']
  timestamps = sorted(timesheet)
  worked_seconds = 0
  worked_hours = 0.0
  last_punch_type = ''
  last_punch_time = 0
  current_punch_type = ''
  number_of_punches = len(timestamps)
  if number_of_punches == 1:
    return 0.0
  count = 0
  for i in timestamps:
    count += 1
    current_punch_type = timesheet[i]
    if count > 1:
      if current_punch_type == 'out' and last_punch_type == 'in':
        worked_seconds = worked_seconds + (int(i) - last_punch_time)
    last_punch_type = current_punch_type
    last_punch_time = int(i)
  worked_hours = float(worked_seconds) / 3600.0
  return worked_hours

def price_to_float(price = '$0.00'):
  newstring = ''
  for i in price:
    if i != '$':
      newstring = newstring + i
  return float(newstring)

def float_to_price(input_float = 0.0):
  newstring = str(round(input_float, 2))
  splitstring = newstring.split('.')
  newstring = '$' + newstring
  if len(splitstring[1]) == 1:
    newstring = newstring + '0'
  return newstring
  
def float_to_percent(input_float):
  percent = round((input_float * 100), 1)
  newstring = str(percent)
  newstring = newstring + '%'
  return newstring

def percent_to_float(input_string):
  newstring = ''
  for i in input_string:
    if i != '%':
      newstring = newstring + i
  percent = float(newstring) / 100
  return percent