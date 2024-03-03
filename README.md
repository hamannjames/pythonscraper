# Python Scraper for Stock Sentinel

This scraper pulls senator stock transaction and transactor data, scraping it from official sources, and pushes it to an azure cosmos db instance. The stock data is incredibly opaque as given by the government, and this library attempts to fix that by putting the data in a digestable format. You can see more of this project on my (github profile)[https://github.com/hamannjames/pythonscraper].

## Process

1. Make initial HTTP handshake with EFD stock transaction report website
2. Make "agreement" handshake with EFD stock transaction report website by sending POST request with CSRF token from form
3. Retrieve new CSRF token and use in a header
4. Make post requests for JSON of PTR (periodic transaction report) reports
5. Parse PTRs for link to actual report
6. Follow link and parse HTML for transaction rows
7. Process individual transaction rows for data and insert into DB
8. Repeat for each PTR returned

All important functions are commented in the code.

## Tools

The most important tools used are PyMongo for the database connection (Azure Cosmos DB, Mongo instance), the requests library for HTTP client, and the BeatifulSoup library for html parsing.

## Todos

Many todos are commented. The main ones are being able to handle "amendment" requests, which means modifying data instead of inserting new data, and also accepting a date parameter as a starting point.