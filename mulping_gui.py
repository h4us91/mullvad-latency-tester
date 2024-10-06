import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import time
import json
import server_distance  # Import server_distance for the new feature
from mulping import getRelays, COUNTRY_NAME, CITY_NAME, COUNTRY_CODE, CITY_CODE, PROVIDER, BANDWIDTH, IPV4, IPV6, TYPE, WIREGUARD, OPENVPN, ping  # Import necessary functions and variables

# Function to load relays and sort countries alphabetically
def load_dynamic_relays():
    try:
        relays = getRelays()
        if not relays:
            raise ValueError("No relays data found.")
        countries = sorted({relay[COUNTRY_NAME] for relay in relays})  # Sort countries alphabetically
        cities_by_country = {}

        for relay in relays:
            country_name = relay[COUNTRY_NAME]
            city_name = relay[CITY_NAME]
            if country_name not in cities_by_country:
                cities_by_country[country_name] = []
            if city_name not in cities_by_country[country_name]:
                cities_by_country[country_name].append(city_name)

        return relays, countries, cities_by_country
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load relays: {e}")
        return [], [], {}

# Function to update city dropdown based on the selected country
def update_city_dropdown(event):
    selected_country_name = country_var.get()
    if selected_country_name != "Please select":
        city_dropdown['state'] = 'readonly'  # Enable city dropdown
        cities = cities_by_country[selected_country_name]
        city_dropdown.config(values=cities)
        city_var.set('')  # Reset city when country is changed
    else:
        city_dropdown['state'] = 'disabled'  # Disable city dropdown if no country is selected

# Function to execute the script as a separate thread
def run_mulping_thread():
    stop_animation.clear()
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, "Starting ping operations...\n")  # Display message in the console
    threading.Thread(target=run_mulping).start()

# Function to update coordinates and relays data
def update_coordinates_and_relays():
    output_text_closest.delete("1.0", tk.END)  # Clear the closest server console before starting
    output_text_closest.insert(tk.END, "Updating coordinates and relays...\n")
    try:
        relays_data = server_distance.fetchRelays()  # Use fetchRelays from mulping.py
        server_distance.update_coordinates(relays_data)
        output_text_closest.insert(tk.END, "Coordinates and relays updated successfully.\n")
    except Exception as e:
        messagebox.showerror("Error", str(e))
        output_text_closest.insert(tk.END, f"Error: {str(e)}\n")

# Function to find the closest servers and display in GUI console
def find_closest_servers():
    output_text_closest.delete("1.0", tk.END)  # Clear previous output for closest server
    output_text_closest.insert(tk.END, "Finding the closest servers...\n")

    def display_closest_servers():
        try:
            relays_data = server_distance.fetchRelays()
            current_location = server_distance.fetch_current_location()
            if not current_location or current_location == (None, None):
                output_text_closest.insert(tk.END, "Could not get current location.\n")
                return

            distances = server_distance.calculate_distances(current_location, relays_data)

            output_text_closest.insert(tk.END, "\nClosest servers based on current location and latency:\n")
            
            # Calculate latency for each server and store the result
            server_list = []
            for hostname, distance, ip in distances[:10]:  # Show top 10 closest servers
                _, avg_latency, _ = ping(ip, count=1, timeout=1000)  # Calculate latency using ping
                latency = avg_latency if avg_latency is not None else float('inf')  # If latency is None, set it to infinity for sorting
                server_list.append((hostname, distance, ip, latency))
            
            # Sort the server list by latency (lowest latency first)
            server_list = sorted(server_list, key=lambda x: x[3])

            # Display the sorted servers in the GUI console
            for hostname, distance, ip, latency in server_list:
                latency_display = f"{latency:.2f} ms" if latency != float('inf') else "N/A"
                output_text_closest.insert(tk.END, f"{hostname} - {distance:.2f} km - {latency_display}\n")

        except Exception as e:
            output_text_closest.insert(tk.END, f"Error: {str(e)}\n")

    threading.Thread(target=display_closest_servers).start()

