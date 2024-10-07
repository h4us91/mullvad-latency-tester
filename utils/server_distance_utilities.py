import os
import requests
import json
from geopy.distance import geodesic
from utils.relay_utilities import fetchRelays
from utils.ping_utilities import ping
import sys

if getattr(sys, 'frozen', False):  
    BASE_DIR = os.path.dirname(sys.executable) 
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(BASE_DIR)
COORDINATES_FILE = os.path.join(BASE_DIR, "data", "coordinates.json")


# Helper function to print messages to GUI or console
def gui_print(message, output_text=None):
    print(message)  
    if output_text is not None:
        output_text.insert("end", message + "\n")  
        output_text.see("end")  
        output_text.update_idletasks()  

# Fetch the current location based on Mullvad's API
def fetch_current_location(output_text=None):
    try:
        response = requests.get("https://am.i.mullvad.net/json", timeout=5)  
        if response.status_code == 200:
            data = response.json()
            return data["latitude"], data["longitude"]
    except Exception as e:
        gui_print(f"Failed to fetch current location: {e}", output_text)
    return None, None

def load_coordinates(output_text=None):
    try:
        if os.path.exists(COORDINATES_FILE):
            print(f"Loading coordinates from {COORDINATES_FILE}.")  
            with open(COORDINATES_FILE, "r") as file:
                return json.load(file)
        print(f"Coordinates file not found at {COORDINATES_FILE}.") 
    except Exception as e:
        print(f"Failed to load coordinates: {e}")  
    return {}

def save_coordinates(coordinates, output_text=None):
    try:
        with open(COORDINATES_FILE, "w") as file:
            json.dump(coordinates, file, indent=4)
        print(f"Coordinates saved successfully at {COORDINATES_FILE}.") 
    except Exception as e:
        print(f"Failed to save coordinates: {e}")  



# Update coordinates using OpenStreetMap API if not present in coordinates.json
def update_coordinates(relays_data, output_text=None):
    coordinates = load_coordinates(output_text)
    updated = False

    for relay in relays_data:
        city_key = f"{relay['country_name']}-{relay['city_name']}"
        if city_key not in coordinates:
            gui_print(f"Fetching coordinates for {city_key}", output_text)
            coords = fetch_coordinates_from_osm(relay['city_name'], relay['country_name'], output_text)
            if coords:
                coordinates[city_key] = coords
                updated = True
                gui_print(f"Coordinates for {city_key} added: {coords}", output_text)
            else:
                gui_print(f"Failed to fetch coordinates for {city_key}", output_text)

    if updated:
        save_coordinates(coordinates, output_text)
        gui_print("Coordinates updated successfully.", output_text)
    else:
        gui_print("No new coordinates were added.", output_text)

# Fetch coordinates using OpenStreetMap API
def fetch_coordinates_from_osm(city, country, output_text=None):
    try:
        # Use Nominatim API to fetch the coordinates with a timeout
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"city": city, "country": country, "format": "json"},
            timeout=5  # Set a 5 second timeout for the request
        )
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        gui_print(f"Failed to fetch coordinates from OpenStreetMap: {e}", output_text)
    return None

# Calculate distance from the current location to each relay
def calculate_distances(current_location, relays_data, output_text=None):
    coordinates = load_coordinates(output_text)
    distances = []
    for relay in relays_data:
        city_key = f"{relay['country_name']}-{relay['city_name']}"
        if city_key in coordinates:
            relay_coords = coordinates[city_key]
            distance = geodesic(current_location, relay_coords).kilometers
            distances.append((relay['hostname'], distance, relay['ipv4_addr_in']))
    return sorted(distances, key=lambda x: x[1])  # Sort by distance

# Function to calculate latency (ping) for each server using the imported ping function
def get_server_latency(ip_address, count=1, timeout=1000, output_text=None):
    try:
        _, avg_latency, _ = ping(ip_address, count=count, timeout=timeout)
        return avg_latency
    except Exception as e:
        gui_print(f"Failed to calculate latency for {ip_address}: {e}", output_text)
        return None

# Main function to get closest servers with latency without updating coordinates
def find_closest_servers(output_text=None):
    relays_data = fetchRelays()

    current_location = fetch_current_location(output_text)
    if not current_location or current_location == (None, None):
        gui_print("Could not get current location. Exiting...", output_text)
        return

    gui_print("Calculating distances to closest servers...", output_text)
    distances = calculate_distances(current_location, relays_data, output_text)
    gui_print("\nClosest servers based on current location and latency:\n", output_text)

    for hostname, distance, ip in distances[:10]:  # Show top 10 closest servers
        latency = get_server_latency(ip, output_text=output_text)  # Calculate latency for each server
        latency_display = f"{latency:.2f} ms" if latency is not None else "N/A"
        gui_print(f"{hostname} - {distance:.2f} km - {latency_display}", output_text)


