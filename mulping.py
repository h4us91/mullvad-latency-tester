#!/bin/env python3

import os
import sys
import json
import argparse
import subprocess
import numpy as np
from time import time
from random import randint

# Platform and system variables
UNIX = "UNIX"
WINDOWS = "WINDOWS"
ON_WINDOWS = False
ON_UNIX = False

# Check if the script is running on a UNIX or Windows system
if "linux" in sys.platform or "darwin" in sys.platform:
    ON_UNIX = True
elif "win" in sys.platform:
    ON_WINDOWS = True
else:
    print("Unknown OS, assuming UNIX based")
    ON_UNIX = True

# Function to handle failure cases
def failure(err):
    print(err, file=sys.stderr)
    sys.exit(1)

RELAYS_LINK = "https://api.mullvad.net/www/relays/all/"
RELAYS_FILE_UNIX = "/tmp/mulpingData"

# Set file paths and timeout based on the operating system
if ON_UNIX:
    RELAYS_FILE = RELAYS_FILE_UNIX
    DEFAULT_TIMEOUT = 10
else:
    RELAYS_FILE = "C:\\Users\\" + os.getlogin() + "\\AppData\\Local\\Temp\\mulpingData"
    DEFAULT_TIMEOUT = 10000

# Relay attributes
TIMESTAMP_INDEX = 0
HOSTNAME = "hostname"
TYPE = "type"
ACTIVE = "active"
COUNTRY_CODE = "country_code"
COUNTRY_NAME = "country_name"
CITY_CODE = "city_code"
CITY_NAME = "city_name"
IPV4 = "ipv4_addr_in"
IPV6 = "ipv6_addr_in"
PROVIDER = "provider"
BANDWIDTH = "network_port_speed"
OWNED = "owned"
STBOOT = "stboot"
RTT = "round_trip_time"

WIREGUARD = "wireguard"
OPENVPN = "openvpn"
BRIDGE = "bridge"

#############################
# Relay filtering utilities #
#############################

# Lambda functions for filtering relay attributes
eqAttr = lambda a: (lambda v: (lambda r: a in r and r[a] == v))
neqAttr = lambda a: (lambda v: (lambda r: a in r and r[a] != v))
geqAttr = lambda a: (lambda v: (lambda r: a in r and r[a] >= v))

# Functions to combine multiple filters
filterOr = lambda filters: (lambda r: [f(r) for f in filters].count(True) > 0)
filterAnd = lambda filters: (lambda r: [f(r) for f in filters].count(False) == 0)

# Utility function to create new filters based on conditions
def getFilter(source, getSubFilter, aggregator, filters):
    conditions = list(map(getSubFilter, source))
    newFilter = aggregator(conditions)
    filters.append(newFilter)

#########################
# Relays data retrieval #
#########################

# Fetch relay data from the API
def fetchRelays():
    print("Fetching relays... ", end="")
    sys.stdout.flush()
    import requests
    try:
        relays = requests.get(f"{RELAYS_LINK}").json()
    except:
        failure("Could not get relays")
    relays.insert(TIMESTAMP_INDEX, time())  # Insert current timestamp at the beginning
    with open(RELAYS_FILE, "w") as f:
        json.dump(relays, f)
    del relays[TIMESTAMP_INDEX]
    print("done!\n")
    return relays

# Load relay data from a local file
def loadRelays():
    with open(RELAYS_FILE, "r") as f:
        relays = json.loads(f.read())
    if not isinstance(relays[TIMESTAMP_INDEX], (float, int)):
        raise Exception
    if time() - relays[TIMESTAMP_INDEX] >= 43200:  # Check if data is older than 12 hours
        raise Exception
    del relays[TIMESTAMP_INDEX]
    return relays

# Retrieve relay data, either by loading from file or fetching from the API
def getRelays():
    if os.path.isfile(RELAYS_FILE):
        try:
            relays = loadRelays()
        except:
            relays = fetchRelays()
    else:
        relays = fetchRelays()
    return relays

##################
# Ping utilities #
##################

# Function to parse ping command output and return min, avg, and max latency values
def parsePing(pingOutput, platform=UNIX):
    """
    This function parses the output of the ping command and returns
    the minimum, average, and maximum latency values.
    """
    print("Debug: Ping Output:")
    print(pingOutput)  # Print raw ping output for debugging

    lines = pingOutput.splitlines()
    while "" in lines: lines.remove("")  # Remove empty lines

    if platform == UNIX:
        try:
            # Unix/Linux parsing (ping statistics at the end of the output)
            stats_line = [line for line in lines if "min/avg/max" in line or "rtt min/avg/max" in line]
            if not stats_line:
                return None, None, None

            # min/avg/max/mdev = 0.040/0.041/0.042/0.001 ms
            rtts = stats_line[0].split("=")[-1].strip().split(" ")[0].split("/")
            rtts = [float(rtt) for rtt in rtts]
            return rtts[0], rtts[1], rtts[2]
        except Exception as e:
            print(f"Error parsing UNIX ping output: {e}")
            return None, None, None
    else:
        try:
            # Windows parsing (look for lines with "Minimum", "Maximum", and "Average")
            stats_line = [line for line in lines if "Minimum" in line and "Maximum" in line]
            if not stats_line:
                return None, None, None

            # Minimum = 1ms, Maximum = 3ms, Average = 2ms
            values = [int(v.split(" ")[-1].replace("ms", "")) for v in stats_line[0].split(",")]
            return values[0], values[2], values[1]  # Min, Avg, Max
        except Exception as e:
            print(f"Error parsing Windows ping output: {e}")
            return None, None, None

