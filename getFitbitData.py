import configparser
import datetime
import sys
import os
import fitbit
from databaseConnection import DatabaseConnection, DatabaseConfigurator

parser=configparser.ConfigParser()
parser.read('config.ini')

databaseConfig = DatabaseConfigurator('config.ini')
dbcontext = DatabaseConnection(databaseConfig.Config())
db = dbcontext.connect()

CLIENT_ID=parser.get('Login Parameters', 'CLIENT_ID')
CLIENT_SECRET=parser.get('Login Parameters', 'CLIENT_SECRET')
TOKEN_USER_NAME=parser.get('User', 'TOKEN_USER_NAME')

def UpdateRefreshToken(token):
  db.user_tokens.find_one_and_update(
    {"user": TOKEN_USER_NAME},
    { "$set": { 
      "access_token": token['access_token'],
      "expires_at": token['expires_at'],
      "expires_in": token['expires_in'],
      "refresh_token": token['refresh_token'],
      "scope": token['scope'],
      "token_type": token['token_type'],
      "user_id": token['user_id']
      } 
    }
  )

token = db.user_tokens.find_one({"user": TOKEN_USER_NAME})
try:
  auth2_client=fitbit.Fitbit(CLIENT_ID,CLIENT_SECRET,oauth2=True,access_token=token['access_token'],refresh_token=token['refresh_token'],expires_at=token['expires_at'],refresh_cb=UpdateRefreshToken)
except (TypeError) as e:
  print("Catched error: %s" % (e))

def getSleepForDate(currentDate, fitbitClient, database):
  date = currentDate.isoformat()
  def checkIfAlreadySaved():
    dateadded_sleep = database.sleep.find({"sleep.dateOfSleep": date})
    return list(dateadded_sleep)
  def getFromApi():
    oneDayData_sleep = fitbitClient.get_sleep(currentDate)
    if (len(oneDayData_sleep['sleep']) > 0):
      database.sleep.insert_one(oneDayData_sleep)
      print("Saved sleep data")
    else:
      print("No sleep data available")
  performRequest(checkIfAlreadySaved, getFromApi, "sleep", date)

def getHeartForDate(currentDate, fitbitClient, database):
  date = currentDate.isoformat()
  def checkIfAlreadySaved():
    dateadded_heart = database.heart.find({"activities-heart.dateTime": date})
    return list(dateadded_heart)
  def getFromApi():
    oneDayData_heart = fitbitClient.intraday_time_series('activities/heart', base_date=date, detail_level='1sec')
    if (len(oneDayData_heart['activities-heart']) > 0):
      database.test.insert_one(oneDayData_heart)
      print("Saved heart data")
    else:
      print("No heart data available")
  performRequest(checkIfAlreadySaved, getFromApi, "heart", date)

def performRequest(checkExisting, getFromApi, name, date):
  result = checkExisting()
  if len(result) == 0:
    try:
      print("Getting %s for date %s" % (name, date))
      getFromApi()
    except (Exception) as e:
      print (e)
  else:
    print("Already saved %s for date %s" % (name, date))

currentDate = datetime.date.today() ## + datetime.timedelta(days=1) #datetime.date(2021, 1, 5)
getSleepForDate(currentDate, auth2_client, db)

yesterDate = datetime.date.today() - datetime.timedelta(days=1)
getHeartForDate(yesterDate, auth2_client, db)

dbcontext.disconnect()

sys.exit()
os._exit(1)