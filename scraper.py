import requests
import logging
import time
from bs4 import BeautifulSoup
import pymongo
import sys
import os
import datetime
from dotenv import load_dotenv
from db import create_stock_sentinel_databse, create_transactions_collection

load_dotenv()

base_uri = "https://efdsearch.senate.gov/search"
ptr_base_uri = "https://efdsearch.senate.gov/"
home_uri = "/home/"
report_uri = "/report/data/"
last_token = ""

BATCH_SIZE = 100
RATE_LIMIT_SECS = 3
PDF_PREFIX = '/search/view/paper/'
LOGGER = logging.getLogger(__name__)

TRANSACTION_ROW_INDEX = 0
TRANSACTION_DATE_INDEX = 1
OWNER_INDEX = 2
TICKER_INDEX = 3
ASSET_NAME_INDEX = 4
ASSET_TYPE_INDEX = 5
TRANSACTION_TYPE_INDEX = 6
AMOUNT_INDEX = 7
COMMENT_INDEX = 8

CONN_STRING = os.environ.get("COSMOSDB_CONNECTION_STRING")
TRANSACTIONS = "transactions"
TRANSACTORS = "transactors"
DB = "stocksentinel"

client = pymongo.MongoClient(CONN_STRING)

if DB not in client.list_database_names():
    LOGGER.info('Creating Database')
    create_stock_sentinel_databse(client)

db = client[DB]

if TRANSACTIONS not in db.list_collection_names():
    LOGGER.info('Creating Transactions Collection')
    create_transactions_collection(db)

transactions = db[TRANSACTIONS]
senators = list(db[TRANSACTORS].find())

def add_rate_limit(f):
    def with_rate_limit(*args, **kw):
        time.sleep(RATE_LIMIT_SECS)
        return f(*args, **kw)
    return with_rate_limit

s = requests.session()
s.get = add_rate_limit(s.get)
s.post = add_rate_limit(s.post)
s.headers.update({'User-Agent': 'Mozilla/5.0'})

def get_csrf()->str:
    LOGGER.info('Initiating Handshake')
    handshake = s.get(base_uri + home_uri)
    soup = BeautifulSoup(handshake.content, "html.parser")
    csrf = soup.find(attrs={"name": "csrfmiddlewaretoken"}).attrs["value"]

    payload = {
        'prohibition_agreement': '1',
        'csrfmiddlewaretoken': csrf
    }

    LOGGER.info('Initiating Agreement')
    agreement = s.post(base_uri + home_uri, data=payload, headers={'Referer': base_uri + home_uri})
    soup = BeautifulSoup(agreement.content, "html.parser")
    form = soup.find(id="searchForm")

    if not form and 'csrftoken' in s.cookies:
        raise AssertionError('You have not made it past the agreement')

    return s.cookies['csrftoken']

def get_reports(token: str):
    start = 0

    login_data = {
        'start': str(start),
        'length': str(BATCH_SIZE),
        'report_types': '[11]',
        'filer_types': '[]',
        'submitted_start_date': '01/01/2020 00:00:00',
        'submitted_end_date': '',
        'candidate_state': '',
        'senator_state': '',
        'office_id': '',
        'first_name': '',
        'last_name': '',
        'csrfmiddlewaretoken': token
    }

    r = s.post(base_uri + report_uri, data=login_data, headers={'Referer': base_uri})
    r_json = r.json()['data']

    while(len(r_json) > 0):
        handle_reports(r_json)

        start += BATCH_SIZE
        login_data['start'] = str(start)
        r = s.post(base_uri + report_uri, data=login_data, headers={'Referer': base_uri})
        r_json = r.json()['data']

def handle_reports(reports: [str]):
    for report in reports:
        if is_paper_report(report):
            continue

        ptr_report = get_ptr_report(report)
        handle_ptr_report(ptr_report=ptr_report,report_meta=report)

def handle_ptr_report(ptr_report: requests.Response, report_meta: [str]):
    soup = BeautifulSoup(ptr_report.content, "html.parser")
    h1 = soup.find('h1')

    if h1.get_text().lower().find('amendment') > -1:
        handle_amendment(soup, report_meta)
    else:
        handle_new_report(soup, report_meta)

def handle_new_report(html: BeautifulSoup, report_meta: [str]):
    table = html.find('tbody')

    if not table:
        return
    
    ptr_id = get_ptr_report_id(report_meta)
    transactor = get_transactor(report_meta)
    
    rows = table.find_all('tr')

    for row in rows:
        handle_transaction(row=row, ptr_id=ptr_id, transactor=transactor)

def handle_transaction(row: BeautifulSoup, ptr_id: str, transactor: {}):

    cells = row.find_all('td')

    if not is_stock_transaction(cells[5].get_text()):
        return

    amount = cells[AMOUNT_INDEX].get_text().strip()
    amount_min = int(amount.split('-')[0].strip()[1:].replace(',', ''))
    amount_max = int(amount.split('-')[1].strip()[1:].replace(',', ''))

    ptr_row = int(cells[TRANSACTION_ROW_INDEX].get_text().strip())
    
    transaction = {
        "ptr_id": ptr_id,
        "ptr_row": ptr_row,
        "transaction_date": cells[TRANSACTION_DATE_INDEX].get_text().strip(),
        "transactor": transactor,
        "ticker": cells[TICKER_INDEX].get_text().strip(),
        "asset_name": cells[ASSET_NAME_INDEX].get_text().strip(),
        "transaction_type": cells[TRANSACTION_TYPE_INDEX].get_text().strip(),
        "amount_min": amount_min,
        "amount_max": amount_max,
        "comment": cells[COMMENT_INDEX].get_text().strip()
    }

    inserted = transactions.update_one({"ptr_id": ptr_id, "ptr_row": ptr_row}, {"$set": transaction}, upsert=True)

    LOGGER.info(f'Inserted: {inserted.modified_count}')
    
def get_transactor(report_meta: [str]) -> {}:
    first_name = report_meta[0].split(' ')[0].strip().lower()
    last_name = report_meta[1].split(' ')[0].strip().lower()

    matches = list(filter(lambda x: 
        x['last_name'].lower() == last_name and
        (x['first_name'].lower().find(first_name) or
        first_name.find(x['first_name'].lower()) or
        x['first_name'].lower() == first_name)
        , senators))

    if (not len(matches) == 1):
        return None
    
    return matches[0]

def handle_amendment(html: BeautifulSoup, report_meta: [str]):
    pass
    
def is_stock_transaction(type: str)->bool:
    return type.lower().find('stock') > -1

def is_paper_report(item: str) -> bool:
    return item[3].find(PDF_PREFIX) > -1

def get_ptr_report(item: [str]) -> requests.Response:
    link = get_link_of_ptr(item[3])
    return s.get(ptr_base_uri + link)

def get_ptr_report_id(item: [str]) -> str:
    link = item[3]
    start = find_nth(link, '/', 4) + 1
    end = find_nth(link, '/', 5)

    LOGGER.info(f'Getting PTR ID from {link}')
    
    return link[start:end]

def get_link_of_ptr(item: str) -> str:
    start = item.find('"')
    end = item.find('"', start + 1)

    return item[start + 1:end]

def get_links_from_report_response(r: requests.Response)->[str]:
    reports = r.json()['data']

    for report in reports:
        print(report)

    return reports

def find_nth(haystack: str, needle: str, n: int) -> int:
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def main():
    csrf = get_csrf()
    get_reports(csrf)

if __name__ == '__main__':
    log_format = '[%(asctime)s %(levelname)s] %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)
    main()