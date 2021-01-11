from emailAdapter import EmailAdapter, EmailAdapterConfig, EmailAdapterConfigurator
from datetime import date, datetime, timedelta
from databaseConnection import DatabaseConnection
import configparser
import random

class EmailSender:
  emailAdapter = None
  database = None
  valuephrases_steps = {
    0 : ['Did you wear your fitbit?'],
    1000: ['Hungover?'],
    5000: ['Seems like you took a stroll!'],
    8000: ['Good! You reached your goals!'],
    9000: ['Over 9000!'],
    10000: ['Congratulations!'],
    15000: ['Magnificent ya filthy health-freak!', 'That\'s really good!', 'Keep it up maestro!']
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

  def analyse(self, database: DatabaseConnection):
    self.database = database
    today = date.today().isoformat()
    sentEmails= self.database.emails.find_one({'date': today, 'category': 'daily' })
    if (sentEmails != None):
      print('Already sent email: %s' % today)
      return
    queuedAt = datetime.now().isoformat()
    self.createIntentToSend(queuedAt)
    emailParts = {}
    yesterDate = date.today() - timedelta(days=1)
    emailParts['restingHeartRate'] = self.addHeartRate(yesterDate)
    emailParts['steps'] = self.addSteps(yesterDate)
    emailParts['distance'] = self.addDistance(yesterDate)
    sentAt = datetime.now().isoformat()
    self.send(emailParts)
    self.confirmEmailSent(queuedAt, sentAt)
    
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
