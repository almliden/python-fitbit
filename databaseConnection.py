from sshtunnel import SSHTunnelForwarder
import pymongo
import configparser
import os.path

class DatabaseConfig:
  REMOTE_HOST=None
  REMOTE_BIND_ADDRESS=None
  REMOTE_BIND_PORT=None
  SSH_USER=None
  SSH_PASS=None
  MONGO_DB=None
  MONGO_USER=None
  MONGO_PASS=None

class DatabaseConnection:
  client=None
  db=None
  databaseConfig=DatabaseConfig

  def __init__(self, databaseConfig):
    self.databaseConfig=databaseConfig
    self.server = SSHTunnelForwarder(
      ssh_address_or_host=self.databaseConfig.REMOTE_HOST,
      ssh_username=self.databaseConfig.SSH_USER,
      ssh_password=self.databaseConfig.SSH_PASS,
      remote_bind_address=(self.databaseConfig.REMOTE_BIND_ADDRESS, self.databaseConfig.REMOTE_BIND_PORT)
    )
  
  def connect(self, database=None):
    self.server.start()
    self.client = pymongo.MongoClient(self.databaseConfig.REMOTE_BIND_ADDRESS, self.server.local_bind_port)
    database = database if database != None else self.databaseConfig.MONGO_DB
    self.db = self.client[database]
    try:
      self.db.authenticate(self.databaseConfig.MONGO_USER, self.databaseConfig.MONGO_PASS)
    except (pymongo.errors.OperationFailure):
      print("Could not authenticate against %s", database)
    return self.db

  def __del__(self):
    self.disconnect()

  def disconnect(self):
    if (self.client != None):
      self.client.disconnect()
      self.server.stop()

class DatabaseConfigurator:
  conf = DatabaseConfig

  def __init__(self, configName='databaseConnectionConfig.ini'):
    if not os.path.isfile(configName):
      raise FileExistsError("Config file not found")
    parser=configparser.ConfigParser()
    parser.read(configName)
    self.conf.REMOTE_HOST=parser.get('SSH Credentials', 'REMOTE_HOST')
    self.conf.REMOTE_BIND_ADDRESS=parser.get('SSH Credentials', 'REMOTE_BIND_ADDRESS')
    self.conf.REMOTE_BIND_PORT=int(parser.get('SSH Credentials', 'REMOTE_BIND_PORT'))
    self.conf.SSH_USER=parser.get('SSH Credentials', 'SSH_USER')
    self.conf.SSH_PASS=parser.get('SSH Credentials', 'SSH_PASS')
    self.conf.MONGO_DB=parser.get('MongoDB Credentials', 'MONGO_DB')
    self.conf.MONGO_USER=parser.get('MongoDB Credentials', 'MONGO_USER')
    self.conf.MONGO_PASS=parser.get('MongoDB Credentials', 'MONGO_PASS')
  
  def Config(self):
    return self.conf