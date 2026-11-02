#!/usr/bin/env python3
"""
Python Network Scanner
======================
Author: Yash Kawade (PRN: 2125UCSM1118)
Course: Network Models and Protocols (NPC)

A multi-threaded network scanner designed to:
  1. Discover active devices across a local network subnet (CIDR).
  2. Resolve and display IP addresses, MAC addresses, and hostnames.
  3. Identify hardware vendors via MAC OUI lookup.
  4. Measure latency / round-trip time (RTT).
  5. Generate comprehensive network reports in JSON, CSV, Markdown, and HTML formats.

Works out of the box with zero external pip dependencies on Windows (using native
Win32 SendARP & ICMP ping) as well as Linux/macOS.
"""

import argparse
import concurrent.futures
import csv
import ctypes
import ipaddress
import json
import os
import platform
import re
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime

# Common MAC OUI prefixes mapped to hardware manufacturers
MAC_VENDOR_DB = {
    "00:0C:29": "VMware, Inc.",
    "00:50:56": "VMware, Inc.",
    "08:00:27": "Oracle VirtualBox",
    "52:54:00": "QEMU / KVM",
    "B8:27:EB": "Raspberry Pi Foundation",
    "DC:A6:32": "Raspberry Pi Foundation",
    "E4:5F:01": "Raspberry Pi Trading",
    "28:CD:C1": "Raspberry Pi Trading",
    "00:1A:11": "Google, Inc.",
    "3C:5A:B4": "Google, Inc.",
    "D8:6C:63": "Google, Inc.",
    "F4:F5:DB": "Google, Inc.",
    "00:17:88": "Philips Lighting",
    "00:1A:2B": "Ayecom Technology",
    "00:26:BB": "Apple, Inc.",
    "28:CF:E9": "Apple, Inc.",
    "3C:07:54": "Apple, Inc.",
    "56:32:C7": "Apple, Inc. (Private/Randomized)",
    "F0:18:98": "Apple, Inc.",
    "BC:D0:74": "Apple, Inc.",
    "AC:DE:48": "Apple, Inc.",
    "A4:83:E7": "Apple, Inc.",
    "F4:34:F0": "Apple, Inc.",
    "00:1F:3B": "Intel Corporation",
    "34:13:E8": "Intel Corporate",
    "80:86:F2": "Intel Corporation",
    "A0:36:BC": "Intel Corporate",
    "00:1E:67": "Intel Corporation",
    "00:15:5D": "Microsoft Hyper-V",
    "70:85:C2": "Microsoft Corporation",
    "00:1B:21": "Intel Corporate",
    "00:1D:72": "Cisco Systems",
    "00:21:A0": "Cisco Systems",
    "00:24:14": "Cisco Systems",
    "00:26:99": "Cisco Systems",
    "50:06:04": "Cisco Systems",
    "70:81:05": "Cisco Systems",
    "C4:72:95": "Cisco Systems",
    "00:18:E7": "Cameo Communications",
    "00:19:E0": "TP-Link Technologies",
    "14:CC:20": "TP-Link Technologies",
    "50:C7:BF": "TP-Link Technologies",
    "70:4F:57": "TP-Link Technologies",
    "98:DA:C4": "TP-Link Technologies",
    "B0:95:75": "TP-Link Technologies",
    "C0:06:C3": "TP-Link Technologies",
    "00:14:D1": "Trendnet",
    "00:18:02": "D-Link Systems",
    "1C:7E:E5": "D-Link International",
    "28:10:7B": "D-Link International",
    "00:1E:58": "D-Link Systems",
    "00:14:BF": "Linksys",
    "00:18:39": "Cisco-Linksys",
    "00:1F:9F": "Actiontec Electronics",
    "00:22:6B": "Cisco-Linksys",
    "00:25:9C": "Cisco-Linksys",
    "24:0A:C4": "Espressif Inc.",
    "30:AE:A4": "Espressif Inc.",
    "84:CC:A8": "Espressif Inc.",
    "A4:CF:12": "Espressif Inc.",
    "C4:4F:33": "Espressif Inc.",
    "EC:FA:BC": "Espressif Inc.",
    "00:23:76": "HTC Corporation",
    "00:26:37": "Samsung Electronics",
    "34:BE:00": "Samsung Electronics",
    "50:85:69": "Samsung Electronics",
    "78:47:1D": "Samsung Electronics",
    "94:01:C2": "Samsung Electronics",
    "B4:07:F9": "Samsung Electronics",
    "E4:7C:F9": "Samsung Electronics",
    "64:A2:F9": "Xiaomi Communications",
    "7C:49:EB": "Xiaomi Communications",
    "AC:C1:EE": "Xiaomi Communications",
    "D8:BB:2C": "Xiaomi Communications",
    "00:15:AF": "Huawei Technologies",
    "00:18:82": "Huawei Technologies",
    "48:46:FB": "Huawei Technologies",
    "70:54:F5": "Huawei Device",
    "00:1E:8C": "ASUSTek Computer",
    "04:D9:F5": "ASUSTek Computer",
    "10:BF:48": "ASUSTek Computer",
    "70:4D:7B": "Dell Inc.",
    "B8:AC:6F": "Dell Inc.",
    "D4:BE:D9": "Dell Inc.",
    "F8:BC:12": "Dell Inc.",
    "00:1A:4B": "Hewlett Packard",
    "3C:D9:2B": "Hewlett Packard",
    "9C:8E:99": "HP Inc.",
}


