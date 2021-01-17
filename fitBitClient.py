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
  def __init__(self, authorized_client: AuthorizedFitbitClient, database):
    self.authorized_client = authorized_client
    self.database = database

  def get_sleep_for_date(self, date):
    def check_existing(): return self.check_if_alreadySaved('sleep', { 'KEY': 'sleep.dateOfSleep', 'VALUE': date.isoformat() } )
    def get_from_api():
      timeSeries = self.authorized_client.get_sleep(date)
      self.save_to_database(time_series=timeSeries, check='sleep', collection='sleep')
    self.perform_request(check_existing, get_from_api, 'sleep', date.isoformat())

  def get_devices(self):
    all_devices = self.authorized_client.get_devices()
    devices = { 'devices': all_devices}
    device_id = devices['devices'][0]['id']
    updated = self.database.devices.find_one_and_update({ 'devices.id': device_id }, { '$set':  devices })
    if (updated == None):
      self.database.devices.insert_one(devices)
    updated_record = { 'key': 'devicesRequest', 'lastDeviceRequest': datetime.datetime.now() }
    updated_requests = self.database.requests.find_one_and_update({ 'key': 'devicesRequest'}, { '$set': updated_record })
    if (updated_requests == None):
      self.database.requests.insert_one(updated_record)

  def get_heart_for_date(self, date):
    self.request_wrapper(date, collection='heart', search={ 'KEY': 'activities-heart.dateTime', 'VALUE': date }, endpoint = 'activities/heart', detail_level='1sec', check='activities-heart')

  def get_steps_for_date(self, date):
    self.request_wrapper(date, collection='steps', search={ 'KEY': 'activities-steps.dateTime', 'VALUE': date }, endpoint = 'activities/steps', detail_level='1min', check='activities-steps')

  def get_distance_for_date(self, date):
    self.request_wrapper(date, collection='distance', search={ 'KEY': 'activities-distance.dateTime', 'VALUE': date }, endpoint = 'activities/distance', detail_level='1min', check='activities-distance')

  def get_elevation_for_date(self, date):
    self.request_wrapper(date, collection='elevation', search={ 'KEY': 'activities-elevation.dateTime', 'VALUE': date }, endpoint = 'activities/tracker/elevation', detail_level='1min', check='activities-elevation')

  def get_test_data_only_for_request(self, date):
    self.request_wrapper(date, collection='testCollection', search={ 'KEY': 'spanish inquisition', 'VALUE': 'noby expects' }, endpoint = 'activities/calories', detail_level='15min', check='activities-calories')

  def request_wrapper(self, date, collection, search, endpoint, detail_level, check):
    def check_existing(): return self.check_if_alreadySaved(collection, search )
    def get_from_api(): return self.get_intra_day_time_series(endpoint = endpoint, date = date, detail_level=detail_level, check=check, collection=collection)
    self.perform_request(check_existing, get_from_api, collection, date)
  
  def save_to_database(self, time_series, check, collection):
    if (len(time_series[check]) > 0):
      self.database[collection].insert_one(time_series)
      print('Added to collection: %s' % collection)
    else:
      print('Nothing to add to collection: %s' % collection)

  def get_intra_day_time_series(self, endpoint, date, detail_level, check, collection):
    time_series = self.authorized_client.intraday_time_series(endpoint, base_date=date, detail_level=detail_level)
    self.save_to_database(time_series=time_series, check=check, collection=collection)

  def handle_rate_limits(self):
    try:
      fitbit_rate_imit_limit = self.authorized_client.get_rate_limits()['fitbitRateLimitLimit']
      fitbit_rate_limit_remaining = self.authorized_client.get_rate_limits()['fitbitRateLimitRemaining']
      fitbit_rate_limit_reset = self.authorized_client.get_rate_limits()['fitbitRateLimitReset']
      record = { 'key': 'ratelimit', 'fitbitRateLimitLimit': fitbit_rate_imit_limit, 'fitbitRateLimitRemaining': fitbit_rate_limit_remaining, 'fitbitRateLimitReset': fitbit_rate_limit_reset, 'updated': datetime.datetime.now() }
      updated = self.database.requests.find_one_and_update({ 'key': 'ratelimit' }, { '$set':  record })
      if (updated == None):
        self.database.requests.insert_one(record)
    except (KeyError):
      pass

  def print_rate_limits(self):
    fitbit_rate_limit = self.database.requests.find_one({ 'key': 'ratelimit' })
    last_updated = fitbit_rate_limit['updated']
    resets_at = last_updated + datetime.timedelta(seconds=int(fitbit_rate_limit['fitbitRateLimitReset']))
    print('FitBit API: %s requests remains of %s. Resets at %s. (Last request made: %s)'  % (fitbit_rate_limit['fitbitRateLimitRemaining'], fitbit_rate_limit['fitbitRateLimitLimit'], resets_at, last_updated))

  def check_if_alreadySaved(self, collection, search): return list(self.database[collection].find({ search['KEY'] : search['VALUE'] }))

  def perform_request(self, check_existing, get_from_api, name, date):
    result = check_existing()
    if len(result) == 0:
      try:
        print('Fetching: %s %s' % (name, date))
        get_from_api()
      except (Exception):
        print ('Error fetching')
    else:
      print('Already stored: %s %s' % (name, date))

  def get_last_synced(self, deviceId):
    result = self.database.devices.find_one({'devices.id': deviceId }, { 'devices.batteryLevel': 1, 'devices.lastSyncTime': 1 } )
    if (result != None):
      return result['devices'][0]
    return {}

  def __del__(self):
    self.authorized_client = None
    self.database = None
