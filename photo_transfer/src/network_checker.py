import subprocess


class NetworkChecker:
    def __init__(self, network, system):
        self.network = network
        self.system = system

    def poll(self):
        if self.system == "Windows":
            command = ["netsh", "wlan", "show", "interfaces"]
        elif self.system == "Pi":
            command = ["nmcli", "-t", "-f", "IN-USE,SSID", "device", "wifi", "list", "--rescan", "no"]
        else:
            raise ValueError("Operating system not supported.")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )

        current_network = ""

        if self.system == "Windows":
            for line in result.stdout.splitlines():
                if line.strip().startswith("State") and line.split(":", 1)[1].strip() != "connected":
                    break
                if line.strip().startswith("SSID"):
                    current_network = line.split(":", 1)[1].strip()
                    break

        elif self.system == "Pi":
            for line in result.stdout.splitlines():
                if line.startswith("*:"):
                    current_network = line[2:]
                    break

        return current_network == self.network