# Function to run the ping command
def ping(addr, count, timeout=DEFAULT_TIMEOUT, ipv6=False):
    try:
        if ON_UNIX:
            pingCommand = ["ping", addr, "-nqc", str(count), "-W", str(timeout)]
        else:
            pingCommand = ["ping", addr, "-n", str(count), "-w", str(timeout)]
        if ipv6: pingCommand.append("-6")
        pingProcess = subprocess.run(pingCommand, capture_output=True)
    except:
        failure("The ping program could not be called")
    if pingProcess.returncode != 0:
        return None, None, None
    return parsePing(pingProcess.stdout.decode("utf-8", errors="ignore"), platform=UNIX if ON_UNIX else WINDOWS)

#####################
# Advanced Function #
#####################

# Function to calculate average latency for a list of relays
def calculate_average_latency(relays, ping_count=5, timeout=10, ipv6=False):
    """
    Performs multiple ping attempts and calculates the average latency.
    """
    average_latencies = {r[HOSTNAME]: [] for r in relays}

    print(f"Starting {ping_count} ping iterations for each server...\n")
    for _ in range(ping_count):
        for index, r in enumerate(relays):
            host = r[HOSTNAME]
            address = r[IPV6] if ipv6 else r[IPV4]
            _, rtt, _ = ping(address, 1, timeout=timeout, ipv6=ipv6)
            if rtt is not None:
                average_latencies[host].append(rtt)
                print(f"Ping {host}: {rtt:.2f}ms")

    # Calculate the average latency for each server
    average_rtt = {host: np.mean(latencies) if latencies else None for host, latencies in average_latencies.items()}

    # Update the RTT values in the relay data
    for r in relays:
        r[RTT] = average_rtt[r[HOSTNAME]]

    return relays

########
# Main #
########

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="mulping",
        description="Batch pings utility for Mullvad VPN (not affiliated)",
    )

    # CLI options
    relayConditions = []

    parser.add_argument("-c", "--country", action="store", help="Only select servers located in the countries specified", nargs="+", metavar="country_code")
    parser.add_argument("-C", "--city", action="store", help="Only select servers located in the cities specified", nargs="+", metavar="city_code")
    parser.add_argument("-w", "--wireguard", action="store_true", help="Only select WireGuard servers")
    parser.add_argument("-o", "--openvpn", action="store_true", help="Only select OpenVPN servers")
    parser.add_argument("-6", "--ipv6", action="store_true", help="Use IPv6 to ping servers (requires IPv6 connectivity on both ends)")
    parser.add_argument("-t", "--timeout", action="store", help="Maximum time to wait for each ping response", metavar="timeout", default=10, type=int)
    parser.add_argument("-np", "--num-pings", action="store", help="Number of ping iterations to perform", metavar="num_pings", default=5, type=int)

    args = parser.parse_args()

    # Apply filters based on CLI arguments
    if args.country:
        getFilter(args.country, eqAttr(COUNTRY_CODE), filterOr, relayConditions)
    if args.city:
        getFilter(args.city, eqAttr(CITY_CODE), filterOr, relayConditions)
    if args.wireguard:
        relayConditions.append(eqAttr(TYPE)(WIREGUARD))
    if args.openvpn:
        relayConditions.append(eqAttr(TYPE)(OPENVPN))

    # Retrieve and filter relays
    relays = list(filter(filterAnd(relayConditions), getRelays()))
    if not relays:
        failure("The conditions specified resulted in no relays")

    # Calculate average latency for each relay
    relays_with_avg_latency = calculate_average_latency(relays, ping_count=args.num_pings, timeout=args.timeout, ipv6=args.ipv6)

    # Output the server with the best average latency
    reachable_relays = list(filter(lambda r: r[RTT] is not None, relays_with_avg_latency))
    reachable_relays = sorted(reachable_relays, key=lambda r: r[RTT])

    if reachable_relays:
        best_server = reachable_relays[0]
        print(f"\nBest server based on average latency: {best_server[HOSTNAME]} ({best_server[RTT]:.3f}ms average latency)")
    else:
        print("No reachable servers found based on the criteria.")
