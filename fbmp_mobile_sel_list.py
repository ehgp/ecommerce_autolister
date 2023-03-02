"""Selenium FB Mobile Marketplace Dropshipping Automator (SFBMMPDA).

Allows user to leverage an excel sheet to automatically add products to FBMP Mobile

Author: ehgp
"""
import datetime as dt
import logging
import logging.config
import os
import random
import re
import string
import sys
import time
from getpass import getuser
from os import listdir
from os.path import isfile, join
from pathlib import Path

import chromedriver_autoinstaller
import keyring
import pandas as pd
import pyautogui
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from webscraperali import imagewebscraperali
from webscraperchewy import imagewebscraperchewy
from webscraperebay import imagewebscraperebay
from webscraperetsy import imagewebscraperetsy
from webscraperwayfair import imagewebscraperwayfair


def format_filename(s):
    """Take a string and return a valid filename constructed from the string.

    Uses a whitelist approach: any characters not present in valid_chars are
    removed.

    Note: this method may produce invalid filenames such as ``, `.` or `..`
    When I use this method I prepend a date string like '2009_01_15_19_46_32_'
    and append a file extension like '.txt', so I avoid the potential of using
    an invalid filename.

    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = "".join(re.sub("[^A-Za-z0-9]+", " ", c) for c in s if c in valid_chars)
    filename = " ".join(filename.split())
    return filename


def _load_config():
    """Load the configuration yaml and return dictionary of setttings.

    Returns:
        yaml as a dictionary.
    """
    config_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(config_path, "xpath_params.yaml")
    with open(config_path, "r") as config_file:
        config_defs = yaml.safe_load(config_file.read())

    if config_defs.values() is None:
        raise ValueError("parameters yaml file incomplete")

    return config_defs


# chrome_options = Options()
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--window-size=1920x1080")
# from utils.encryption import create_encrypted_config, load_encrypted_config
# os.makedirs(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET', exist_ok = True)
# os.rmdir(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET')
# Creds
user = getuser()
fb_email = keyring.get_password("FACEBOOK_EMAIL", user)
fb_pass = keyring.get_password("FACEBOOK_PASSWORD", user)

# Paths
path = Path(os.getcwd())
# binary_path = Path(path, "chromedriver.exe")
chromedriver_autoinstaller.install()
dropship_sh_path = Path(path, "Dropshipping Items", "DROPSHIPPING_SPREADSHEET.xlsx")
dropship_path = Path(path, "Droppping Items")

# Logging
Path("log").mkdir(parents=True, exist_ok=True)
log_config = Path(path, "log_config.yaml")
timestamp = "{:%Y_%m_%d_%H_%M_%S}".format(dt.datetime.now())
with open(log_config, "r") as log_file:
    config_dict = yaml.safe_load(log_file.read())
    # Append date stamp to the file name
    log_filename = config_dict["handlers"]["file"]["filename"]
    base, extension = os.path.splitext(log_filename)
    base2 = "_" + os.path.splitext(os.path.basename(__file__))[0] + "_"
    log_filename = "{}{}{}{}".format(base, base2, timestamp, extension)
    config_dict["handlers"]["file"]["filename"] = log_filename
    logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)


# OpenBrowser
driver = webdriver.Chrome()
driver.get("https://facebook.com/")

# Logging
email = driver.find_element_by_id("email")
password = driver.find_element_by_id("pass")
# facebook username input
email.send_keys(fb_email)
# facebook password input
password.send_keys(fb_pass)


time.sleep(5)
driver.find_element_by_name("login").click()
# Redicret to fb marketplace
time.sleep(2)
driver.get("https://m.facebook.com/marketplace/selling/item/")

# Filling up form
driver.find_element_by_xpath(
    "/html/body/div[1]/div/div[4]/div/div[1]/div/form/div[1]/div/div[1]/div/div/div/div/div/div[1]"
).click()
time.sleep(4)  # waiting for window popup to open
pyautogui.write(r"C:\Users\ehgp\Pictures\6V.png")  # path of File
pyautogui.press("enter")

time.sleep(5)
title = driver.find_element_by_name("title").send_keys("title teste")

time.sleep(2)
price = driver.find_element_by_name("price").send_keys("50")

time.sleep(2)
driver.find_element_by_xpath(
    "/html/body/div[1]/div/div[4]/div/div[1]/div/form/div[2]/div/div/div[4]/div/div[1]/div/div[2]/input"
).click()

time.sleep(2)
driver.find_element_by_xpath(
    "/html/body/div[2]/div/div[2]/div/div/div[23]/div[1]"
).click()
# driver.find_element_by_xpath("/html/body/div[2]/div/div[2]/div/div/div[35]/div[2]").click()

time.sleep(2)
description = driver.find_element_by_name("description").send_keys("description teste")

time.sleep(2)
driver.find_element_by_xpath(
    "/html/body/div[1]/div/div[4]/div/div[1]/div/form/div[2]/div/div/div[7]/div[3]"
).click()
