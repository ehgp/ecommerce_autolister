"""Get New Items.

Automatically gets new links from products from your lists

Author: ehgp
"""
import os
from pathlib import Path

import pandas as pd

import webscraperali
import webscraperchewy
import webscraperebay
import webscraperetsy
import webscraperwayfair

path = Path(os.getcwd())
Path("log").mkdir(parents=True, exist_ok=True)

binary_path = Path(path, "chromedriver.exe")

new_items_ali = pd.read_csv(Path(path, "Dropshipping Items", "new_links_ali.csv"))

new_items_ebay = pd.read_csv(Path(path, "Dropshipping Items", "new_links_ebay.csv"))

new_items_etsy = pd.read_csv(Path(path, "Dropshipping Items", "new_links_etsy.csv"))

new_items_wayfair = pd.read_csv(
    Path(path, "Dropshipping Items", "new_links_wayfair.csv")
)

if len(new_items_ali) > 0:
    webscraperali.listingscraper(new_items_ali["link"].to_list())

if len(new_items_ebay) > 0:
    webscraperebay.listingscraper(new_items_ebay["link"].to_list())

if len(new_items_etsy) > 0:
    webscraperetsy.listingscraper(new_items_etsy["link"].to_list())

if len(new_items_wayfair) > 0:
    webscraperwayfair.listingscraper(new_items_wayfair["link"].to_list())

# etsy checks 4 pages, ali 2, ebay 2, wayfair all
webscraperali.linkscraperali()
webscraperchewy.linkscraperchewy()
webscraperebay.linkscraperebay()
webscraperetsy.linkscraperetsy()
webscraperwayfair.linkscraperwayfair()
