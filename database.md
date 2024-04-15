# Working
## natapos
- 'instance_name': str (the business name to display)
- 'pay_period_type': str ('weekly', 'biweekly', 'bimonthly'), defaults to biweekly on instance spinup
- 'current_pay_period': str (MM/DD/YY-MM/DD/YY), for weekly/biweekly, defaults to starting on the most recent sunday on instance spinup
- 'pay_period_rollover': int (DD) for bimonthly pay period, pay period rolls over on the 1st and the pay_period_rolloverth, defaults to 15 on instance spinup
- 'timesheets_locked': bool (used to lock the timesheets to perform pay period rollover safely wrt clocking in/out)
- 'employee_discount': float (default employee discount for new items)

## timesheets
- 'username': str (username)
- str (YYMMDDHHMMSS timestamp): str ('in', 'out')

## inventory
- 'item_id': str (UPC/PLU)
- 'previous_item_id': str (UPC/PLU) (use this to link items for sales reports, to keep continuous sales data when UPCs change)
- 'name': str (human readable name, goes on register display)
- 'receipt_alias': str (shortened version for receipt printing)
- 'description': str (long form description, visible to customer in places)
- 'memo': str (internal, never visible to customer)
- 'picture': str (url to picture)
- 'suggested_retail_price': float ($price)
- 'unit': str ('ea', 'lb', 'oz', etc)
- 'supplier': str ('supplier_id')
- 'order_code': str (if supplier uses something other than UPC to identify product, like product number etc)
- 'case_quantity': float
- 'case_cost': float ($case cost)
- 'item_groups': list of str (item_group_id)
- 'department': str (department_id)
- 'category': str (category_id)
- 'brand': str (brand_id)
- 'local': bool
- 'discontinued': bool
- 'employee_discount': float (percent)   if present, overrides department/category defaults
- 'age_restricted': int (0 if no, other if age)
- 'food_item': bool
- 'random_weight_per': bool
- 'date_added': str MMDDYY
- 'break_pack_item_id': str (item_id of item this pack contains)
- 'break_pack_quantity': float (number of items in pack)
- 'wic_elegible': bool(WIC eligible)
- 'ebt_eligible': bool(EBT eligible)
- 'consignment': bool(on consignment)
- 'locations' list of dict:
  - 'location_id': str (unique identifier for location)
  - 'regular_price': float (price at this location)
  - 'quantity_on_hand': float (quantity at this location)
  - 'most_recent_delivery': str (MMDDYY)
  - 'quantity_low': float (low alert quantity)
  - 'quantity_high': float (plenty on hand quantity)
  - 'item_location': str (location of item in store eg aisle 5)
  - 'backstock_location': str (location of backstock in store eg dry storage)
  - 'last_sold': str(MMDDYY)
  - 'active': bool(to keep buying or not)
  - 'taxes': list of [str(tax_id)] this item gets charged

## suppliers  (inventory_management collection,  'type': 'supplier')
- 'supplier_id': str (unique supplier identifer eg 'UNFI')
- 'website': str (website url for ordering)
- 'phone': str (phone number)
- 'address':  str (mailing address)
- 'contact_name': str (name of the human we talk to to order stuff)
- 'email': str (email address for ordering)

## item_groups (inventory_management collection, 'type': 'item_group')
- 'item_group_id': str (unique group identifier)
- 'items': list of str (item_id)

## locations (inventory_management collection, 'type': 'location')
- 'location_id': str (unique identifier for store location)
- 'phone': str (phone number)
- 'address': str (street address)
- 'taxes': list of dict {'tax_id': str (name of tax), 'rate': float (tax rate)}
- 'default_taxes': list of [str('tax_id')]

## departments  (inventory_management collection,  'type': 'department')
- 'department_id': str (unique identifier for department)
- 'categories': list of[{'category_id': str (category id), 'subcategories': ['subcategory_id', 'subcategory_id']}]
- 'default_employee_discount': float (percent off for employees)
- 'default_margin': float (percentage)
- 'default_ebt_eligible': bool
- 'default_food_item': bool
- 'location_defaults': [list] of dict:
  - 'location_id': str (location_id)
  - 'default_online_ordering': str ('yes' or 'no')
  - 'default_taxes': [list of tax_id]

