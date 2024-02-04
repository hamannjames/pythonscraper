import requests
import pymongo
import os
import sys
import datetime
from datetime import datetime as innerdatetime
from dotenv import load_dotenv

load_dotenv()

CONN_STRING = os.environ.get("COSMOSDB_CONNECTION_STRING")
COLLECTION = "transactors"
DB = "stocksentinel"

client = pymongo.MongoClient(CONN_STRING)

db = client[DB]

if DB not in client.list_database_names():
    db.command({"customAction": "CreateDatabase", "offerThroughput": 400})

senators = db[COLLECTION]

if COLLECTION not in db.list_collection_names():
    indexes = [
        {"key": {"_id": 1}, "name": "_id_1"},
        {"key": {"bio_id", 1}, "name": "_bio_id"},
        {'key': {'first_name': 1}, 'name': '_first_name'},
        {'key': {'last_name': 1}, 'name': '_last_name'}
    ]
    db.command({"customAction": "CreateCollection", "collection": COLLECTION, 'indexes': indexes})

current = requests.get('https://theunitedstates.io/congress-legislators/legislators-current.json').json()
previous = requests.get('https://theunitedstates.io/congress-legislators/legislators-historical.json').json()

START_DATE = datetime.datetime(2011, 1, 1)
NOW = innerdatetime.now()

def filter_current_and_sen(mem: {})->bool:
    sen_start = innerdatetime.strptime(mem['terms'][-1]['end'], '%Y-%m-%d')
    return sen_start > START_DATE and mem['terms'][-1]['type'] == 'sen'

def filter_sen(mem: {})->bool:
    return mem['terms'][-1]['type'] == 'sen'

def format_senator(sen: {})->{}:
    name: {} = sen['name']
    bio: {} = sen['bio']
    term: {} = sen['terms'][-1]
    id: {} = sen['id']

    end_date = innerdatetime.strptime(term['end'], '%Y-%m-%d')

    return {
        "bio_id": id["bioguide"],
        "first_name": get_first_name(name),
        "last_name": get_last_name(name),
        "full_name": get_full_name(name),
        "party": get_party(term["party"]),
        "state": term["state"],
        "birthday": bio['birthday'],
        'active': end_date > NOW
    }

def get_first_name(name: {})->str:
    if 'first_name' not in name.keys():
        return name['first']

    return name['first_name']

def get_last_name(name: {})->str:
    if 'last_name' not in name.keys():
        return name['last']

    return name['last_name']

def get_full_name(name: {})->str:
    if 'official_full' not in name.keys():
        return f"{name['first']} {name['last']}"
    
    return name['official_full']

def get_party(party: str)->str:
    if party == 'Independent':
        return 'I'
    
    if party == 'Republican':
        return "R"

    if party == "Democrat":
        return "D"
    
    if len(party) > 1:
        return "I"
    
    return party

for sen in filter(filter_current_and_sen, previous + current):
    formatted: {} = format_senator(sen)

    result = senators.update_one({"bio_id": formatted['bio_id']}, {"$set": formatted}, upsert=True)

    print(f"Upserted document with senator {formatted['full_name']}")
