If it's in the 'working' category, it has a page that uses it that is user configurable to the extent sensible and allowable.  It might not be done and perfect but it works.  These schema are still subject to change but will probably keep looking more or less like they do.

If it's in the 'todo' category, it's all ideas and hypotheticals and will probably end up looking different once the specifics of implementation become clear.

# Working
## global_config (natapos collection, 'type': 'global_config')
- 'instance_name': str (the business name to display)
- 'current_pay_period_start': str (MM/DD/YY) defaults to starting on the most recent sunday on instance spinup
- 'timesheets_locked': bool (used to lock the timesheets to perform pay period rollover safely wrt clocking in/out)
- 'employee_discount': float (default employee discount for new items)
- 'phone': str (phone number)
- 'address': str (street address)
- 'taxes': list of dict {'tax_id': str (name of tax), 'rate': float (tax rate)}
- 'default_taxes': list of [str('tax_id')]

## session_keys
- 'session_key': str (40 random alphanumeric characters)
- 'time_stamp': last activity, in seconds after the epoch
- 'username': str (username of the employee logged in)
- 'source_ip': str (ip user logged in from)
- 'last_shelf_tag_printer': str (hardware_id of last shelf tag printer used)

## timesheets
- 'pay_period': str('current' or 'MMDDYY-MMDDYY' once rolled over by the nightly audit at end of pay period)
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
- 'package_size': str( '10 oz', str(int) + ' ' + unit)
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
- 'regular_price': float (price before sales/discounts/etc)
- 'quantity_on_hand': float
- 'most_recent_delivery': str (MMDDYY)
- 'quantity_low': float (low alert quantity)
- 'quantity_high': float (plenty on hand quantity)
- 'item_location': str (location of item in store eg aisle 5)
- 'backstock_location': str (location of backstock in store eg dry storage)
- 'last_sold': str(MMDDYY)
- 'active': bool (to keep buying or not)
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

## departments  (inventory_management collection,  'type': 'department')
- 'department_id': str (unique identifier for department)
- 'categories': list of[{'category_id': str (category id), 'subcategories': ['subcategory_id', 'subcategory_id']}]
- 'default_employee_discount': float (percent off for employees)
- 'default_margin': float (percentage)
- 'default_ebt_eligible': bool
- 'default_food_item': bool
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

### available permissions:
- 'superuser': all permissions
- 'employee_management': add/modify users
- 'inventory_management': add/remove/modify items in inventory
- 'suppliers_departments_brands': add/change suppliers, departments, brands
- 'shrink': shrink items
- 'hardware': add/remove connected hardware

## allbid
- 'item_id': str (upc)
- 'order_code': str (UNFI order number)
- 'case_quantity': float (number in a case)
- 'package_size': str ('10 oz' etc)
- 'description': str (UNFI provided description)
- 'new': bool (UNFI provided new item or no)
- 'cost_change': bool (UNFI provided cost change or no)
- 'case_cost': float (cost per case)
- 'suggested_retail_price': str (UNFI suggested retail price)

## allbid_upload (inventory_management collection, 'type': 'allbid_upload')
- 'processing_time': float (seconds)
- 'complete': bool (processing complete)
- 'items_processed': int (items in the allbid)
- 'items_available': int (items at warehouses we get stuff from)
- 'new_items': int
- 'changed_prices': int
- 'deleted_items': int

## hardware (natapos collection, 'type': 'hardware')
- 'hardware_id': str (unique identifier for hardware eg 'pax s300 card reader sn9789')
- 'hardware_type': str ('shelf_tag_printer', 'card_reader', 'receipt_printer', 'label_printer' )
- 'driver': str('zebra', 'pax_s300')
- 'location': str ('192.168.1.159' or 'http://192.168.1.159:8080/')

# to do (everything in this section is tentative and will almost certainly be modified as it is implemented)

## registers
- 'register_id': str (unique identifier)
- 'current_transaction': str (transaction_id) or '' if none/new
- 'ip_address': str (ip address of interface)
- 'linked_hardware': list of str (hardware_id)
- 'open': str ('no', username)

## unique_inventory
- type: str ('markdown', 'unique_item', 'pre_measured')
- tbd

## gift_cards
- 'gift_card_id': str (scan code for gift card)
- 'value': float ($ value remaining)
- 'purchased': str (MMDDYY)
- 'tied_member_account': str (member_id or '' for none)
- 'alternate id': str (any other way to tie this to an owner, or '')

## members
- 'member_id': str (member number)
- 'name': str (however you want to use this, owner name or family name usually)
- 'linked_transactions': list of str (transaction_id)
- 'phone': str (phone number)
- 'email': str (email)
- 'join_date': str (join date MM/DD/YY)
- 'password': str (bcrypt hash of password)

## transactions
- 'time_started': str (YYMMDDHHMMSS) time transaction started
- 'time_completed': str (YYMMDDHHMMSS) time transaction completed or '' for incomplete
- 'register': str (register_id or 'online')
- 'member_id': str (member_id) or ''
- 'status': str ('unpaid', 'paid', 'background', 'voided')
- 'clerk': str (username of employee making the transaction or account_id of online account)
- 'payments': dictionary of
  - str (payment type, 'credit', 'debit', 'ebt', 'cash', 'gift_card', 'check'): float ($ paid)
- items: list of dictionary of
  - 'item_id': str(item_id)
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
- 'eligibility': i don't even know
