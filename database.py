from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

import os
from dotenv import load_dotenv

if os.path.exists('.env'):
    load_dotenv()

DATABASE_LOGIN = os.environ.get('DATABASE_LOGIN')
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')
DB = os.environ.get('DATABASE_NAME')

if not DATABASE_LOGIN or not DATABASE_PASSWORD:
    raise Exception("No DATABASE_LOGIN or DATABASE_PASSWORD available.")
else:
    print("\033[94m"+"DB:" + "\033[0m" + "\t  Database data available through .env file! Connecting...")

if not DB:
    raise Exception("No DATABASE_NAME available.")

URL = f"mongodb+srv://{DATABASE_LOGIN}:{DATABASE_PASSWORD}@cluster0.zj9tl.mongodb.net/Cluster0?"

try:
    # Cria o cliente utilizando a URL
    client = MongoClient(URL)
    
    # Pinga o cliente para verificar se existe
    client.admin.command('ping')

    print("\033[94m"+"CLIENT:" + "\033[0m" + "\t  The Client URL exists and responded. Connecting to the provided DATABASE_NAME...")
except ConnectionFailure:
    raise Exception("The Client couldn't connect to the provided URL.")

if DB not in client.list_database_names():
    raise Exception("The Client connected to the URL, but the database provided don't exist.")
else:
    print("\033[94m"+"DB:" + "\033[0m" + "\t  The DATABASE_NAME provided exists in the Client. Connected.")

db = client[DB]
