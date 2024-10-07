import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading
import utils.server_distance_utilities as server_distance_utilities  
from utils.relay_utilities import getRelays, COUNTRY_NAME, CITY_NAME, COUNTRY_CODE, CITY_CODE, PROVIDER, BANDWIDTH, TYPE, WIREGUARD, OPENVPN, BRIDGE
from utils.ping_utilities import get_latency_for_relays

# Function to load relays and sort countries alphabetically
def load_dynamic_relays():
    try:
        relays = getRelays()
        if not relays:
            raise ValueError("No relays data found.")
        countries = sorted({relay[COUNTRY_NAME] for relay in relays})  # Sort countries alphabetically
        cities_by_country = {}
        providers_by_country_city = {}

        for relay in relays:
            country_name = relay[COUNTRY_NAME]
            city_name = relay[CITY_NAME]
            provider_name = relay[PROVIDER]
            
            if country_name not in cities_by_country:
                cities_by_country[country_name] = []
            if city_name not in cities_by_country[country_name]:
                cities_by_country[country_name].append(city_name)
            
            # Create providers mapping
            if country_name not in providers_by_country_city:
                providers_by_country_city[country_name] = {}
            if city_name not in providers_by_country_city[country_name]:
                providers_by_country_city[country_name][city_name] = []
            if provider_name not in providers_by_country_city[country_name][city_name]:
                providers_by_country_city[country_name][city_name].append(provider_name)

        return relays, countries, cities_by_country, providers_by_country_city
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load relays: {e}")
        return [], [], {}, {}

# Function to update city dropdown and select the first city
def update_city_dropdown(event):
    selected_country_name = country_var.get()
    selected_server_type = server_type_var.get()
    
    if selected_country_name != "Please select":
        cities = cities_by_country[selected_country_name]

        # Check if there are any Bridge servers in the selected country
        bridge_available = any(
            relay[TYPE] == BRIDGE and relay[COUNTRY_NAME] == selected_country_name for relay in relays
        )

        if selected_server_type == "Bridge":
            # Filter cities based on Bridge server availability
            bridge_cities = [
                city for city in cities 
                if any(relay[TYPE] == BRIDGE and relay[CITY_NAME] == city for relay in relays if relay[COUNTRY_NAME] == selected_country_name)
            ]
            
            if not bridge_cities:  # If no bridge cities found, show info and disable city dropdown
                messagebox.showinfo("Bridge Not Available", "Bridge servers are not available for the selected country.")
                
                # Disable Bridge option in the server type dropdown and switch to WireGuard/OpenVPN
                server_type_dropdown.set("WireGuard" if bridge_available else "OpenVPN")
                
                # Filter cities based on the new selected server type (WireGuard or OpenVPN)
                filtered_cities = [
                    city for city in cities 
                    if any(relay[TYPE] == server_type_var.get() and relay[CITY_NAME] == city for relay in relays if relay[COUNTRY_NAME] == selected_country_name)
                ]

                # If no cities for the new type, show all cities
                cities = filtered_cities if filtered_cities else cities
                
                # Update city dropdown and select the first city
                city_dropdown['state'] = 'readonly'
                city_dropdown.config(values=cities)
                if cities:
                    city_var.set(cities[0])  # Set the first city as selected
                else:
                    city_var.set('')
                    city_dropdown['state'] = 'disabled'
                    city_dropdown.config(values=[])
                update_provider_dropdown()
                return
            else:
                cities = bridge_cities  # Use bridge cities if available

        # Filter cities based on the selected server type
        if selected_server_type in [WIREGUARD, OPENVPN]:
            cities = [
                city for city in cities 
                if any(relay[TYPE] == selected_server_type and relay[CITY_NAME] == city for relay in relays if relay[COUNTRY_NAME] == selected_country_name)
            ]

        city_dropdown['state'] = 'readonly'  # Enable city dropdown
        city_dropdown.config(values=cities)
        if cities:
            city_var.set(cities[0])  # Set first city as selected
        else:
            city_var.set('')
            city_dropdown['state'] = 'disabled'
            city_dropdown.config(values=[])
        update_provider_dropdown()
    else:
        city_dropdown['state'] = 'disabled'  # Disable city dropdown if no country is selected
        city_dropdown.config(values=[])

        
