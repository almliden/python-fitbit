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

# Initialize
database_context = DatabaseConnection(DatabaseConfigurator('config.ini').Config())
database = database_context.connect()

parser=configparser.ConfigParser()
parser.read('config.ini')

CLIENT_ID=parser.get('Login Parameters', 'CLIENT_ID')
CLIENT_SECRET=parser.get('Login Parameters', 'CLIENT_SECRET')
TOKEN_USER_NAME=parser.get('User', 'TOKEN_USER_NAME')
DEVICE_ID=parser.get('User', 'DEVICE_ID')

client = AuthorizedFitbitClient(database)
authorized_client = client.get_authorized_client(user_name=TOKEN_USER_NAME, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
api_client = ApiClient(authorized_client, database)

def send_email_update(database, device_id, override_check = False):
  sender = EmailSender()
  sender.analyse(database, override_check, device_id)

# Main
api_client.get_devices()
last_sync_time_result = api_client.get_last_synced(DEVICE_ID)
current_date = datetime.date.today()
yester_date = datetime.date.today() - datetime.timedelta(days=1)

api_client.get_sleep_for_date(current_date)

if (last_sync_time_result != None and datetime.date.fromisoformat(last_sync_time_result['lastSyncTime'][0:10]) > yester_date ):
  api_client.get_heart_for_date(yester_date.isoformat())
  api_client.get_steps_for_date(yester_date.isoformat())
  api_client.get_distance_for_date(yester_date.isoformat())
  send_email_update(database, device_id=DEVICE_ID, override_check = False)

api_client.handle_rate_limits()
api_client.print_rate_limits()

# Debug
# apiClient.getTestDataOnlyForRequest(yesterDate.isoformat(), auth2_client, db)
# sendEmailUpdate(db, override_check = True)

# Teardown
database_context.disconnect()

sys.exit()
os._exit(1)