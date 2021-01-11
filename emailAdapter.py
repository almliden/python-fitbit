import configparser
import smtplib, ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailAdapterConfig:
  port = 465
  account = None
  password = None
  server = None

class EmailAdapter:
  config = EmailAdapterConfig
  context = None

  def __init__(self, emailAdapterConfig=None):
    if (emailAdapterConfig != None):
      self.config = emailAdapterConfig
    else:
      raise('You need to provide login details')
    if (self.config.server == None or self.config.account == None or self.config.password == None):
      raise('Not enough information to connect to server')

  def sendEmail(self, sender, receiver, subject, message, sender_text = None, content_type = None, sender_name=None):
    if (self.config.server == None or self.config.account == None or self.config.password == None):
      raise('Not enough information to connect to server')
    self.context = ssl.create_default_context()
    message_content = MIMEMultipart("text")
    message_content["From"] = sender if sender_name == None else '{sender_name} <{sender}>'.format(sender_name = sender_name, sender=sender)
    message_content["To"] = receiver
    message_content["Subject"] = subject
    if (len(content_type.keys()) > 0):
      part = MIMEText(message, "html")
      for k, v in content_type.items():
        part.add_header(k, v)
    else:
      part = MIMEText(message, "text")

    message_content.attach(part)
    text = message_content.as_string()

    with smtplib.SMTP_SSL(self.config.server, self.config.port, context=self.context) as server:
      server.login(self.config.account, self.config.password)
      server.sendmail(sender, receiver, text)

class EmailAdapterConfigurator:
  config = None
  configName = None

  def __init__(self, EmailAdapterConfig=None):
    if (EmailAdapterConfig != None):
      self.config = EmailAdapterConfig
    self.configName = 'config.ini'

  def Config(self, fileName=None):
    if not os.path.isfile(self.configName):
      raise FileExistsError("Config file not found")
    parser=configparser.ConfigParser()
    parser.read(self.configName)
    self.config = EmailAdapterConfig
    self.config.port = int(parser.get('Email', 'EMAIL_PORT', fallback = 465))
    self.config.account = parser.get('Email', 'EMAIL_ACCOUNT', fallback = None)
    self.config.password = parser.get('Email', 'EMAIL_PASSWORD', fallback = None)
    self.config.server = parser.get('Email', 'EMAIL_SERVER', fallback = None)
    return self.config


## Example Usage
# config = EmailAdapterConfigurator()
# emailAdapter = EmailAdapter(config.Config())

# content_type = {
#   'MIME-Version' : '1.0',
# }

#emailAdapter.sendEmail(sender = 'from@example.com', receiver = 'to@example.com', subject = 'Example', message = '<h1>Daily report</h1>', content_type=content_type, sender_name='Email Service')
