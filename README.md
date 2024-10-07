# Mullvad Latency Tester

This project provides a GUI tool to measure the latency of Mullvad VPN servers. It allows users to quickly find the best server based on geographic proximity and latency.

## Features

### Latency Test Tab
- Allows you to select country, city, and server type (WireGuard, OpenVPN, or Bridge).
- Performs multiple ping tests to selected servers and displays the results in the GUI.

### Find Closest Servers Tab
- Automatically identifies your current location and calculates the distance to various Mullvad VPN servers.
- Displays the closest servers based on distance and latency.

### Server Coordinate Updates
- Uses OpenStreetMap to fetch and update the geographic coordinates of servers as needed.
- Stores and retrieves coordinates locally to optimize future searches.


## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/mullvad-latency-tester.git
   cd mullvad-latency-tester
