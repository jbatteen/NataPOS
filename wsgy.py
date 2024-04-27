import os
from waitress import serve
from app import app

this_files_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(this_files_dir)
serve(app, host='0.0.0.0', port=8080)
