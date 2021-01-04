from sshtunnel import SSHTunnelForwarder
import pymongo
import pprint
import configparser
import datetime
import sys
import os
import gather_keys_oauth2 as Oauth2
import fitbit
import json
from bson import BSON
from bson import json_util
from bson.json_util import dumps, loads
from types import SimpleNamespace
from databaseConnection import DatabaseConnection, DatabaseConfigurator

parser=configparser.ConfigParser()
parser.read('config.ini')

databaseConfig = DatabaseConfigurator('config.ini')
dbcontext = DatabaseConnection(databaseConfig.Config())
db = dbcontext.connect()

CLIENT_ID=parser.get('Login Parameters', 'CLIENT_ID')
CLIENT_SECRET=parser.get('Login Parameters', 'CLIENT_SECRET')
TOKEN_USER_NAME=parser.get('User', 'TOKEN_USER_NAME')

currentDate = datetime.date.today() #datetime.date(2021, 1, 5) ## date of today instead?
yesterDate = datetime.date.today() - datetime.timedelta(days=1)

def UpdateRefreshToken(TOKEN_DICT):
  print("Updating Tokens from Callback UpdateRefreshToken")
  updated = db.user_tokens.find_one_and_update(
    {"user": TOKEN_USER_NAME},
    { "$set": { 
      "ACCESS_TOKEN": TOKEN_DICT['access_token'],
      "REFRESH_TOKEN": TOKEN_DICT['refresh_token'],
      "EXPIRES_AT": TOKEN_DICT['expires_at'],
      "SCOPE": TOKEN_DICT['scope'],
      "TOKEN_TYPE": TOKEN_DICT['token_type'],
      "USER_ID": TOKEN_DICT['user_id'],
      "EXPIRES_IN": TOKEN_DICT['expires_in']
      } 
    }
  )

token = db.user_tokens.find_one({"user": TOKEN_USER_NAME})
try:
  auth2_client=fitbit.Fitbit(CLIENT_ID,CLIENT_SECRET,oauth2=True,access_token=token['ACCESS_TOKEN'],refresh_token=token['REFRESH_TOKEN'],expires_at=token['EXPIRES_AT'],refresh_cb=UpdateRefreshToken)
except (TypeError) as e:
  print("Catched error: %s" % (e))

def getSleepForDate(currentDate, fitbitClient, database):
  date = currentDate.isoformat()
  def checkFn():
    dateadded_sleep = database.sleep.find({"sleep.dateOfSleep": date})
    return list(dateadded_sleep)
  def goGet():
    oneDayData_sleep = fitbitClient.get_sleep(currentDate)
    if (len(oneDayData_sleep['sleep']) > 0):
      database.sleep.insert_one(oneDayData_sleep)
      print("Saved sleep data")
    else:
      print("No sleep data available")
  performRequest(checkFn, goGet, "sleep", date, fitbitClient)

def getHeartForDate(currentDate, fitbitClient, database):
  date = currentDate.isoformat()
  def checkFn():
    dateadded_heart = database.heart.find({"activities-heart.dateTime": date})
    return list(dateadded_heart)
  def goGet():
    oneDayData_heart = fitbitClient.intraday_time_series('activities/heart', base_date=date, detail_level='1sec')
    if (len(oneDayData_heart['activities-heart']) > 0):
      database.heart.insert_one(oneDayData_heart)
      print("Saved heart data")
    else:
      print("No heart data available")
  performRequest(checkFn, goGet, "heart", date, fitbitClient)

def performRequest(checkFn, requestFn, name, date, fitbitClient):
  result = checkFn()
  if len(result) == 0:
    try:
      print("Getting %s for date %s" % (name, date))
      requestFn()
    except (Exception) as e:
      print (e)
  else:
    print("Already saved %s for date %s" % (name, date))

getSleepForDate(currentDate, auth2_client, db)
getHeartForDate(yesterDate, auth2_client, db)

dbcontext.disconnect()

sys.exit()
os._exit(1)