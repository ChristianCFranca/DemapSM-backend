import pymongo
from pymongo import MongoClient
import os

DATABASE_LOGIN = os.environ.get('DATABASE_LOGIN')
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')

if not DATABASE_LOGIN or not DATABASE_PASSWORD:
    from dotenv import load_dotenv
    load_dotenv()
    DATABASE_LOGIN = os.environ.get('DATABASE_LOGIN')
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')
    if not DATABASE_LOGIN or not DATABASE_PASSWORD:
        raise Exception("No DATABASE_LOGIN or DATABASE_PASSWORD available.")
    else:
        print("Database data available through .env file! Connecting...")
else:
    print("Database data available! Connecting...")

URL = f"mongodb+srv://{DATABASE_LOGIN}:{DATABASE_PASSWORD}@cluster0.zj9tl.mongodb.net/Cluster0?"
client = MongoClient(URL)

DB = 'pedidosdecompradb'
db = client[DB]
