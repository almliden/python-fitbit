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
    {'user': TOKEN_USER_NAME},
    { '$set': { 
      'access_token': token['access_token'],
      'expires_at': token['expires_at'],
      'expires_in': token['expires_in'],
      'refresh_token': token['refresh_token'],
      'scope': token['scope'],
      'token_type': token['token_type'],
      'user_id': token['user_id']
      } 
    }
  )

token = db.user_tokens.find_one({'user': TOKEN_USER_NAME})
if (token != None and token['access_token'] != None and token['refresh_token'] and token['expires_at']):
  try:
    auth2_client=fitbit.Fitbit(CLIENT_ID,CLIENT_SECRET,oauth2=True,access_token=token['access_token'],refresh_token=token['refresh_token'],expires_at=token['expires_at'],refresh_cb=UpdateRefreshToken)
  except (TypeError) as e:
    print('Catched error: %s. \n This is probably related to the user not present in the db' % (e))
else:
  raise Exception( ('User does not exist: %s' % TOKEN_USER_NAME))

def getSleepForDate(date, fitbitClient, database):
  def checkExisting(): return checkIfAlreadySaved(database, 'sleep', { 'KEY': 'sleep.dateOfSleep', 'VALUE': date.isoformat() } )
  def getFromApi():
    timeSeries = fitbitClient.get_sleep(date)
    saveToDatabase(timeSeries=timeSeries, check='sleep', database=database, collection='sleep')
  performRequest(checkExisting, getFromApi, 'sleep', date.isoformat())

def getHeartForDate(date, fitbitClient, database):
  requestWrapper(date, fitbitClient, database, collection='heart', search={ 'KEY': 'activities-heart.dateTime', 'VALUE': date }, endpoint = 'activities/heart', detail_level='1sec', check='activities-heart')

def getStepsForDate(date, fitbitClient, database):
  requestWrapper(date, fitbitClient, database, collection='steps', search={ 'KEY': 'activities-steps.dateTime', 'VALUE': date }, endpoint = 'activities/steps', detail_level='1min', check='activities-steps')

def getDistanceForDate(date, fitbitClient, database):
  requestWrapper(date, fitbitClient, database, collection='distance', search={ 'KEY': 'activities-distance.dateTime', 'VALUE': date }, endpoint = 'activities/distance', detail_level='1min', check='activities-distance')

def getElevationForDate(date, fitbitClient, database):
  requestWrapper(date, fitbitClient, database, collection='elevation', search={ 'KEY': 'activities-elevation.dateTime', 'VALUE': date }, endpoint = 'activities/tracker/elevation', detail_level='1min', check='activities-elevation')

def requestWrapper(date, fitbitClient, database, collection, search, endpoint, detail_level, check):
  def checkExisting(): return checkIfAlreadySaved(database, collection, search )
  def getFromApi(): return getIntraDayTimeSeries(fitbitClient, database, endpoint = endpoint, date = date, detail_level=detail_level, check=check, collection=collection)
  performRequest(checkExisting, getFromApi, collection, date)

def saveToDatabase(timeSeries, check, database, collection):
  if (len(timeSeries[check]) > 0):
    database[collection].insert_one(timeSeries)
    print('Added to collection: %s' % collection)
  else:
    print('Nothing to add to collection: %s' % collection)

def getIntraDayTimeSeries(fitbitClient, database, endpoint, date, detail_level, check, collection):
  timeSeries = fitbitClient.intraday_time_series(endpoint, base_date=date, detail_level=detail_level)
  handleRateLimits(fitbitClient)
  saveToDatabase(timeSeries=timeSeries, check=check, database=database, collection=collection)

def handleRateLimits(fitbitClient):
  fitbitRateLimitLimit = fitbitClient.get_rate_limits()['fitbitRateLimitLimit']
  fitbitRateLimitRemaining = fitbitClient.get_rate_limits()['fitbitRateLimitRemaining']
  fitbitRateLimitReset = fitbitClient.get_rate_limits()['fitbitRateLimitReset']
  record = { 'key': 'ratelimit', 'fitbitRateLimitLimit': fitbitRateLimitLimit, 'fitbitRateLimitRemaining': fitbitRateLimitRemaining, 'fitbitRateLimitReset': fitbitRateLimitReset, 'updated': datetime.datetime.now() }
  updated = db.requests.find_one_and_replace({ 'key': 'ratelimit' }, record)
  if (updated == None):
    db.requests.insert_one(record)

def printRateLimits():
  fitbitRateLimit = db.requests.find_one({ 'key': 'ratelimit' })
  minutes = int(fitbitRateLimit['fitbitRateLimitReset'])/60
  seconds = 60 - (minutes % 60)
  print('FitBit API: %s requests remains of %s. Resets in %s seconds (%d minutes %d seconds).' % (fitbitRateLimit['fitbitRateLimitRemaining'], fitbitRateLimit['fitbitRateLimitLimit'], fitbitRateLimit['fitbitRateLimitReset'], minutes, seconds))

def checkIfAlreadySaved(database, collection, search): return list(database[collection].find({ search['KEY'] : search['VALUE'] }))

def performRequest(checkExisting, getFromApi, name, date):
  result = checkExisting()
  if len(result) == 0:
    try:
      print('Fetching: %s %s' % (name, date))
      getFromApi()
    except (Exception) as e:
      print (e)
  else:
    print('Already stored: %s %s' % (name, date))

currentDate = datetime.date.today() ## + datetime.timedelta(days=1) #datetime.date(2021, 1, 5)
yesterDate = datetime.date.today() - datetime.timedelta(days=1)

getSleepForDate(currentDate, auth2_client, db)
getHeartForDate(yesterDate.isoformat(), auth2_client, db)
getStepsForDate(yesterDate.isoformat(), auth2_client, db)
getDistanceForDate(yesterDate.isoformat(), auth2_client, db)

printRateLimits()

def getDates(startDate, endDate):
  start = datetime.datetime.fromisoformat(startDate)
  end = datetime.datetime.fromisoformat(endDate)
  timedelta = end - start
  days = int(timedelta.total_seconds()/3600/24)+1
  date_list = [datetime.datetime.isoformat(end - datetime.timedelta(days=x))[0:10] for x in reversed(range(days)) ]
  return date_list

## Move out to some helper or utility class to sync historic data
# dates = getDates('2021-01-01', '2021-01-04')
# for date in dates:
#   dateToGet = datetime.date.fromisoformat(date)
#   getStepsForDate(dateToGet, auth2_client, db)

dbcontext.disconnect()

sys.exit()
os._exit(1)