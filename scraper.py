import requests
import logging
import time
from bs4 import BeautifulSoup

base_uri = "https://efdsearch.senate.gov/search"
home_uri = "/home/"
report_uri = "/report/data/"
last_token = ""

BATCH_SIZE = 100
RATE_LIMIT_SECS = 3
PDF_PREFIX = '/search/view/paper/'
LOGGER = logging.getLogger(__name__)

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
    login_data = {
        'start': '100',
        'length': str(BATCH_SIZE),
        'report_types': '[11]',
        'filer_types': '[]',
        'submitted_start_date': '02/01/2024 00:00:00',
        'submitted_end_date': '',
        'candidate_state': '',
        'senator_state': '',
        'office_id': '',
        'first_name': '',
        'last_name': '',
        'csrfmiddlewaretoken': token
    }

    r = s.post(base_uri + report_uri, data=login_data, headers={'Referer': base_uri})

def main():
    csrf = get_csrf()
    get_reports(csrf)

if __name__ == '__main__':
    log_format = '[%(asctime)s %(levelname)s] %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)
    main()