# Function to update provider dropdown based on selected country and city
def update_provider_dropdown(*args):
    selected_country_name = country_var.get()
    selected_city_name = city_var.get()

    if selected_country_name and selected_city_name:
        # Disable provider dropdown if Mullvad-owned is set to True
        if owned_var.get() == "True":
            provider_var.set("All Providers")
            provider_dropdown['state'] = 'disabled'
        else:
            providers = sorted(providers_by_country_city[selected_country_name].get(selected_city_name, []))
            provider_dropdown.config(values=["All Providers"] + providers)
            provider_var.set("All Providers")  # Set default value to "All Providers"
            provider_dropdown['state'] = 'readonly'  # Enable dropdown if not disabled        

# Function to execute the script as a separate thread
def run_mulping_thread():
    start_button['state'] = 'disabled'  # Disable Start button
    stop_button['state'] = 'normal'     # Enable Stop button
    stop_animation.clear()
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, "Starting ping operations...\n")  # Display message in the console
    threading.Thread(target=run_mulping).start()

# Function to stop the current operation
def stop_mulping():
    stop_animation.set()
    output_text.insert(tk.END, "\nOperation stopped by user.\n")
    stop_button['state'] = 'disabled'  # Disable Stop button
    start_button['state'] = 'normal'   # Enable Start button

# Function to update coordinates and relays data
def update_coordinates_and_relays():
    output_text_closest.delete("1.0", tk.END)  # Clear the closest server console before starting
    output_text_closest.insert(tk.END, "Updating coordinates and relays...\n")

    def update_coordinates_thread():
        try:
            relays_data = server_distance_utilities.fetchRelays()  # Use fetchRelays from mulping.py
            server_distance_utilities.update_coordinates(relays_data, output_text_closest)  # Update coordinates
            output_text_closest.insert(tk.END, "Coordinates and relays updated successfully.\n")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            output_text_closest.insert(tk.END, f"Error: {str(e)}\n")

    threading.Thread(target=update_coordinates_thread).start()

# Function to find the closest servers and display in GUI console
def find_closest_servers():
    output_text_closest.delete("1.0", tk.END)  # Clear previous output for closest server
    output_text_closest.insert(tk.END, "Finding the closest servers...\n")

    def display_closest_servers():
        try:
            result = server_distance_utilities.find_closest_servers(output_text_closest)
            if result:
                output_text_closest.insert(tk.END, result)
        except Exception as e:
            output_text_closest.insert(tk.END, f"Error: {str(e)}\n")

    threading.Thread(target=display_closest_servers).start()



# Function to handle changes in owned_var dropdown
def update_owned_filter(*args):
    if owned_var.get() == "True":
        provider_var.set("All Providers")
        provider_dropdown['state'] = 'disabled'
    else:
        provider_dropdown['state'] = 'readonly'
    update_provider_dropdown()

