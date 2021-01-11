from emailAdapter import EmailAdapter, EmailAdapterConfig, EmailAdapterConfigurator
from datetime import date, datetime
from databaseConnection import DatabaseConnection
import configparser

class EmailSender:
  emailAdapter = None
  database = None

  def __init__(self):
    config = EmailAdapterConfigurator()
    self.emailAdapter = EmailAdapter(config.Config())
    parser=configparser.ConfigParser()
    parser.read('config.ini')
    self.sender=parser.get('Email Daily Healt Report', 'EMAIL_DAILY_HEALTH_REPORT_SENDER')
    self.receiver=parser.get('Email Daily Healt Report', 'EMAIL_DAILY_HEALTH_REPORT_RECEIVER')
    self.buttonHref=parser.get('Email Daily Healt Report', 'EMAIL_DAILY_HEALTH_REPORT_LINK')
    self.template_file_name=parser.get('Email Daily Healt Report', 'EMAIL_DAILY_HEALTH_TEMPLATE')

  def analyse(self, database: DatabaseConnection):
    self.database = database
    today = date.today().isoformat()
    sentEmails= self.database.emails.find_one({'date': today, 'category': 'daily' })
    if (sentEmails != None):
      return
    queuedAt = datetime.datetime.now().isoformat()
    self.createIntentToSend(queuedAt)
    emailParts = {}
    emailParts['restingHeartRate'] = self.addHeartRate()
    sentAt = datetime.datetime.now().isoformat()
    self.send(emailParts)
    self.confirmEmailSent(queuedAt, sentAt)
    
  def createIntentToSend(self, queuedAt: str):
    try:
      self.database.emails.insert_one({ 'date': datetime.date.today().isoformat(), 'category': 'daily', 'queuedAt': queuedAt, 'sent': False })
    except (Exception):
      print('Exception in createIntentToSend')
  
  def confirmEmailSent(self, queuedAt:str, sentAt: str):
    try:
      self.database.emails.find_one_and_update({ 'queuedAt': queuedAt}, { '$set': { 'sent': True, 'sentAt': sentAt } })
    except (Exception):
      print('Exception in confirmEmailSent')

  def addHeartRate(self):
    yesterDate = datetime.date.today() - datetime.timedelta(days=1)
    try:
      yesterdate_heart = self.database.heart.find_one({'activities-heart.dateTime' : yesterDate.isoformat() })
      heartRate = yesterdate_heart['activities-heart'][0]['value']['restingHeartRate']
      if (heartRate != None):
        with open('./email_templates/plainText.html', 'r', -1) as fopen:
          return (fopen.read().format(section_text = 'Resting heart rate: %d' % int(heartRate)))
    except:
      print('Something went wrong in def addHeartRate')
      
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
