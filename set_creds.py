"""Set Creds.

Leverages Keyring to add your credentials for each portal and then retrieves them in code.
author: ehgp
"""
import datetime as dt
import logging
import logging.config
import os
from getpass import getpass, getuser
from pathlib import Path

import keyring
import yaml

# Paths
path = Path(os.getcwd())

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

# Leverages Windows Credential Manager and Mac Keychain to store credentials
# and also makes environment variables that store your credentials in your computer
dsns = [
    "FACEBOOK_EMAIL",
    "FACEBOOK_PASSWORD",
    # "ALI_EMAIL",
    # "ALI_PASSWORD",
    # "CHEWY_EMAIL",
    # "CHEWY_PASSWORD",
    "EBAY_EMAIL",
    "EBAY_PASSWORD",
    # "ETSY_EMAIL",
    # "ETSY_PASSWORD",
    # "WAYFAIR_EMAIL",
    # "WAYFAIR_PASSWORD",
    # "WALMART_EMAIL",
    # "WALMART_PASSWORD",
]
user = getuser()
for dsn in dsns:
    if keyring.get_password(dsn, user) is None:
        prompt = f"Please input {dsn}: "
        password = getpass(prompt=prompt, stream=None)
        keyring.set_password(dsn, user, password)
