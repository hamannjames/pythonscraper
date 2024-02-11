import pymongo

def create_stock_sentinel_databse(client: pymongo.MongoClient):
    DB = "stocksentinel"
    db = client[DB]

    db.command({"customAction": "CreateDatabase", "offerThroughput": 400})

def create_transactors_collection(db: pymongo.database.Database):
    COLLECTION = "transactors"

    indexes = [
        {"key": {"_id": 1}, "name": "_id_1"},
        {"key": {"bio_id", 1}, "name": "_bio_id"},
        {'key': {'first_name': 1}, 'name': '_first_name'},
        {'key': {'last_name': 1}, 'name': '_last_name'}
    ]

    db.command({"customAction": "CreateCollection", "collection": COLLECTION, 'indexes': indexes})

def create_transactions_collection(db: pymongo.database.Database):
    COLLECTION = "transactions"

    indexes = [
        {"key": {"_id": 1}, "name": "_id_1"},
        {"key": {"ticker": 1}, "name": "_ticker"},
        {"key": {
            "transactor.bio_id": 1, 
            "transactor.first_name": 1, 
            "transactor.last_name": 1
        }, "name": "_transactor_name_transactor_bio_id"},
        {"key": {"transaction_date": 1}, "name": "_transaction_date"},
        {"key": {"amount_min": 1}, "name": "_amount_min"},
        {"key": {"amount_max": 1}, "name": "_amount_max"},
    ]

    db.command({"customAction": "CreateCollection", "collection": COLLECTION, 'indexes': indexes})