def run_mulping():
    try:
        country_name = country_var.get()
        city_name = city_var.get()
        server_type = server_type_var.get()  # Get the selected server type
        num_pings = int(num_pings_entry.get())  # Ensure num_pings is an integer
        timeout = int(timeout_entry.get())  # Ensure timeout is an integer
        provider_filter = provider_var.get()
        min_bandwidth = int(min_bandwidth_var.get())  # Get minimum bandwidth value

        # Use the value from owned_var to filter for Mullvad-owned servers
        owned_filter = owned_var.get() == "True"

        if not country_name or country_name == "Please select" or not city_name:
            messagebox.showerror("Error", "Please select a country and a city.")
            return

        country_code = next((relay[COUNTRY_CODE] for relay in relays if relay[COUNTRY_NAME] == country_name), None)
        city_code = next((relay[CITY_CODE] for relay in relays if relay[CITY_NAME] == city_name and relay[COUNTRY_NAME] == country_name), None)

        if not country_code or not city_code:
            messagebox.showerror("Error", "Failed to get country or city code.")
            return

        # Filter relays by selected country and city
        selected_relays = [relay for relay in relays if relay[COUNTRY_CODE] == country_code and relay[CITY_CODE] == city_code]

        # Filter relays further by server type (WireGuard, OpenVPN, or Bridge)
        if server_type == "WireGuard":
            selected_relays = [relay for relay in selected_relays if relay.get(TYPE) == WIREGUARD]
        elif server_type == "OpenVPN":
            selected_relays = [relay for relay in selected_relays if relay.get(TYPE) == OPENVPN]
        elif server_type == "Bridge":
            selected_relays = [relay for relay in selected_relays if relay.get(TYPE) == BRIDGE]

        # Filter by provider if a specific provider is selected and owned_var is not True
        if provider_filter != "All Providers" and not owned_filter:
            selected_relays = [relay for relay in selected_relays if relay.get(PROVIDER) == provider_filter]

        # Filter by Mullvad-owned servers if the owned_var is True
        if owned_filter:
            selected_relays = [relay for relay in selected_relays if relay.get("owned")]

        # Filter by minimum bandwidth
        selected_relays = [relay for relay in selected_relays if relay.get(BANDWIDTH, 0) >= min_bandwidth]

        if not selected_relays:
            messagebox.showerror("Error", f"No servers found for {country_name} - {city_name} with type {server_type}, provider {provider_filter}, and minimum bandwidth {min_bandwidth} Mbps.")
            return

        output_text.insert(tk.END, f"Starting {num_pings} ping iterations for each server...\n")
        output_text.see(tk.END)  # Auto-scroll
        output_text.update_idletasks()  # Ensure the GUI updates

        # Use the refactored function to get latency values for each server and update GUI console
        server_latencies = get_latency_for_relays(selected_relays, count=num_pings, timeout=timeout, output_text=output_text, stop_animation=stop_animation)

        if server_latencies:
            # Find the server with the lowest latency
            best_server = min(server_latencies, key=server_latencies.get)
            average_latency = server_latencies[best_server]

            # Format and display the final message only if not stopped
            if not stop_animation.is_set():
                final_message = "\n" + "#" * 40 + "\n"
                final_message += "#{:^38}#\n".format("Best Server Based on Average Latency")
                final_message += "#{:^38}#\n".format(f"Server: {best_server}")
                final_message += "#{:^38}#\n".format(f"Average Latency: {average_latency:.3f} ms")
                final_message += "#" * 40 + "\n"
                final_message += "\nDONE!\n"
                output_text.insert(tk.END, final_message)
                output_text.see(tk.END)  # Auto-scroll
                output_text.update_idletasks()  # Ensure the GUI updates
        else:
            output_text.insert(tk.END, "\nNo server latency information found.\n")
            output_text.see(tk.END)  # Auto-scroll
            output_text.update_idletasks()  # Ensure the GUI updates

    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        stop_animation.set()
        stop_button['state'] = 'disabled'  # Disable Stop button
        start_button['state'] = 'normal'   # Enable Start button



# Create main GUI window
root = tk.Tk()
root.title("Mullvad Latency Tester")

icon_path = os.path.join(os.path.dirname(__file__), "assets", "mullvad.ico")
root.iconbitmap(icon_path)

# Create a Notebook for the tabs
notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

# Create the main frame for the first tab
frame_main = ttk.Frame(notebook)
notebook.add(frame_main, text="Latency Test")

# Create the main frame for the new tab (Closest Server)
frame_closest = ttk.Frame(notebook)
notebook.add(frame_closest, text="Find Closest Servers")

# Initialize dropdown variables and checkboxes
country_var = tk.StringVar(value="Please select")  # Initialize with "Please select"
city_var = tk.StringVar()
server_type_var = tk.StringVar(value="WireGuard")  # Default to WireGuard

# Load current relays
relays, countries, cities_by_country, providers_by_country_city = load_dynamic_relays()
if not relays:
    messagebox.showerror("Error", "No relays found. Please update the coordinates or check your connection.")
    root.destroy()  # Exit the program if no relays are found

# --- Latency Test Tab ---
# Define padding for consistent spacing
default_padx = 10
default_pady = 5

# Dropdown menus for country and city selection
ttk.Label(frame_main, text="Select Country:").grid(row=0, column=0, sticky="e", padx=default_padx, pady=default_pady)
country_dropdown = ttk.Combobox(frame_main, textvariable=country_var, values=["Please select"] + list(countries), state="readonly")
country_dropdown.grid(row=0, column=1, sticky="ew", padx=default_padx, pady=default_pady)
country_dropdown.bind("<<ComboboxSelected>>", update_city_dropdown)  # Bind event to update cities

ttk.Label(frame_main, text="Select City:").grid(row=1, column=0, sticky="e", padx=default_padx, pady=default_pady)
city_dropdown = ttk.Combobox(frame_main, textvariable=city_var, values=[], state="disabled")  # Empty values and disabled until a country is selected
city_dropdown.grid(row=1, column=1, sticky="ew", padx=default_padx, pady=default_pady)
city_var.trace("w", update_provider_dropdown)  # Bind event to update providers

# Dropdown for Server Type
ttk.Label(frame_main, text="Server Type:").grid(row=2, column=0, sticky="e", padx=default_padx, pady=default_pady)
server_type_dropdown = ttk.Combobox(frame_main, textvariable=server_type_var, values=["WireGuard", "OpenVPN", "Bridge"], state="readonly")
server_type_dropdown.grid(row=2, column=1, sticky="ew", padx=default_padx, pady=default_pady)

