# NataPOS
Natural Abundance Point Of Sale system
This is a point of sale system being written for Natural Abundance Food Co-op, a cooperative grocery store in Aberdeen, South Dakota.
I'm the IT manager there, and I'm not happy with the available options, commercial or open-source.  Our needs are few but specific.
I'm building this with the intention that it can be re-used by others.  It's primarily designed for members of NCG, National Cooperative Grocers, but presumably anyone could use it if it fit their needs.  Some features will be extraneous.
I'm more familiar with programming than I am with the operation of grocery stores, but I am intending to design this to be as generic and extensible as possible for unforeseen future uses.
This is being developed on OpenBSD, which does not always have the most up-to-date packages in the package manager.  I don't yet have the skillset to compile more up-to-date versions from source, so I use what's there.  Currently that's Python 3.10.13 and MongoDB 4.4.24.

pip packages:
bcrypt
pymongo
flask
waitress

Almost all configuration is done through the app and stored on a database, but there are some constants configured in config.py:
  db_name = name of the database to store everything in
  mongo_uri = location of the mongod instance
  assets_url = location of the static elements of the site such as css and images
  business_name = name of the business to be displayed on the interface

The app expects stylesheets and images hosted at assets_url.

All registers connect with a web browser.  The barcode scanner is directly connected to the machine running the browser.  All other peripherals, such as scale, cash register, receipt and label printers, and card readers, are connected over the network.  All computation happens on the server running the flask app.  The browsers/registers are effectively dumb terminals.  All data is stored in the database, so theoretically one could write an entirely new application that could still interface with the information in the database if so desired.

I have the database schema sketched out on paper but not set in stone yet.  More information to come.