# Update the run_mulping function to include the new filters
def run_mulping():
    try:
        country_name = country_var.get()
        city_name = city_var.get()
        server_type = server_type_var.get()  # Get the selected server type
        num_pings = int(num_pings_entry.get())  # Ensure num_pings is an integer
        timeout = int(timeout_entry.get())  # Ensure timeout is an integer
        min_bandwidth = int(min_bandwidth_var.get())  # Get minimum bandwidth value

        if not country_name or country_name == "Please select" or not city_name:
            messagebox.showerror("Error", "Please select a country and a city.")
            stop_animation.set()
            return

        country_code = next((relay[COUNTRY_CODE] for relay in relays if relay[COUNTRY_NAME] == country_name), None)
        city_code = next((relay[CITY_CODE] for relay in relays if relay[CITY_NAME] == city_name and relay[COUNTRY_NAME] == country_name), None)

        if not country_code or not city_code:
            messagebox.showerror("Error", "Failed to get country or city code.")
            stop_animation.set()
            return

        # Filter relays by selected country and city
        selected_relays = [relay for relay in relays if relay[COUNTRY_CODE] == country_code and relay[CITY_CODE] == city_code]

        # Filter relays further by server type (WireGuard or OpenVPN)
        if server_type == "WireGuard":
            selected_relays = [relay for relay in selected_relays if relay.get("type") == "wireguard"]
        elif server_type == "OpenVPN":
            selected_relays = [relay for relay in selected_relays if relay.get("type") == "openvpn"]

        # Filter by provider if a specific provider is selected
            selected_relays = [relay for relay in selected_relays if relay.get(PROVIDER) == provider_filter]

        # Filter by minimum bandwidth
        selected_relays = [relay for relay in selected_relays if relay.get(BANDWIDTH, 0) >= min_bandwidth]

        if not selected_relays:
            messagebox.showerror("Error", f"No servers found for {country_name} - {city_name} with type {server_type}, provider {provider_filter}, and minimum bandwidth {min_bandwidth} Mbps.")
            stop_animation.set()
            return

        # Dictionary to track server latencies
        server_latencies = {}

        output_text.insert(tk.END, f"Starting {num_pings} ping iterations for each server...\n")
        output_text.see(tk.END)  # Auto-scroll

        # Run ping for each server and gather latencies
        for relay in selected_relays:
            hostname = relay.get("hostname", "Unknown")
            ipv4_addr = relay.get("ipv4_addr_in", "N/A")
            output_text.insert(tk.END, f"\nPinging {hostname} ({ipv4_addr})...\n")

            output_text.see(tk.END)  # Auto-scroll

            _, avg_latency, _ = ping(ipv4_addr, count=num_pings, timeout=timeout)

            # Display ping result in the console
            if avg_latency is not None:
                output_text.insert(tk.END, f"Ping {hostname}: {avg_latency:.2f} ms\n")
                server_latencies[hostname] = avg_latency
            else:
                output_text.insert(tk.END, f"Ping {hostname}: No response\n")
            output_text.see(tk.END)  # Auto-scroll

        stop_animation.set()

        if server_latencies:
            # Find the server with the lowest latency
            best_server = min(server_latencies, key=server_latencies.get)
            average_latency = server_latencies[best_server]

            # Format and display the final message
            final_message = "\n" + "#" * 40 + "\n"
            final_message += "#{:^38}#\n".format("Best Server Based on Average Latency")
            final_message += "#{:^38}#\n".format(f"Server: {best_server}")
            final_message += "#{:^38}#\n".format(f"Average Latency: {average_latency:.3f} ms")
            final_message += "#" * 40 + "\n"
            final_message += "\nDONE!\n"
            output_text.insert(tk.END, final_message)
            output_text.see(tk.END)  # Auto-scroll
        else:
            output_text.insert(tk.END, "\nNo server latency information found.\n")
            output_text.see(tk.END)  # Auto-scroll

    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        stop_animation.set()

# Create main GUI window
root = tk.Tk()
root.title("Mulping GUI")

# Create a Notebook for the tabs
notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

# Create the main frame for the first tab
frame_main = ttk.Frame(notebook)
notebook.add(frame_main, text="Main")