## brands  (inventory_management collection,  'type': 'brand')
- 'brand_id': str (unique brand identifier eg 'Kalona')
- 'website': str (http://)
- 'supplier': str (supplier_id)
- 'local': bool (default for new items)

## employees (employees collection, 'type': 'user')
- 'username': str (username for this system)
- 'password': str (bcrypt hash of password)
- 'name': str (employee's name, however you want to format it)
- 'short_name': str (name to print on receipts and display in register mode)
- 'title': str (job title, does nothing for the program just for your records)
- 'phone': str (phone number)
- 'address': str (address)
- 'email': str (email address)
- 'hire_date': str (hire date YY/MM/DD)
- 'status': str (current, former, other?)
- 'permissions': list of str (permission names the user does/doesn't have)

### permissions:
- 'superuser': all permissions
- 'employee_management': add/modify users
- 'inventory_management': add/remove/modify items in inventory
- 'shrink': shrink items

# to do

## gift_cards
- 'gift_card_id': str (scan code for gift card)
- 'value': float ($ value remaining)
- 'purchased': str (MMDDYY)
- 'tied_member_account': str (member_id or '' for none)
- 'tied_online_account': str (account_id or '' for none)
- 'alternate id': str (any other way to tie this to an owner, or '')

## registers
- 'register_id': str (unique identifier)
- 'location': str (location_identifier)
- 'current_transaction': str (transaction_id) or '' if none/new
- 'ip_address': str (ip address of interface)
- 'linked_hardware': list of str (hardware_id)
- 'open': str ('no', username)

## members
- 'member_id': str (member number)
- 'name': str (however you want to use this, owner name or family name usually)
- 'linked_transactions': list of str (transaction_id)
- 'phone': str (phone number)
- 'email': str (email)
- 'join_date': str (join date MM/DD/YY)
- 'password': str (bcrypt hash of password)

## register_logs
- 'log_id': str (YYMMDDHHMMSS+register_id)
- 'clerk': str (username)
- 'transactions': list of str (transaction_id)

## hardware
- 'hardware_id': str (unique identifier for hardware eg 'pax s300 card reader sn9789')
- 'type': str ('pax s300', 'cash_drawer', 'receipt_printer', 'zebra zd200' )
- 'url': str (http://xxxxxx)

## transactions
- 'time_started': str (YYMMDDHHMMSS) time transaction started
- 'time_completed': str (YYMMDDHHMMSS) time transaction completed or '' for incomplete
- 'register': str (register_id or 'online')
- 'member_id': str (member_id) or ''
- 'status': str ('unpaid', 'paid', 'background', 'voided')
- 'clerk': str (username of employee making the transaction or account_id of online account)
- 'location': str (location_id or 'online')
- 'payments': dictionary of
  - str (payment type, 'credit', 'debit', 'ebt', 'cash', 'gift_card', 'check'): float ($ paid)
- str (item_id): dictionary of
  - 'quantity': float (number of things bought.  float for bulk items by weight)
  - 'regular_price': float (total cost of all in the quantity after bogos discounts etc, what the receipt says for that line)
  - 'sales_tax': float (total sales tax withheld for these items)
  - 'our_cost': float (what the store paid for the items we sold)
  - 'coupons_applied': str (coupon UPCs, in a list if multiple)
  - 'override_price': float (if  the cashier overrode the calculated price, include this as well)

## coupons
- 'coupon_id': str (UPC)
- 'name': str (human readable display name, goes on screen & receipt)
- 'eligibility': list of str(item_id) coupon applies to
- 'valid': str(YYMMDD coupon begins being valid)
- 'expires': str(YYMMDD coupon expires)
- 'type': str ('percent', 'discount', 'buyXgetY')   surely more types are to be added
- 'value': float (percent or $ discount)
- 'x': int (buy X)
- 'y': int (get Y)

## discounts
- 'discount_id' str ('senior', 'member')
- 'value': float (percent off)
- 'eligibility': '

