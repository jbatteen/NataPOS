# NataPOS
## Natural Abundance Point Of Sale system
**This is not a working product yet and is undergoing rapid development.  Don't try to use this code now.**  

Todo 4-29-24: clean up hardware management page, make UNFI-specific section of vendor page with allbid upload settings, implement delivery mode, implement sales and importing sales from LBMX, implement coupons, implement membership, implement unique item barcodes, then can start building the cash register

This is a point of sale system being written for Natural Abundance Food Co-op, a cooperative grocery store in Aberdeen, South Dakota.  I'm the IT manager there, and I'm not happy with the available options, commercial or open-source.  Some of them are fine but too expensive, some of them are inexpensive but difficult to use or lacking in features.  Our needs are few but specific. 

Not that I expect anyone to, but I'm building this with the intention that it can be re-used by others.  It's primarily designed for members of NCG, National Cooperative Grocers, but presumably anyone could use it if it fit their needs.  Some features would be extraneous.  No doubt there are features larger stores need that our store does not.  I could maybe be convinced to add some features, it never hurts to ask.  If you have any suggestions or feedback on features or programming style/methods I'm very open to hearing it.  This is my first project of this size and I have a lot to learn.  

This is being developed on Debian 12, using python 3.11.2 and mongodb 7.0.8, though so far it's platform independent and has also been confirmed to work on OpenBSD 7.5.  

pip packages required:
- bcrypt
- pymongo
- flask
- waitress
- zpl

Almost all configuration is done through the app and stored on a database, but there are some constants configured in config.py:
- db_name = name of the database to store everything in
- mongo_url = location of the mongod instance
- assets_url = location of the static elements of the site such as css and images

The app expects the assets folder hosted at assets_url.  Add your own logo.png to be displayed in the upper left corner of the interface, and favicon.ico.  You can adjust the color scheme in the css if desired.  You'll probably want to put it behind a reverse proxy supporting TLS for actual production usage.  

The first time you fire it up and connect to the root directory you will be prompted to create the first user, then brought to the global configuration page where you should adjust the settings.  Next you'll want to add suppliers, departments and brands, add employees, and configure hardware.

New UNFI allbid csv files can be imported as they are delivered under Admin -> Import Data.  It only saves information for items available at the warehouses we get deliveries from, which are set in config.py (for now).  After that, in view/edit item mode and delivery checkin mode (not built yet), if you scan an item that isn't in your inventory, it will give you the option to pre-populate fields with information from the allbid.

Registers (not built yet) connect with a web browser as dumb terminals.  All computation happens on the server running the flask POS app.  The interface is designed to be touchscreen friendly as much as possible, and generally scales well with screen size and aspect ratio.  The barcode scanner is directly connected to the machine running the browser in keyboard emulation mode.  All other peripherals, such as scale, cash register, receipt and label printers, and card readers, are connected over the network.  Peripherals that don't have a network option will be networked by an app on the machine they are connected to, independent of the web browser.

## Links
[Database Schema](database.md)
