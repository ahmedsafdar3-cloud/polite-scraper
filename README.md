# Polite Scraper

A small Python scraping pipeline for the FlyRank Backend Track assignment.

The scraper processes the first three catalogue pages from Books to Scrape, discovers 60 unique books, visits each product page, extracts raw data, normalizes and validates the records, stores clean JSON output, survives broken pages, and writes a run report.

## Target classification

Target: Books to Scrape

Scope: Only the first 3 catalogue pages.

Purpose: This project is for the FlyRank Backend Track scraping assignment.

Data collected:

- title
- product URL
- price
- availability
- rating
- description
- source page
- fetch time

Books to Scrape is a sandbox created for practicing web scraping.

Robots result: no robots file found.

I will not reuse this code on another site without checking its rules and terms first.

## Tech stack

- Python 3.10+
- Requests
- Beautiful Soup
- Pydantic
- JSON

## Installation

Clone the repository:

```bash
git clone https://github.com/ahmedsafdar3-cloud/polite-scraper.git
cd polite-scraper