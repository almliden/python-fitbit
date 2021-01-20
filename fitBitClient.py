import datetime
import time
import fitbit
from bson.json_util import dumps, loads

class AuthorizedFitbitClient:
  def __init__(self, database):
    self.database = database
    self.user_name = None

  def update_refresh_token(self, token:str):
    self.database.user_tokens.find_one_and_update(
      {'user': self.user_name},
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
  
  def get_authorized_client(self, user_name, client_id, client_secret):
    self.user_name = user_name
    token = self.database.user_tokens.find_one({'user': self.user_name})
    if (token != None and token['access_token'] != None and token['refresh_token'] and token['expires_at']):
      try:
        auth2_client=fitbit.Fitbit(client_id,client_secret,oauth2=True,access_token=token['access_token'],refresh_token=token['refresh_token'],expires_at=token['expires_at'],refresh_cb=self.update_refresh_token)
        return auth2_client
      except (TypeError) as e:
        print('Catched error: %s. \n This is probably related to the user not present in the db' % (e))
    else:
      raise Exception( ('User does not exist: %s' % self.user_name))

class ApiClient:
  def __init__(self, authorized_client: AuthorizedFitbitClient, database, logging_enabled=False):
    self.authorized_client = authorized_client
    self.database = database
    self.logging = logging_enabled

  # Help methods
  def is_saved(self, collection:str, search:dict, name:str, date:str):
    if len(self.retrieve(collection, search)) == 0:
      return False
    else:
      return True
      
  def is_not_saved(self, collection:str, search:dict, name:str, date:str):
    return not self.is_saved(collection=collection, search=search, name=name, date=date)

  def save(self, time_series, check:str, collection:str):
    if (len(time_series[check]) > 0):
      self.database[collection].insert_one(time_series)

  def update(self, collection:str, find:dict, update):
    self.database[collection].find_one_and_update(find, update)

  def retrieve(self, collection:str, search:dict):
    return list(self.database[collection].find({ search['KEY'] : search['VALUE'] }))

  def retrieve_one(self, collection:str, search:dict):
    return self.database[collection].find_one({ search['KEY'] : search['VALUE'] })

  # Data-related
  def devices(self):
    devices = { 'devices': self.authorized_client.get_devices() }
    updated = self.database.devices.find_one_and_update({ 'devices.id': devices['devices'][0]['id'] }, { '$set':  devices })
    if (updated == None):
      self.database.devices.insert_one(devices)
    updated_record = { 'key': 'devicesRequest', 'lastDeviceRequest': datetime.datetime.now() }
    if ( self.database.requests.find_one_and_update({ 'key': 'devicesRequest'}, { '$set': updated_record }) == None):
      self.database.requests.insert_one(updated_record)

  def last_synced(self, deviceId:str):
    result = self.database.devices.find_one({'devices.id': deviceId }, { 'devices.batteryLevel': 1, 'devices.lastSyncTime': 1 } )
    if (result != None):
      return result['devices'][0]
    return {}

  def save_sleep(self, date:str):
    name = 'sleep'
    date_formatted = datetime.date.fromisoformat(date)
    if (self.is_not_saved(collection=name, search={ 'KEY': 'sleep.dateOfSleep', 'VALUE': date }, name=name, date=date)):
      time_series = self.authorized_client.get_sleep(date_formatted)
      self.save(time_series=time_series, check=name, collection=name)
    elif (self.logging): print('Already saved %s %s' % (name, date))

  def update_sleep(self, date:str):
    name = 'sleep'
    date_formatted = datetime.date.fromisoformat(date)
    time_series_api = self.authorized_client.get_sleep(date_formatted)
    time_series_db = self.retrieve_one(collection=name, search = { 'KEY': 'sleep.dateOfSleep', 'VALUE': date_formatted.isoformat() }) #self.database[name].find_one({ 'sleep.dateOfSleep': date.isoformat() })  #
    if (time_series_api != None and time_series_db != None):
      if (len(time_series_api['sleep']) > len(time_series_db['sleep'])):
        if (self.logging): print('Should update sleep')
        self.update(collection=name, find={'sleep.dateOfSleep': date.isoformat()}, update={'$set':  time_series_api} )
      elif (self.logging): print('Already saved latest sleep %s' % date)

  def save_heart(self, date:str):
    self.fetch_and_save_intraday(date, collection='heart', search={ 'KEY': 'activities-heart.dateTime', 'VALUE': date }, endpoint = 'activities/heart', detail_level='1sec', check='activities-heart')

  def save_steps(self, date:str):
    self.fetch_and_save_intraday(date, collection='steps', search={ 'KEY': 'activities-steps.dateTime', 'VALUE': date }, endpoint = 'activities/steps', detail_level='1min', check='activities-steps')

  def save_distance(self, date:str):
    self.fetch_and_save_intraday(date, collection='distance', search={ 'KEY': 'activities-distance.dateTime', 'VALUE': date }, endpoint = 'activities/distance', detail_level='1min', check='activities-distance')

  def save_elevation(self, date:str):
    self.fetch_and_save_intraday(date, collection='elevation', search={ 'KEY': 'activities-elevation.dateTime', 'VALUE': date }, endpoint = 'activities/tracker/elevation', detail_level='1min', check='activities-elevation')

  def save_test_data(self, date):
    self.fetch_and_save_intraday(date, collection='testCollection', search={ 'KEY': 'the spanish inquisition', 'VALUE': 'noby expects' }, endpoint = 'activities/calories', detail_level='15min', check='activities-calories')

  def update_heart(self, date:str):
    self.fetch_and_update_intraday(date, collection='heart', search={ 'KEY': 'activities-heart.dateTime', 'VALUE': date }, endpoint = 'activities/heart', detail_level='1sec', check='activities-heart')
  
  def update_steps(self, date:str):
    self.fetch_and_update_intraday(date, collection='steps', search={ 'KEY': 'activities-steps.dateTime', 'VALUE': date }, endpoint = 'activities/steps', detail_level='1min', check='activities-steps')
 
  def update_distance(self, date:str):
    self.fetch_and_update_intraday(date, collection='distance', search={ 'KEY': 'activities-distance.dateTime', 'VALUE': date }, endpoint = 'activities/distance', detail_level='1min', check='activities-distance')

  def fetch_and_update_intraday(self, date:str, collection:str, search:dict, endpoint:str, detail_level:str, check:str):
    time_series_api = self.authorized_client.intraday_time_series(endpoint, base_date=date, detail_level=detail_level)
    time_series_saved = self.retrieve_one(collection, search)
    if (time_series_saved != None):
      if (len(time_series_api['activities-{collection}-intraday'.format(collection=collection)]['dataset']) > len(time_series_saved['activities-{collection}-intraday'.format(collection=collection)]['dataset'])):
        updated = self.database[collection].find_one_and_update({ 'activities-{collection}.dateTime'.format(collection=collection): date }, { '$set': time_series_api })
        if (self.logging): print('Updated %s' % (collection, len(time_series_api['activities-{collection}-intraday'.format(collection=collection)]['dataset']), len(time_series_saved['activities-{collection}-intraday'.format(collection=collection)]['dataset'])))
        if (self.logging): print(updated['activities-heart'])
      elif (self.logging): print('Already saved latest %s %s' % (collection, date))
    elif (self.logging):
      print('Save new data %s %s' % (collection, date))
      self.save(time_series=time_series_api, check=check, collection=collection)

  def fetch_and_save_intraday(self, date:str, collection:str, search:dict, endpoint:str, detail_level:str, check:str):
    if (self.is_not_saved(collection, search, name=collection, date=date)):
      if (self.logging): print('Get and save %s %s' % (collection, date))
      time_series = self.authorized_client.intraday_time_series(endpoint, base_date=date, detail_level=detail_level)
      self.save(time_series=time_series, check=check, collection=collection)
    elif (self.logging): print('Already saved %s %s' % (collection, date))

  def handle_rate_limits(self):
    if (self.authorized_client.get_rate_limits() != {}):
      try:
        fitbit_rate_limit_limit = self.authorized_client.get_rate_limits()['fitbitRateLimitLimit']
        fitbit_rate_limit_remaining = self.authorized_client.get_rate_limits()['fitbitRateLimitRemaining']
        fitbit_rate_limit_reset = self.authorized_client.get_rate_limits()['fitbitRateLimitReset']
        record = { 'key': 'ratelimit', 'fitbitRateLimitLimit': fitbit_rate_limit_limit, 'fitbitRateLimitRemaining': fitbit_rate_limit_remaining, 'fitbitRateLimitReset': fitbit_rate_limit_reset, 'updated': datetime.datetime.now() }
        last_request = self.database.requests.find_one({ 'key': 'ratelimit' })
        if (last_request == None):
          self.database.requests.insert_one(record)
          return
        last_updated = last_request['updated']
        resets_at = last_updated + datetime.timedelta(seconds=int(last_request['fitbitRateLimitReset']))
        if (datetime.datetime.now() >= resets_at):
          self.database.requests.find_one_and_update({ 'key': 'ratelimit' }, { '$set':  record })
        elif (int(last_request['fitbitRateLimitRemaining']) > int(fitbit_rate_limit_remaining)):
          self.database.requests.find_one_and_update({ 'key': 'ratelimit' }, { '$set':  record })
      except (Exception):
        print('Error in rate limit handling')
        pass

  def print_rate_limits(self):
    self.handle_rate_limits()
    fitbit_rate_limit = self.database.requests.find_one({ 'key': 'ratelimit' })
    last_updated = fitbit_rate_limit['updated']
    resets_at = last_updated + datetime.timedelta(seconds=int(fitbit_rate_limit['fitbitRateLimitReset']))
    print('FitBit API: %s requests remains of %s. Resets at %s. (Last request made: %s)'  % (fitbit_rate_limit['fitbitRateLimitRemaining'], fitbit_rate_limit['fitbitRateLimitLimit'], resets_at, last_updated))

  def __del__(self):
    if (self.database != None):
      self.handle_rate_limits()
    del self.database
