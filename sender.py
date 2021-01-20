from emailAdapter import EmailAdapter, EmailAdapterConfig, EmailAdapterConfigurator
from datetime import date, datetime, timedelta
from databaseConnection import DatabaseConnection
import configparser
import random

class EmailSender:
  emailAdapter = None
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
    self.emailAdapter = EmailAdapter(config.Config())
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
      queuedAt = datetime.now().isoformat()
      sentEmails= self.database.emails.find_one({'date': today, 'category': 'daily' })
      if (sentEmails != None and bool(sentEmails['sent']) == True and not override_check):
        print('Already sent email: %s' % today)
        return
      if (sentEmails == None):
        self.createIntentToSend(queuedAt)
      lastSyncTimeResult = self.getLastSyncedFromDb(database, device_id)
      emailParts = {}
      yesterDate = date.today() - timedelta(days=1)
      emailParts['steps'] = self.addSteps(yesterDate)
      emailParts['restingHeartRate'] = self.addHeartRate(yesterDate)
      emailParts['distance'] = self.addDistance(yesterDate)
      emailParts['meditateNudge'] = self.addMeditate()
      emailParts['sleepStatsYesterDay'] = self.addYesterDaySleep(yesterDate)
      emailParts['batteryLevel'] = self.addBatteryLevel(lastSyncTimeResult['batteryLevel'], lastSyncTimeResult['lastSyncTime'][0:19])
      sentAt = datetime.now().isoformat()
      self.send(emailParts)
      self.confirmEmailSent(queuedAt, sentAt)
    except (Exception):
      print('Something went wrong in sending email.')
  
  def getLastSyncedFromDb(self, db, deviceId:str):
    result = db.devices.find_one({'devices.id': deviceId }, { 'devices.batteryLevel': 1, 'devices.lastSyncTime': 1 } )
    if (result != None):
      return result['devices'][0]
    return {}
    
  def createIntentToSend(self, queuedAt: str):
    try:
      self.database.emails.insert_one({ 'date': date.today().isoformat(), 'category': 'daily', 'queuedAt': queuedAt, 'sent': False })
    except (Exception):
      print('Exception in createIntentToSend')
  
  def confirmEmailSent(self, queuedAt:str, sentAt: str):
    try:
      self.database.emails.find_one_and_update({ 'queuedAt': queuedAt}, { '$set': { 'sent': True, 'sentAt': sentAt } })
    except (Exception):
      print('Exception in confirmEmailSent')

  def addBatteryLevel(self, batteryLevel:int, last_synced:str):
    try:
      selected_text = 'Your trackers battery level.'
      if (batteryLevel < 20):
        selected_text += ' Kindly try to find some time to charge your device during the day.'
      with open('{folderPath}/batteryLevel.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
        return fopen.read().format(section_text = selected_text, section_number = batteryLevel, last_synced = last_synced)
    except (Exception):
      print('Something went wrong in def addBatteryLevel')
      return ''

  def addHeartRate(self, search_date:date):
    try:
      yesterdate_heart = self.database.heart.find_one({'activities-heart.dateTime' : search_date.isoformat() })
      heartRate = yesterdate_heart['activities-heart'][0]['value']['restingHeartRate']
      if (heartRate != None):
        with open('{folderPath}/restingHeartRate.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = 'This was your resting heart rate.', section_number = heartRate)
    except (Exception):
      print('Something went wrong in def addHeartRate')
      return ''
  
  def addDistance(self, search_date:date):
    try:
      data = self.database.distance.find_one({'activities-distance.dateTime' : search_date.isoformat() })
      distance = data['activities-distance'][0]['value']
      if (distance != None):
        with open('{folderPath}/distance.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = 'This is your calculated distance.', section_number = round(float(distance), 3))
    except (Exception):
      print('Something went wrong in def addDistance')
      return ''

  def addSteps(self, search_date:date):
    try:
      data = self.database.steps.find_one({'activities-steps.dateTime' : search_date.isoformat() })
      steps = data['activities-steps'][0]['value']
      if (steps != None):
        keys = self.valuephrases_steps.keys()
        phraseKey = 0
        for k in keys:
          if int(steps) > k:
            phraseKey = k 
          elif k > phraseKey:
            break
        possiblePhrases = self.valuephrases_steps[phraseKey]
        phraseIndex = random.randrange(0, len(possiblePhrases))
        selectedPhrase = possiblePhrases[phraseIndex]
        with open('{folderPath}/totalSteps.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
          return fopen.read().format(section_text = 'You took this many steps. %s The recommended number of steps per day is 10 000, but we settle for 8000 to keep our goals reasonable.' % selectedPhrase, section_number = steps)
    except (Exception) as e:
      print(e)
      print('Something went wrong in def addSteps')
      return ''

  def addMeditate(self):
    try:
      with open('{folderPath}/meditate.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
        return fopen.read().format(section_text='Meditation sets the mood for the day. Do you have time to spare?', button_location='headspace://home', button_text='Take me there!')
    except (Exception):
      print('Something went wrong in def addMeditate')
      return ''
  
  def addYesterDaySleep(self,  search_date:date):
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
      print('Something went wrong in def addYesterDaySleep')
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

      self.emailAdapter.sendEmail(
        sender=self.sender,
        receiver=self.receiver,
        subject='Health Update ' + date.today().isoformat(),
        message=message,
        content_type={ 'MIME-Version': '1.0' },
        sender_name='Health Service')
