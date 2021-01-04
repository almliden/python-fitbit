from sshtunnel import SSHTunnelForwarder
import pymongo
import pprint
import configparser
import datetime
import sys

parser = configparser.ConfigParser()
parser.read('config.ini')

REMOTE_HOST = parser.get('SSH Credentials', 'REMOTE_HOST')
SSH_USER = parser.get('SSH Credentials', 'SSH_USER')
SSH_PASS = parser.get('SSH Credentials', 'SSH_PASS')
MONGO_DB = parser.get('MongoDB Credentials', 'MONGO_DB')
MONGO_USER = parser.get('MongoDB Credentials', 'MONGO_USER')
MONGO_PASS = parser.get('MongoDB Credentials', 'MONGO_PASS')

server = SSHTunnelForwarder(
    REMOTE_HOST,
    ssh_username=SSH_USER,
    ssh_password=SSH_PASS,
    remote_bind_address=('127.0.0.1', 27017)
)

server.start()

client = pymongo.MongoClient('127.0.0.1', server.local_bind_port) # server.local_bind_port is assigned local port
db = client[MONGO_DB]
db.authenticate(MONGO_USER, MONGO_PASS)

pprint.pprint(db.collection_names())

post = {"user": "name",
"ACCESS_TOKEN": "token",
"REFRESH_TOKEN": "token",
"REFRESHED": "--"
}

post_id = db.user_tokens.insert_one(post).inserted_id
print(post_id)

client.disconnect()
server.stop()

sys.exit()