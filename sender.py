from emailAdapter import EmailAdapter, EmailAdapterConfig, EmailAdapterConfigurator
from datetime import date, datetime, timedelta
from databaseConnection import DatabaseConnection
import configparser
import random
import helper_functions

class EmailSender:
  email_adapter = None
  database = None
  valuephrases_steps = {
    0 : ['Did you wear your fitbit?', 'I believe you can do better than this.', 'Hope you are well!'],
    2000 : ['You should definitely try to get some steps today!'],
    6000: ['Seems like you took a stroll!', 'Perhaps you can squeeze in some workout today?'],
    8000: ['Good! You reached your goals!'],
    9000: ['Over 9000!'],
    10000: ['Congratulations!', '10k is not bad!'],
    15000: ['Magnificent ya filthy health-freak!', 'That\'s really good!', 'Keep it up maestro!', 'Impressive!']
  }

  def __init__(self):
    config = EmailAdapterConfigurator()
    self.email_adapter = EmailAdapter(config.Config())
    parser=configparser.ConfigParser()
    parser.read('config.ini')
    self.sender=parser.get('Email Daily Health Report', 'EMAIL_DAILY_HEALTH_REPORT_SENDER')
    self.receiver=parser.get('Email Daily Health Report', 'EMAIL_DAILY_HEALTH_REPORT_RECEIVER')
    self.buttonHref=parser.get('Email Daily Health Report', 'EMAIL_DAILY_HEALTH_REPORT_LINK')
    self.template_file_name=parser.get('Email Daily Health Report', 'EMAIL_DAILY_HEALTH_REPORT_TEMPLATE')
    self.template_folder=parser.get('Email Daily Health Report', 'EMAIL_DAILY_HEALTH_REPORT_TEMPLATE_FOLDER')

  def analyse(self, database: DatabaseConnection, override_check:bool, device_id:str):
    try:
      self.database = database
      today = date.today().isoformat()
      queued_at = datetime.now().isoformat()
      sent_emails = self.database.emails.find_one({'date': today, 'category': 'daily' })
      if (sent_emails != None and bool(sent_emails['sent']) == True and not override_check):
        print('Already sent email: %s' % today)
        return
      if (sent_emails == None):
        self.create_intent_to_send(queued_at)
      last_sync_time = self.get_last_synced(database, device_id)
      email_parts = {}
      yesterdate = date.today() - timedelta(days=1)
      email_parts['steps'] = self.add_steps(yesterdate)
      email_parts['mostActiveHour'] = self.add_most_active_hour(yesterdate)
      email_parts['restingHeartRate'] = self.add_heartrate(yesterdate)
      email_parts['tip_of_the_day'] = self.add_tip_of_the_day()
      email_parts['distance'] = self.add_distance(yesterdate)
      email_parts['meditateNudge'] = self.add_meditate()
      email_parts['sleepStatsYesterDay'] = self.add_yesterday_sleep(yesterdate)
      email_parts['batteryLevel'] = self.add_battery_level(last_sync_time['batteryLevel'], last_sync_time['lastSyncTime'][0:19])
      sent_at = datetime.now().isoformat()
      self.send(email_parts)
      self.confirm_email_sent(queued_at, sent_at)
    except (Exception):
      print('Something went wrong in sending email.')
  
  def get_last_synced(self, db, device_id:str):
    result = db.devices.find_one({'devices.id': device_id }, { 'devices.batteryLevel': 1, 'devices.lastSyncTime': 1 } )
    if (result != None):
      return result['devices'][0]
    return {}
    
  def create_intent_to_send(self, queued_at: str):
    try:
      self.database.emails.insert_one({ 'date': date.today().isoformat(), 'category': 'daily', 'queuedAt': queued_at, 'sent': False })
    except (Exception):
      print('Exception in create_intent_to_send')
  
  def confirm_email_sent(self, queued_at:str, sentAt: str):
    try:
      self.database.emails.find_one_and_update({ 'queuedAt': queued_at}, { '$set': { 'sent': True, 'sentAt': sentAt } })
    except (Exception):
      print('Exception in confirm_email_sent')

  def add_battery_level(self, battery_level:int, last_synced:str):
    try:
      selected_text = 'Your trackers battery level.'
      if (battery_level < 20):
        selected_text += ' Kindly try to find some time to charge your device during the day.'
      with open('{folderPath}/batteryLevel.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
        return fopen.read().format(section_text = selected_text, section_number = battery_level, last_synced = last_synced)
    except (Exception):
      print('Something went wrong in def add_battery_level')
      return ''

  def add_tip_of_the_day(self):
    try:
      skip_random = random.randrange(0, self.database.advice.count())
      result = self.database.advice.find({}).limit(1).skip(skip_random)
      if (result != None and result[0]['title'] != None and result[0]['body'] != None):
        section_text = result[0]['body']
        section_header = result[0]['title']
        with open('{folderPath}/tipOfTheDay.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = section_text, section_header = section_header)
    except (Exception) as e:
      print(e)
      print('Something went wrong in def add_tip_of_the_day')
      return ''

  def add_most_active_hour(self, search_date:date):
    try:
      yesterdate_active = self.database.steps.find_one({'activities-steps.dateTime' : search_date.isoformat() })
      time_series = yesterdate_active['activities-steps-intraday']['dataset']
      if (time_series != None):
        top = helper_functions.find_max_top(time_series, 'time', 1)[0]
        with open('{folderPath}/mostActiveHour.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = 'Your most active minute was {t}'.format(t = top['time']), section_number = top['value'])
    except (Exception):
      print('Something went wrong in def add_most_active_hour')
      return ''

  def add_heartrate(self, search_date:date):
    try:
      yesterdate_heart = self.database.heart.find_one({'activities-heart.dateTime' : search_date.isoformat() })
      heartrate = yesterdate_heart['activities-heart'][0]['value']['restingHeartRate']
      if (heartrate != None):
        with open('{folderPath}/restingHeartRate.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = 'This was your resting heart rate.', section_number = heartrate)
    except (Exception):
      print('Something went wrong in def add_heartrate')
      return ''
  
  def add_distance(self, search_date:date):
    try:
      data = self.database.distance.find_one({'activities-distance.dateTime' : search_date.isoformat() })
      distance = data['activities-distance'][0]['value']
      if (distance != None):
        with open('{folderPath}/distance.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = 'This is your calculated distance.', section_number = round(float(distance), 3))
    except (Exception):
      print('Something went wrong in def add_distance')
      return ''

  def add_steps(self, search_date:date):
    try:
      data = self.database.steps.find_one({'activities-steps.dateTime' : search_date.isoformat() })
      steps = data['activities-steps'][0]['value']
      if (steps != None):
        keys = self.valuephrases_steps.keys()
        phrase_key = 0
        for k in keys:
          if int(steps) > k:
            phrase_key = k 
          elif k > phrase_key:
            break
        possible_phrases = self.valuephrases_steps[phrase_key]
        phrase_index = random.randrange(0, len(possible_phrases))
        selected_phrase = possible_phrases[phrase_index]
        with open('{folderPath}/totalSteps.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = 'You took this many steps. %s The recommended number of steps per day is 10 000, but we settle for 8000 to keep our goals reasonable.' % selected_phrase, section_number = steps)
    except (Exception) as e:
      print(e)
      print('Something went wrong in def add_steps')
      return ''

  def add_meditate(self):
    try:
      with open('{folderPath}/meditate.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
        return fopen.read().format(section_text='Meditation sets the mood for the day. Do you have time to spare?', button_location='headspace://home', button_text='Take me there!')
    except (Exception):
      print('Something went wrong in def add_meditate')
      return ''
  
  def add_yesterday_sleep(self,  search_date:date):
    try:
      data = self.database.sleep.find_one({'sleep.dateOfSleep' : search_date.isoformat() })
      sleep_time_asleep_raw = data['sleep'][0]['startTime']
      sleep_time_asleep = sleep_time_asleep_raw[11:][0:5]
      sleep_duration_total = int(data['sleep'][0]['minutesAsleep'])
      sleep_duration_hours = round(sleep_duration_total / 60, 0)
      sleep_duration_minutes = sleep_duration_total % 60
      sleep_duration = '{hours} hours and {minutes} minutes'.format(hours = sleep_duration_hours, minutes = sleep_duration_minutes)
      if (sleep_time_asleep != None and sleep_duration != None):
        with open('{folderPath}/sleep.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(sleep_time_asleep = sleep_time_asleep, sleep_duration = sleep_duration)
    except (Exception):
      print('Something went wrong in def add_yesterday_sleep')
      return ''

  def send(self, sections: dict):
    sections_content = ''

    for key, value in sections.items():
      if (value != ''):
        sections_content += value
      else:
        print('Tried to create content for {key}, but there was none.'.format(key=key))   

    with open(self.template_file_name, 'r', -1) as fopen:
      message = fopen.read().format(
        date=date.today().isoformat(),
        title='Daily report',
        sections=sections_content,
        button_text='View more stats!',
        button_location=self.buttonHref)

      self.email_adapter.sendEmail(
        sender=self.sender,
        receiver=self.receiver,
        subject='Health Update ' + date.today().isoformat(),
        message=message,
        content_type={ 'MIME-Version': '1.0' },
        sender_name='Health Service')
