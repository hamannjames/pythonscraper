# Python Scraper for Stock Sentinel

This scraper pulls transaction and transactor data, scraping it from official sources, and pushes it to an azure cosmos db instance

## Devlog

As of right now, this scraper skips over amendment transactions, meaning that the database has data that needs to be amended. It also skips over paper reports