# Create the main frame for the new tab (Closest Server)
frame_closest = ttk.Frame(notebook)
notebook.add(frame_closest, text="Closest Server")

# Initialize dropdown variables and checkboxes
country_var = tk.StringVar(value="Please select")  # Initialize with "Please select"
city_var = tk.StringVar()
server_type_var = tk.StringVar(value="WireGuard")  # Default to WireGuard

# Load current relays
relays, countries, cities_by_country = load_dynamic_relays()
if not relays:
    messagebox.showerror("Error", "No relays found. Please update the coordinates or check your connection.")
    root.destroy()  # Exit the program if no relays are found

# --- Main Tab ---
# Dropdown menus for country and city selection
ttk.Label(frame_main, text="Select Country:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
country_dropdown = ttk.Combobox(frame_main, textvariable=country_var, values=["Please select"] + list(countries), state="readonly")
country_dropdown.grid(row=0, column=1, padx=5, pady=5)
country_dropdown.bind("<<ComboboxSelected>>", update_city_dropdown)  # Bind event to update cities

ttk.Label(frame_main, text="Select City:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
city_dropdown = ttk.Combobox(frame_main, textvariable=city_var, values=[], state="disabled")  # Empty values and disabled until a country is selected
city_dropdown.grid(row=1, column=1, padx=5, pady=5)

# Dropdown for Server Type
ttk.Label(frame_main, text="Server Type:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
server_type_dropdown = ttk.Combobox(frame_main, textvariable=server_type_var, values=["WireGuard", "OpenVPN"], state="readonly")
server_type_dropdown.grid(row=2, column=1, padx=5, pady=5)

# Input fields for number of pings and timeout
ttk.Label(frame_main, text="Number of Pings:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
num_pings_entry = ttk.Entry(frame_main)
num_pings_entry.insert(0, "5")
num_pings_entry.grid(row=3, column=1, padx=5, pady=5)

ttk.Label(frame_main, text="Timeout (s):").grid(row=4, column=0, sticky="e", padx=5, pady=5)
timeout_entry = ttk.Entry(frame_main)
timeout_entry.insert(0, "5")
timeout_entry.grid(row=4, column=1, padx=5, pady=5)

# Provider dropdown
providers = sorted({relay[PROVIDER] for relay in relays})
provider_var = tk.StringVar(value="All Providers")
ttk.Label(frame_main, text="Provider:").grid(row=6, column=0, sticky="e", padx=5, pady=5)
provider_dropdown = ttk.Combobox(frame_main, textvariable=provider_var, values=["All Providers"] + list(providers), state="readonly")
provider_dropdown.grid(row=6, column=1, padx=5, pady=5)

# Minimum Bandwidth entry

# Output text field for main tab
output_text = tk.Text(frame_main, wrap=tk.WORD, height=15, width=50)
output_text.grid(row=8, column=0, columnspan=2, padx=5, pady=5)

# Scrollbar for the text field in the main tab
scrollbar = ttk.Scrollbar(frame_main, orient="vertical", command=output_text.yview)
scrollbar.grid(row=8, column=2, sticky="ns")
output_text["yscrollcommand"] = scrollbar.set

# Start button for the main tab
start_button = ttk.Button(frame_main, text="Start", command=run_mulping_thread)
start_button.grid(row=9, column=0, columnspan=2, pady=10)

# --- Closest Server Tab ---
# Output text area for displaying results in the closest server tab
output_text_closest = tk.Text(frame_closest, wrap=tk.WORD, height=15, width=50)
output_text_closest.pack(pady=10)

# Frame for the buttons in the closest server tab
button_frame = ttk.Frame(frame_closest)
button_frame.pack(pady=10)

# Add buttons to the new tab for closest server feature
update_button = ttk.Button(button_frame, text="Update Coordinates", command=update_coordinates_and_relays)
update_button.grid(row=0, column=0, padx=5)

find_button = ttk.Button(button_frame, text="Find Closest Servers", command=find_closest_servers)
find_button.grid(row=0, column=1, padx=5)

# Animation stop flag
stop_animation = threading.Event()

# Start the GUI main loop
root.mainloop()
