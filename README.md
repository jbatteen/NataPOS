# NataPOS
## Natural Abundance Point Of Sale system
**This is not a working product yet and is undergoing rapid development.  Don't try to use this code now.  Also everything is in the middle of a reconfiguration so now is an especially bad time 4-25-24**  

This is a point of sale system being written for Natural Abundance Food Co-op, a cooperative grocery store in Aberdeen, South Dakota.  I'm the IT manager there, and I'm not happy with the available options, commercial or open-source.  Some of them are fine but too expensive, some of them are inexpensive but difficult to use or lacking in features.  Our needs are few but specific.  

Not that I expect anyone to, but I'm building this with the intention that it can be re-used by others.  It's primarily designed for members of NCG, National Cooperative Grocers, but presumably anyone could use it if it fit their needs.  Some features would be extraneous.  I'm more familiar with programming than I am with the operation of grocery stores, but I am intending to design this to be as generic and extensible as possible for unforeseen future uses.  

This is being developed on Debian 12, using python 3.11.2 and mongodb 7.0.8.

pip packages required:
- bcrypt
- pymongo
- flask
- waitress
- zpl

Almost all configuration is done through the app and stored on a database, but there are some constants configured in config.py:
- db_name = name of the database to store everything in
- mongo_uri = location of the mongod instance
- assets_url = location of the static elements of the site such as css and images

The app expects stylesheets and images hosted at assets_url.  

All registers connect with a web browser.  The barcode scanner is directly connected to the machine running the browser.  Tentatively, all other peripherals, such as scale, cash register, receipt and label printers, and card readers, are connected over the network.  All computation happens on the server running the flask app.  The browsers/registers are effectively dumb terminals.  All data is stored in the database, so theoretically one could write an entirely new application that could still interface with the information in the database if so desired.  

## Links
[Database Schema](database.md)