class NetworkScanner:
    """Core network scanning engine providing discovery and reporting."""

    def __init__(self, target=None, timeout=1.0, max_threads=50, verbose=False):
        self.target = target
        self.timeout = timeout
        self.max_threads = max_threads
        self.verbose = verbose
        self.system = platform.system()
        self.discovered_hosts = []

    def get_default_local_network(self):
        """Auto-detect the primary active local network subnet."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # Inspect netmask or default to /24 if standard class C
            # Under Windows, let's use /24 or detect from ipconfig/Get-NetIPAddress
            net = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            return str(net)
        except Exception:
            return "192.168.1.0/24"

    def get_mac_vendor(self, mac_address):
        """Lookup hardware manufacturer using OUI prefix."""
        if not mac_address or mac_address == "N/A":
            return "Unknown"
        normalized = mac_address.upper().replace("-", ":")
        prefix = ":".join(normalized.split(":")[:3])
        return MAC_VENDOR_DB.get(prefix, "Unidentified Vendor")

    def resolve_mac_windows(self, ip_str):
        """Query MAC address via Win32 SendARP API (zero raw socket dependencies)."""
        try:
            SendARP = ctypes.windll.Iphlpapi.SendARP
            dest_ip = struct.unpack("<I", socket.inet_aton(ip_str))[0]
            mac_addr = (ctypes.c_byte * 6)()
            mac_addr_len = ctypes.c_ulong(6)

            res = SendARP(dest_ip, 0, ctypes.byref(mac_addr), ctypes.byref(mac_addr_len))
            if res == 0:
                return ":".join(f"{b & 0xFF:02X}" for b in mac_addr)
        except Exception:
            pass
        return None

    def resolve_mac_arp_cache(self, ip_str):
        """Inspect the system ARP cache for the target IP."""
        try:
            cmd = ["arp", "-a", ip_str] if self.system == "Windows" else ["arp", "-n", ip_str]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=1.5).decode("utf-8", errors="ignore")
            # Look for standard MAC pattern
            match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", output)
            if match:
                mac = match.group(0).upper().replace("-", ":")
                if mac not in ("FF:FF:FF:FF:FF:FF", "00:00:00:00:00:00"):
                    return mac
        except Exception:
            pass
        return None

    def ping_host(self, ip_str):
        """Ping host using system ICMP ping to check reachability and measure RTT."""
        try:
            start_t = time.perf_counter()
            if self.system == "Windows":
                cmd = ["ping", "-n", "1", "-w", str(int(self.timeout * 1000)), ip_str]
            else:
                cmd = ["ping", "-c", "1", "-W", str(int(self.timeout)), ip_str]

            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            if proc.returncode == 0:
                # Extract TTL or time if reported
                time_match = re.search(r"(?:time[=<]\s*|time=)(\d+(?:\.\d+)?)\s*ms", proc.stdout, re.IGNORECASE)
                if time_match:
                    return True, float(time_match.group(1))
                return True, round(elapsed_ms, 2)
        except Exception:
            pass
        return False, None

    def resolve_hostname(self, ip_str):
        """Attempt reverse DNS lookup to identify device hostname."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_str)
            return hostname
        except Exception:
            return "N/A"

    def scan_single_host(self, ip_str):
        """Perform comprehensive scan of a single IP address."""
        mac = None
        is_active = False
        rtt_ms = None

        # 1. First attempt native ARP resolution (instant and non-intrusive)
        if self.system == "Windows":
            mac = self.resolve_mac_windows(ip_str)
            if mac:
                is_active = True

        # 2. Ping probe
        ping_ok, ping_rtt = self.ping_host(ip_str)
        if ping_ok:
            is_active = True
            rtt_ms = ping_rtt

        # 3. If MAC was not resolved yet, check ARP cache post-ping
        if not mac and is_active:
            mac = self.resolve_mac_arp_cache(ip_str)

        # 4. If active, resolve hostname and vendor
        if is_active:
            hostname = self.resolve_hostname(ip_str)
            vendor = self.get_mac_vendor(mac) if mac else "Unknown"
            host_info = {
                "ip": ip_str,
                "mac": mac if mac else "Unresolved",
                "hostname": hostname,
                "vendor": vendor,
                "rtt_ms": rtt_ms if rtt_ms is not None else 1.0,
                "status": "Active",
            }
            if self.verbose:
                print(f"[+] Found active host: {ip_str} | MAC: {host_info['mac']} | Hostname: {hostname}")
            return host_info
        return None

    def scan(self):
        """Scan the entire target network subnet."""
        if not self.target or self.target.lower() == "auto":
            self.target = self.get_default_local_network()

        network = ipaddress.IPv4Network(self.target, strict=False)
        hosts_to_scan = [str(ip) for ip in network.hosts()]
        total_hosts = len(hosts_to_scan)

        print("=" * 72)
        print("          PYTHON NETWORK SCANNER (Host & MAC Discovery)          ")
        print("=" * 72)
        print(f"[*] Target Subnet    : {network}")
        print(f"[*] Total Addresses  : {total_hosts}")
        print(f"[*] Concurrency      : {self.max_threads} worker threads")
        print(f"[*] Timeout per host : {self.timeout}s")
        print(f"[*] Scan Started     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 72)
        print("[*] Sweeping network via multi-threaded ARP & ICMP probes...")

        start_time = time.time()
        active_hosts = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_ip = {executor.submit(self.scan_single_host, ip): ip for ip in hosts_to_scan}
            for future in concurrent.futures.as_completed(future_to_ip):
                res = future.result()
                if res:
                    active_hosts.append(res)

        elapsed = time.time() - start_time
        # Sort hosts numerically by IP address
        active_hosts.sort(key=lambda h: socket.inet_aton(h["ip"]))
        self.discovered_hosts = active_hosts

        print(f"[+] Scan completed in {elapsed:.2f} seconds.")
        print(f"[+] Discovered {len(active_hosts)} active host(s) on {network}.\n")
        return active_hosts, elapsed


class ReportGenerator:
    """Exports structured network discovery reports across multiple formats."""

    def __init__(self, target_subnet, hosts, elapsed_seconds):
        self.target_subnet = target_subnet
        self.hosts = hosts
        self.elapsed_seconds = elapsed_seconds
        self.timestamp = datetime.now()

    def print_console_table(self):
        """Render a formatted ASCII table in the terminal."""
        print("+" + "-" * 17 + "+" + "-" * 19 + "+" + "-" * 26 + "+" + "-" * 28 + "+" + "-" * 11 + "+")
        print(f"| {'IP Address':<15} | {'MAC Address':<17} | {'Hostname':<24} | {'Vendor / Manufacturer':<26} | {'Latency':<9} |")
        print("+" + "=" * 17 + "+" + "=" * 19 + "+" + "=" * 26 + "+" + "=" * 28 + "+" + "=" * 11 + "+")

        if not self.hosts:
            print(f"| {'No active hosts detected on target subnet':^107} |")
        else:
            for h in self.hosts:
                latency_str = f"{h['rtt_ms']:.1f} ms" if isinstance(h["rtt_ms"], (int, float)) else "N/A"
                print(
                    f"| {h['ip']:<15} | {h['mac']:<17} | {h['hostname'][:24]:<24} | {h['vendor'][:26]:<26} | {latency_str:<9} |"
                )
        print("+" + "-" * 17 + "+" + "-" * 19 + "+" + "-" * 26 + "+" + "-" * 28 + "+" + "-" * 11 + "+")

    def export_json(self, output_path):
        """Export scan results as a JSON report."""
        report = {
            "metadata": {
                "scanner": "Python Network Scanner",
                "author": "Yash Kawade (PRN: 2125UCSM1118)",
                "target_subnet": str(self.target_subnet),
                "scan_timestamp": self.timestamp.isoformat(),
                "duration_seconds": round(self.elapsed_seconds, 2),
                "active_hosts_count": len(self.hosts),
            },
            "active_hosts": self.hosts,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
        print(f"[+] JSON Report saved to      : {output_path}")

    def export_csv(self, output_path):
        """Export scan results as a CSV spreadsheet."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["IP Address", "MAC Address", "Hostname", "Hardware Vendor", "Latency (ms)", "Status"])
            for h in self.hosts:
                writer.writerow([h["ip"], h["mac"], h["hostname"], h["vendor"], h["rtt_ms"], h["status"]])
        print(f"[+] CSV Report saved to       : {output_path}")

    def export_markdown(self, output_path):
        """Generate a GitHub Flavored Markdown report."""
        lines = [
            "# Local Network Discovery Report",
            "",
            f"**Generated by:** Python Network Scanner  ",
            f"**Author:** Yash Kawade (PRN: 2125UCSM1118)  ",
            f"**Target Subnet:** `{self.target_subnet}`  ",
            f"**Scan Date & Time:** `{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}`  ",
            f"**Scan Duration:** `{self.elapsed_seconds:.2f} seconds`  ",
            f"**Total Active Hosts:** `{len(self.hosts)}`  ",
            "",
            "---",
            "",
            "## Discovered Active Devices",
            "",
            "| IP Address | MAC Address | Hostname | Hardware Vendor | Latency | Status |",
            "|---|---|---|---|---|:---:|",
        ]
        if not self.hosts:
            lines.append("| — | — | No active hosts detected | — | — | Inactive |")
        else:
            for h in self.hosts:
                lat = f"{h['rtt_ms']:.1f} ms" if isinstance(h["rtt_ms"], (int, float)) else "N/A"
                lines.append(f"| `{h['ip']}` | `{h['mac']}` | {h['hostname']} | {h['vendor']} | {lat} | {h['status']} |")

        lines.extend([
            "",
            "---",
            "*Report generated automatically by Python Network Scanner.*",
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[+] Markdown Report saved to  : {output_path}")

    def export_html(self, output_path):
        """Generate a modern, responsive HTML dashboard report."""
        rows = ""
        for h in self.hosts:
            lat = f"{h['rtt_ms']:.1f} ms" if isinstance(h["rtt_ms"], (int, float)) else "N/A"
            rows += f"""
            <tr>
                <td><code>{h['ip']}</code></td>
                <td><code>{h['mac']}</code></td>
                <td>{h['hostname']}</td>
                <td><span class="badge vendor">{h['vendor']}</span></td>
                <td>{lat}</td>
                <td><span class="badge status-active">{h['status']}</span></td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Discovery Report - {self.target_subnet}</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --accent: #22c55e;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        header {{
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
        }}
        h1 {{
            margin: 0 0 8px 0;
            color: var(--primary);
            font-size: 26px;
        }}
        .subtitle {{
            color: var(--text-muted);
            font-size: 14px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .metric-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .metric-card .title {{
            font-size: 12px;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.5px;
        }}
        .metric-card .value {{
            font-size: 22px;
            font-weight: 700;
            color: var(--text-main);
            margin-top: 6px;
        }}
        .table-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            text-align: left;
        }}
        th {{
            background-color: #172033;
            color: var(--text-muted);
            padding: 12px 16px;
            font-weight: 600;
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        code {{
            background: #090d16;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: Consolas, monospace;
            font-size: 13px;
            color: #7dd3fc;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        .badge.vendor {{
            background: #1e3a8a;
            color: #bfdbfe;
        }}
        .badge.status-active {{
            background: #064e3b;
            color: #6ee7b7;
        }}
        footer {{
            margin-top: 30px;
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Local Network Discovery Report</h1>
            <div class="subtitle">Scanned with Python Network Scanner &bull; Author: Yash Kawade (PRN: 2125UCSM1118)</div>
        </header>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="title">Target Subnet</div>
                <div class="value">{self.target_subnet}</div>
            </div>
            <div class="metric-card">
                <div class="title">Active Hosts</div>
                <div class="value" style="color: var(--accent);">{len(self.hosts)}</div>
            </div>
            <div class="metric-card">
                <div class="title">Scan Duration</div>
                <div class="value">{self.elapsed_seconds:.2f}s</div>
            </div>
            <div class="metric-card">
                <div class="title">Scan Timestamp</div>
                <div class="value" style="font-size: 16px;">{self.timestamp.strftime('%Y-%m-%d %H:%M')}</div>
            </div>
        </div>

        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th>IP Address</th>
                        <th>MAC Address</th>
                        <th>Hostname</th>
                        <th>Hardware Vendor</th>
                        <th>Latency</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="6" style="text-align:center; padding: 20px;">No active hosts found</td></tr>'}
                </tbody>
            </table>
        </div>

        <footer>
            Network Models and Protocols (NPC) &bull; Yash Kawade &bull; Automated Network Discovery
        </footer>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[+] HTML Report saved to      : {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Python Network Scanner - Discover active hosts, MAC addresses, and generate network reports."
    )
    parser.add_argument(
        "-t", "--target",
        default="auto",
        help="Target IP or CIDR subnet (e.g. 192.168.1.0/24, 172.20.10.0/28). Defaults to auto-detecting active interface.",
    )
    parser.add_argument(
        "-n", "--threads",
        type=int,
        default=50,
        help="Number of concurrent worker threads (default: 50).",
    )
    parser.add_argument(
        "-w", "--timeout",
        type=float,
        default=1.0,
        help="Host timeout in seconds (default: 1.0).",
    )
    parser.add_argument(
        "-o", "--output",
        default="network_report",
        help="Base filename for generated reports (default: network_report).",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["all", "json", "csv", "md", "html", "none"],
        default="all",
        help="Report export format: all, json, csv, md, html, or none (default: all).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output during scanning.",
    )

    args = parser.parse_args()

    scanner = NetworkScanner(
        target=args.target,
        timeout=args.timeout,
        max_threads=args.threads,
        verbose=args.verbose,
    )

    hosts, elapsed = scanner.scan()
    reporter = ReportGenerator(scanner.target, hosts, elapsed)

    # Print live console table
    reporter.print_console_table()

    # Generate requested reports
    fmt = args.format.lower()
    base_name = args.output

    if fmt in ("all", "json"):
        reporter.export_json(f"{base_name}.json")
    if fmt in ("all", "csv"):
        reporter.export_csv(f"{base_name}.csv")
    if fmt in ("all", "md"):
        reporter.export_markdown(f"{base_name}.md")
    if fmt in ("all", "html"):
        reporter.export_html(f"{base_name}.html")


if __name__ == "__main__":
    main()
