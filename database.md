# Collections
## natapos
- 'instance_name': str (the business name to display)
- 'pay_period_type': str ('weekly', 'biweekly', 'bimonthly'), defaults to biweekly on instance spinup
- 'current_pay_period': str (MM/DD/YY-MM/DD/YY), for weekly/biweekly, defaults to starting on the most recent sunday on instance spinup
- 'pay_period_rollover': int (DD) for bimonthly pay period, pay period rolls over on the 1st and the pay_period_rolloverth, defaults to 15 on instance spinup
- 'tax_types': list of str ('Sales', 'Alcohol') (not sure if we're using this field yet)

## employees
- 'username': str (username for this system)
- 'password': str (bcrypt hash of password)
- 'name': str (employee's name, however you want to format it)
- 'short_name': str (name to print on receipts and display in register mode)
- 'title': str (job title, does nothing for the program just for your records)
- 'phone': str (phone number)
- 'email': str (email address)
- 'hire_date': str (hire date YY/MM/DD)
- 'status': str (current, former, other?)
- 'permissions': list of str (permission names the user does/doesn't have)
- 'authorized_locations': list of str (location_id) where the employee is authorized to work

### permissions:
- 'superuser': all permissions, program checks for this first before checking individual permissions
- 'change_users': add/modify users
- 'remove_users': remove users
- 'inventory_management': add/remove/modify items in inventory
- 'shrink': shrink items

## members
- 'member_id': str (member number)
- 'name': str (however you want to use this, owner name or family name usually)
- 'linked_transactions': list of str (transaction_id)
- 'phone': str (phone number)
- 'email': str (email)
- 'join_date': str (join date MM/DD/YY)
- 'password': str (bcrypt hash of password)

## registers
- 'register_id': str (unique identifier)
- 'location': str (location_identifier)
- 'current_transaction': str (transaction_id) or '' if none/new
- 'ip_address': str (ip address of interface)
- 'linked_hardware': list of str (hardware_id)
- 'open': str ('no', username)

## register_logs
- 'log_id': str (YYMMDDHHMMSS+register_id)
- 'clerk': str (username)
- 'transactions': list of str (transaction_id)

## hardware
- 'hardware_id': str (unique identifier for hardware eg 'pax s300 card reader sn9789')
- 'type': str ('pax s300', 'cash_drawer', 'receipt_printer', 'zebra zd200' )
- 'url': str (http://xxxxxx)

## transactions
- 'transaction_id': str (YYMMDDHHMMSS) (while transaction is unpaid or if voided, this is the timestamp of transaction creation.  when it is paid, the id changes to become the time of transaction completion)
- 'register': str (register number)
- 'member': str (member_id)
- 'status': str ('unpaid', 'paid', 'background', 'voided')
- 'clerk': str (username of employee making the transaction)
- 'location': str (location_identifier, store location)
- 'payments': dictionary of
  - str (payment type, 'credit', 'debit', 'ebt', 'cash', 'gift_card', 'check'): float ($ paid)
- str (item_id): dictionary of
  - 'quantity': float (number of things bought.  float for bulk items by weight)
  - 'regular_price': float (total cost of all in the quantity after bogos discounts etc, what the receipt says for that line)
  - 'sales_tax': float (total sales tax withheld for these items)
  - 'our_cost': float (what the store paid for the items we sold)
  - 'coupons_applied': str (coupon UPCs, in a list if multiple)
  - 'override_price': float (if  the cashier overrode the calculated price, include this as well)

## locations
- 'location_id': str (unique identifier for store location)
- 'phone': str (phone number)
- 'address': str (street address)
- 'attached_inventory': str (inventory_id)
- 'default_taxes': list of str (tax_id applied to new items entered in inventory by default)


## departments
- 'department_id': str (unique identifier for department)
- 'sub_inventory': str, '' by default, otherwise inventory_id of separate inventory if you need to keep track of interdepartment sales like deli buying ingredients from store
- 'default_taxes': if present, overrides store default
- 'employee_discount': float (percent off for employees)
- 'categories': dictionary of
  - 'category_id' str (eg 'Chips', 'Diapers')
  - 'default_taxes': if present, overrides department default
  - 'employee_discount': float (percent off for employees)

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

## taxes
- 'tax_type': str ('tax_type') from list of tax types in natapos config db
- 'locality': str (tax district, eg 'Aberdeen, SD')
- 'rate': float (tax rate)

## inventory_<inventory_id>
- 'item_id': str (UPC/PLU)
- 'previous_item_id': str (UPC/PLU) (use this to link items for sales reports, to keep continuous sales data when UPCs change)
- 'name': str (human readable name, goes on register display)
- 'receipt_alias': str (shortened version for receipt printing)
- 'description': str (long form description, visible to customer in places)
- 'memo': str (internal, never visible to customer)
- 'picture': str (url to picture)
- 'regular_price': float (base $price to the customer per unit)
- 'suggested_retail_price': float ($price)
- 'unit': str ('ea', 'lb', 'oz', etc)
- 'supplier': str ('supplier_id')
- 'order_code': str (if supplier uses something other than UPC to identify product, like product number etc)
- 'case_quantity': float
- 'case_price': float ($case price)
- 'item_groups': list of str (item_group_id)
- 'department': str (department_id)
- 'category': str (category_id)
- 'brand': str (brand_id)
- 'local': bool
- 'discontinued': bool
- 'employee_discount': float (percent)   if present, overrides department/category defaults
- 'age_restricted': int (0 if no, other if age)
- 'quantity_on_hand': float
- 'most_recent_delivery': str (MMDDYY)
- 'quantity_low_alert': float (quantity to alert)

## item_groups
- 'item_group_id': str (unique group identifier)
- 'items': list of str (item_id)

## brands
- 'brand_id': str (unique brand identifier eg 'Kalona')
- 'local': bool   default for new items
- 'supplier': str (default supplier_id for new items)

## suppliers
- 'supplier_id': str (unique supplier identifer eg 'UNFI')
- 'website': str (website url for ordering)
- 'phone': str (phone number)
- 'address':  str (mailing address)
- 'contact_name': str (name of the human we talk to to order stuff)
- 'email': str (email address for ordering)

## timesheets
- 'username': str (username)
- 'pay_period': str (pay period identifier)
- str (YYMMDDHHMMSS timestamp): str ('in', 'out')

## gift_cards
- 'gift_card_id': str (scan code for gift card)
- 'value': float ($ value remaining)
- 'purchased': str (MMDDYY)
- 'owner': str (member_id or phone number for nonmember or '' for these people trust themselves not to lose it)