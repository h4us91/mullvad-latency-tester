# server_distance.py
import os
import requests
import json
from geopy.distance import geodesic
from mulping import fetchRelays, ping  # Import fetchRelays and ping from mulping.py

COORDINATES_FILE = "coordinates.json"  # File with city coordinates

# Fetch the current location based on Mullvad's API
def fetch_current_location():
    try:
        response = requests.get("https://am.i.mullvad.net/json", timeout=5)  # Set a timeout for the request
        if response.status_code == 200:
            data = response.json()
            return data["latitude"], data["longitude"]
    except Exception as e:
        print(f"Failed to fetch current location: {e}")
    return None, None

# Load coordinates from coordinates.json
def load_coordinates():
    if os.path.exists(COORDINATES_FILE):
        with open(COORDINATES_FILE, "r") as file:
            return json.load(file)
    return {}

# Save coordinates to coordinates.json
def save_coordinates(coordinates):
    with open(COORDINATES_FILE, "w") as file:
        json.dump(coordinates, file, indent=4)

# Update coordinates using OpenStreetMap API if not present in coordinates.json
def update_coordinates(relays_data):
    coordinates = load_coordinates()
    updated = False

    for relay in relays_data:
        city_key = f"{relay['country_name']}-{relay['city_name']}"
        if city_key not in coordinates:
            print(f"Fetching coordinates for {city_key}")
            coords = fetch_coordinates_from_osm(relay['city_name'], relay['country_name'])
            if coords:
                coordinates[city_key] = coords
                updated = True
                print(f"Coordinates for {city_key} added: {coords}")
            else:
                print(f"Failed to fetch coordinates for {city_key}")

    if updated:
        save_coordinates(coordinates)
        print("Coordinates updated successfully.")
    else:
        print("No new coordinates were added.")

# Fetch coordinates using OpenStreetMap API
def fetch_coordinates_from_osm(city, country):
    try:
        # Use Nominatim API to fetch the coordinates with a timeout
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"city": city, "country": country, "format": "json"},
            timeout=5  # Set a 5 second timeout for the request
        )
        data = response.json()
        if data and len(data) > 0:
            # Return the first result's coordinates
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Failed to fetch coordinates from OpenStreetMap: {e}")
    return None

# Calculate distance from the current location to each relay
def calculate_distances(current_location, relays_data):
    coordinates = load_coordinates()
    distances = []
    for relay in relays_data:
        city_key = f"{relay['country_name']}-{relay['city_name']}"
        if city_key in coordinates:
            relay_coords = coordinates[city_key]
            distance = geodesic(current_location, relay_coords).kilometers
            distances.append((relay['hostname'], distance, relay['ipv4_addr_in']))
    return sorted(distances, key=lambda x: x[1])  # Sort by distance

# Function to calculate latency (ping) for each server using the imported ping function
def get_server_latency(ip_address, count=1, timeout=1000):
    try:
        # Use the ping function from mulping.py
        _, avg_latency, _ = ping(ip_address, count=count, timeout=timeout)
        return avg_latency
    except Exception as e:
        print(f"Failed to calculate latency for {ip_address}: {e}")
        return None

# Main function to get closest servers with latency
def find_closest_servers():
    relays_data = fetchRelays()

    current_location = fetch_current_location()
    if not current_location or current_location == (None, None):
        print("Could not get current location. Exiting...")
        return

    print("Updating coordinates...")
    update_coordinates(relays_data)  # Update coordinates if necessary
    distances = calculate_distances(current_location, relays_data)

    # Print the closest servers with their distances and latencies
    result = "\nClosest servers based on current location and latency:\n"
    for hostname, distance, ip in distances[:10]:  # Show top 10 closest servers
        latency = get_server_latency(ip)  # Calculate latency for each server
        latency_display = f"{latency:.2f} ms" if latency is not None else "N/A"
        result += f"{hostname} - {distance:.2f} km - {latency_display}\n"
        print(f"{hostname} - {distance:.2f} km - {latency_display}")

    return result

# Entry point for running the script directly
if __name__ == "__main__":
    result = find_closest_servers()
    if result:
        print(result)
