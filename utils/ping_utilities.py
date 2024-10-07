import subprocess
import tkinter as tk

DEFAULT_TIMEOUT = 10000  # Default timeout for ping in milliseconds

def parsePing(pingOutput):
    """
    Parse the ping command output and return min, avg, and max latency values.
    This function assumes Windows-style ping output.
    """
    try:
        lines = pingOutput.splitlines()
        stats_line = [line for line in lines if "Minimum" in line and "Maximum" in line]
        if not stats_line:
            return None, None, None

        # Extract Minimum, Maximum, and Average values
        values = [int(v.split(" ")[-1].replace("ms", "")) for v in stats_line[0].split(",")]
        return values[0], values[2], values[1]  # Min, Avg, Max
    except Exception:
        return None, None, None

def ping(addr, count, timeout=DEFAULT_TIMEOUT, ipv6=False):
    """
    Run the ping command and return the parsed latency values.
    The ping command is called with the specified `count` and `timeout` values.
    Returns a tuple with (min_latency, avg_latency, max_latency).
    """
    # Create the ping command based on the parameters
    pingCommand = ["ping", addr, "-n", str(count), "-w", str(timeout)]
    if ipv6:
        pingCommand.append("-6")

    # Display the constructed ping command in the terminal (optional for debugging)
    print(f"Executing Ping Command: {' '.join(pingCommand)}")

    try:
        # Configure subprocess to hide the console window
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE  # Hide the window

        # Run the command and hide the console window
        pingProcess = subprocess.run(pingCommand, capture_output=True, startupinfo=si)

        # Check for unsuccessful execution
        if pingProcess.returncode != 0:
            print(f"Ping command failed with return code: {pingProcess.returncode}")
            return None, None, None

        # Parse and return the latency values
        min_latency, avg_latency, max_latency = parsePing(pingProcess.stdout.decode("utf-8", errors="ignore"))
        return min_latency, avg_latency, max_latency
    except Exception as e:
        print(f"Error during ping execution: {e}")
        return None, None, None



def get_latency_for_relays(relays, count=1, timeout=1000, output_text=None, stop_animation=None):
    """
    Ping each relay and return a dictionary with hostname as the key and average latency as the value.
    Optionally, update the GUI console with progress using `output_text`.
    The process can be stopped using `stop_animation`.
    """
    latency_dict = {}
    for relay in relays:
        if stop_animation is not None and stop_animation.is_set():
            print("Ping operation stopped by user.")  
            break

        # Check if relay is a tuple and has 3 elements (hostname, distance, ip)
        if isinstance(relay, tuple) and len(relay) == 3:
            hostname, _, ip = relay  
        else:
            # If relay is a dictionary, extract values normally
            hostname = relay.get("hostname", "Unknown")
            ip = relay.get("ipv4_addr_in", None)  # Use the IPv4 address for pinging

        # Check if we have an IP to ping
        if ip:
            min_latency, avg_latency, max_latency = ping(ip, count=count, timeout=timeout)
            latency = avg_latency if avg_latency is not None else float('inf')
            latency_dict[hostname] = latency

            # Terminal output for each ping with detailed values
            latency_display = f"Min: {min_latency} ms, Avg: {latency:.2f} ms, Max: {max_latency} ms" if latency != float('inf') else "N/A"
            print(f"Ping {hostname} ({ip}): {latency_display}")  

            # Update the GUI console if output_text is provided
            if output_text is not None:
                output_text.insert(tk.END, f"Ping {hostname}: {latency_display}\n")
                output_text.see(tk.END)  # Auto-scroll
                output_text.update_idletasks()  

    return latency_dict