# Provider dropdown (directly under Server Type)
provider_var = tk.StringVar(value="All Providers")
ttk.Label(frame_main, text="Provider:").grid(row=3, column=0, sticky="e", padx=default_padx, pady=default_pady)
provider_dropdown = ttk.Combobox(frame_main, textvariable=provider_var, values=["All Providers"], state="readonly")
provider_dropdown.grid(row=3, column=1, sticky="ew", padx=default_padx, pady=default_pady)

# Dropdown for Mullvad-Only Servers
ttk.Label(frame_main, text="Mullvad-Owned Only:").grid(row=4, column=0, sticky="e", padx=default_padx, pady=default_pady)
owned_var = tk.StringVar(value="False")  # Default value is "False"
owned_dropdown = ttk.Combobox(frame_main, textvariable=owned_var, values=["True", "False"], state="readonly")
owned_dropdown.grid(row=4, column=1, sticky="ew", padx=default_padx, pady=default_pady)
owned_var.trace("w", update_owned_filter)  # Bind event to update owned servers

# Input fields for number of pings and timeout (aligned with ComboBoxes)
ttk.Label(frame_main, text="Number of Pings:").grid(row=5, column=0, sticky="e", padx=default_padx, pady=default_pady)
num_pings_entry = ttk.Entry(frame_main)
num_pings_entry.insert(0, "5")
num_pings_entry.grid(row=5, column=1, sticky="ew", padx=default_padx, pady=default_pady)

ttk.Label(frame_main, text="Timeout (s):").grid(row=6, column=0, sticky="e", padx=default_padx, pady=default_pady)
timeout_entry = ttk.Entry(frame_main)
timeout_entry.insert(0, "5")
timeout_entry.grid(row=6, column=1, sticky="ew", padx=default_padx, pady=default_pady)

# Minimum Bandwidth entry (Gbps)
min_bandwidth_var = tk.StringVar(value="0")  # Default to 0 (no bandwidth filter)
ttk.Label(frame_main, text="Min. Bandwidth (Gbps):").grid(row=7, column=0, sticky="e", padx=default_padx, pady=default_pady)
min_bandwidth_entry = ttk.Entry(frame_main, textvariable=min_bandwidth_var)
min_bandwidth_entry.grid(row=7, column=1, sticky="ew", padx=default_padx, pady=default_pady)

# Output text field for main tab
output_text = tk.Text(frame_main, wrap=tk.WORD, height=15, width=50)
output_text.grid(row=8, column=0, columnspan=3, padx=default_padx, pady=default_pady)

# Output text field for main tab (disable user input)
output_text = tk.Text(frame_main, wrap=tk.WORD, height=15, width=50, state="normal")  
output_text.grid(row=8, column=0, columnspan=3, padx=default_padx, pady=default_pady)

# Scrollbar for the text field in the main tab
scrollbar = ttk.Scrollbar(frame_main, orient="vertical", command=output_text.yview)
scrollbar.grid(row=8, column=2, sticky="ns")
output_text["yscrollcommand"] = scrollbar.set

# Frame for Start and Stop buttons
button_frame = ttk.Frame(frame_main)
button_frame.grid(row=9, column=0, columnspan=3, pady=default_pady)  # Center the button frame

# Add Start and Stop buttons inside the button frame, closer together
start_button = ttk.Button(button_frame, text="Start", command=run_mulping_thread)
start_button.pack(side="left", padx=(default_padx, 5), pady=default_pady)

stop_button = ttk.Button(button_frame, text="Stop", command=stop_mulping, state='disabled')
stop_button.pack(side="left", padx=(5, default_padx), pady=default_pady)



# --- Closest Server Tab ---
# Output text area for displaying results in the closest server tab
output_text_closest = tk.Text(frame_closest, wrap=tk.WORD, height=15, width=50)
output_text_closest.pack(pady=10)

# Frame for the buttons in the closest server tab
button_frame = ttk.Frame(frame_closest)
button_frame.pack(pady=10)

# Add buttons to the new tab for closest server feature in the desired order
find_button = ttk.Button(button_frame, text="Find Closest Servers", command=find_closest_servers)
find_button.grid(row=0, column=0, padx=5)

update_button = ttk.Button(button_frame, text="Update Server Coordinates", command=update_coordinates_and_relays)
update_button.grid(row=0, column=1, padx=5)


# Animation stop flag
stop_animation = threading.Event()

# Start the GUI main loop
root.mainloop()
