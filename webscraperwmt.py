"""WALMART IMAGE SCRAPER.

Scrapes images from your list on WALMART

Author: ehgp
"""
import json
import os
import re
import shutil
import string
from os import listdir
from os.path import isfile, join
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def format_filename(s):
    """Take a string and return a valid filename constructed from the string.

    Uses a whitelist approach: any characters not present in valid_chars are
    removed. Also spaces are replaced with underscores.

    Note: this method may produce invalid filenames such as ``, `.` or `..`
    When I use this method I prepend a date string like '2009_01_15_19_46_32_'
    and append a file extension like '.txt', so I avoid the potential of using
    an invalid filename.

    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = "".join(c for c in s if c in valid_chars)
    return filename


path = Path(os.getcwd())
Path("log").mkdir(parents=True, exist_ok=True)
URL = "https://www.walmart.com/ip/LED-Face-Mask-Luminous-Programmable-Message-Display-Mask-Rechargeable/978504239"
title = "Bluetooth App LED Mask Customize"

# # def imagewebscraperwmt(URL,title):

page = requests.get(URL)

soup = BeautifulSoup(page.content, "html.parser")

imgfilename = re.findall(
    r"(http:|https:)(\/\/.walmartimages.com[^\"\']*)(96.png|96.jpg|96.jpeg|96.gif|96.png|96.svg|96.webp)",
    str(soup),
)

imgfilename = ["".join(i) for i in imgfilename]
imgfilename = list(dict.fromkeys(imgfilename))

os.makedirs(Path(path, "Dropshipping Items", title), exist_ok=True)

for idx, url in enumerate(imgfilename):
    with open(Path(path, "Dropshipping Items", title, f"{title}{idx}.jpg"), "wb") as f:
        response = requests.get(url.replace("96", "300"))
        f.write(response.content)
