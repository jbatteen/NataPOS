import string
from datetime import datetime, date, timedelta

def is_valid_string(input_string=''):
  allowed = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 .,()-+')
  for i in input_string:
    if i not in allowed:
      return False
  return True

def is_valid_password(input_string=''):
  allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 .,()[]\{\}!@#$%^&*-+_;:<>/\\")
  for i in input_string:
    if i not in allowed:
      return False
  return True

def is_valid_date(input_string=''):
  allowed = set("0123456789/")
  for i in input_string:
    if i not in allowed:
      return False
  ymd = input_string.split('/')
  if len(ymd) != 3:
    return False
  if len(ymd[2]) > 2:
    return False
  input_month = int(ymd[0])
  input_day = int(ymd[1])
  input_year = int(ymd[2]) + 2000
  try:
    test_date = date(input_year, input_month, input_day)
  except:
    return False
  print(test_date)
  print('valid date')
  return True
 # return True


def is_date_within_range(input_string='', checkdiff=0):
  allowed = set("0123456789/")
  for i in input_string:
    if i not in allowed:
      return False
  ymd = input_string.split('/')
  if len(ymd) != 3:
    return False
  if len(ymd[2]) > 2:
    return False
  input_month = int(ymd[0])
  input_day = int(ymd[1])
  input_year = int(ymd[2]) + 2000
  try:
    test_date = date(input_year, input_month, input_day)
  except:
    return False
  today = date.today()
  if (today - test_date) > timedelta(days=checkdiff):
    return False
  return True

def is_valid_pay_period_rollover(input_string=''):
  allowed = set("0123456789")
  result = True
  for i in input_string:
    if i not in allowed:
      return False
  input_int = int(input_string)
  if input_int < 10 or input_int > 19:
    return False
  else:
    return True