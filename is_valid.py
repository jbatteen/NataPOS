import string

def is_valid_string(input_string=''):
  allowed = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 .,()-+')
  result = True
  for i in input_string:
    if i not in allowed:
      result = False
  return result
def is_valid_password(input_string=''):
  allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 .,()[]{}!@#$%^&*-+_;:<>/\\")
  result = True
  for i in input_string:
    if i not in allowed:
      result = False
  return result