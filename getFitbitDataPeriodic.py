import configparser
import datetime
import time
import sys
import os
import fitbit
from databaseConnection import DatabaseConnection, DatabaseConfigurator
from bson.json_util import dumps, loads
from sender import EmailSender
from fitBitClient import AuthorizedFitbitClient, ApiClient
import helperFunctions

# Initialize
parser=configparser.ConfigParser()
parser.read('config.ini')

CLIENT_ID=parser.get('Login Parameters', 'CLIENT_ID')
CLIENT_SECRET=parser.get('Login Parameters', 'CLIENT_SECRET')
TOKEN_USER_NAME=parser.get('User', 'TOKEN_USER_NAME')
DEVICE_ID=parser.get('User', 'DEVICE_ID')

database_context = DatabaseConnection(DatabaseConfigurator('config.ini').Config())
database = database_context.connect()

client = AuthorizedFitbitClient(database)
authorized_client = client.get_authorized_client(user_name=TOKEN_USER_NAME, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
api_client = ApiClient(authorized_client, database, logging_enabled=True)

# Main
current_date = datetime.date.today()
yester_date = datetime.date.today() - datetime.timedelta(days=7)
dates_to_check = helperFunctions.get_dates(yester_date, current_date)

for check_date in dates_to_check:
  api_client.update_heart(check_date)
  api_client.update_steps(check_date)
  api_client.update_distance(check_date)
  api_client.update_sleep(check_date)

api_client.print_rate_limits()

# Teardown

del api_client
database_context.disconnect()

sys.exit()
os._exit(1)