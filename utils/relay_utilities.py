import os
import json
import requests
from time import time

# Relay attributes
TIMESTAMP_INDEX = 0
HOSTNAME = "hostname"
TYPE = "type"
COUNTRY_CODE = "country_code"
COUNTRY_NAME = "country_name"
CITY_CODE = "city_code"
CITY_NAME = "city_name"
IPV4 = "ipv4_addr_in"
IPV6 = "ipv6_addr_in"
PROVIDER = "provider"
BANDWIDTH = "network_port_speed"
OWNED = "owned"

WIREGUARD = "wireguard"
OPENVPN = "openvpn"
BRIDGE = "bridge"

RELAYS_LINK = "https://api.mullvad.net/www/relays/all/"
RELAYS_FILE = os.path.join(os.getenv("TEMP"), "mulpingData.json")  # File path for Windows

def fetchRelays():
    """Fetch the latest relays from the Mullvad API and save them locally."""
    try:
        relays = requests.get(f"{RELAYS_LINK}").json()
    except:
        return []
    relays.insert(TIMESTAMP_INDEX, time())  # Insert current timestamp at the beginning
    with open(RELAYS_FILE, "w") as f:
        json.dump(relays, f) 
    del relays[TIMESTAMP_INDEX]
    return relays

def loadRelays():
    """Load relays from the local file if available and not older than 12 hours."""
    with open(RELAYS_FILE, "r") as f:
        relays = json.loads(f.read())
    if not isinstance(relays[TIMESTAMP_INDEX], (float, int)):
        raise Exception
    if time() - relays[TIMESTAMP_INDEX] >= 43200:  # Check if data is older than 12 hours
        raise Exception
    del relays[TIMESTAMP_INDEX]
    return relays

def getRelays():
    """Retrieve relays by loading from file or fetching from the API if not available or outdated."""
    if os.path.isfile(RELAYS_FILE):
        try:
            relays = loadRelays()
        except:
            relays = fetchRelays()
    else:
        relays = fetchRelays()
    return relays
