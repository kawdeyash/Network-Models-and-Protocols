# Python Network Scanner

**Course:** Network Models and Protocols / Networking Protocols & Communication (NPC)  
**Author:** Yash Kawade  
**PRN:** 2125UCSM1118  
**Department:** Cyber Security  
**Institution:** Sanjivani University, Kopargaon  
**Repository:** [Network-Models-and-Protocols](https://github.com/kawdeyash/Network-Models-and-Protocols)

---

## 1. Project Overview

The **Python Network Scanner** is a fast, multi-threaded command-line tool built to perform automated local area network discovery and host reconnaissance. It scans target IP subnets, resolves physical MAC addresses, identifies active hosts, determines hardware vendors via OUI prefix lookup, and generates comprehensive reports.

---

## 2. Key Features

- **Local Network Discovery:** Auto-detects the active network interface and subnet, or accepts custom CIDR notation (e.g., `192.168.1.0/24`, `172.20.10.0/28`).
- **IP & MAC Address Resolution:**
  - **Native Win32 ARP (`SendARP`):** Leverages Windows `iphlpapi.dll` for rapid Layer-2 ARP queries directly through the OS network stack with zero external dependencies (no Npcap/WinPcap required).
  - **Cross-Platform ARP Cache Inspection:** Seamless fallback for Linux and macOS.
- **Active Host Identification:** Combines ICMP ping sweeps and ARP probes to distinguish active hosts from inactive addresses with millisecond round-trip time (RTT) measurements.
- **Hostname & Hardware Vendor Lookup:**
  - Reverse DNS hostname resolution (`socket.gethostbyaddr`).
  - Built-in IEEE OUI MAC prefix database to identify device manufacturers (Apple, Cisco, Intel, Samsung, TP-Link, Raspberry Pi, etc.).
- **Multi-Format Network Reports:** Automatically exports network discovery reports in **JSON**, **CSV**, **Markdown**, and modern responsive **HTML**.

---

## 3. Installation & Requirements

### Requirements
- **Python 3.8+** (Standard Library only — no `pip install` required for core functionality!)
- Compatible with Windows 10/11, Linux, and macOS.

```bash
# Verify Python installation
python --version
```

---

## 4. Usage Guide

### Basic Scan (Auto-Detect Local Subnet)
```bash
python network_scanner.py
```

### Scan Specific Subnet (CIDR)
```bash
python network_scanner.py --target 192.168.1.0/24
```

### Scan with Custom Concurrency & Timeout
```bash
python network_scanner.py --target 172.20.10.0/28 --threads 50 --timeout 0.8
```

### Export to Specific Format
```bash
# Export only Markdown and JSON reports
python network_scanner.py --target 192.168.1.0/24 --format md --output my_network_report
```

### CLI Command Options
| Flag | Name | Default | Description |
|---|---|---|---|
| `-t` | `--target` | `auto` | Target IP or CIDR subnet (e.g., `192.168.1.0/24`) |
| `-n` | `--threads` | `50` | Number of concurrent worker threads |
| `-w` | `--timeout` | `1.0` | Timeout per host probe (in seconds) |
| `-o` | `--output` | `network_report` | Base filename for output reports |
| `-f` | `--format` | `all` | Report export format (`all`, `json`, `csv`, `md`, `html`, `none`) |
| `-v` | `--verbose` | `False` | Enable verbose scanning logs |

---

## 5. Sample Terminal Output

```text
========================================================================
          PYTHON NETWORK SCANNER (Host & MAC Discovery)          
========================================================================
[*] Target Subnet    : 172.20.10.0/28
[*] Total Addresses  : 14
[*] Concurrency      : 50 worker threads
[*] Timeout per host : 1.0s
[*] Scan Started     : 2026-11-02 21:07:45
------------------------------------------------------------------------
[*] Sweeping network via multi-threaded ARP & ICMP probes...
[+] Scan completed in 5.18 seconds.
[+] Discovered 2 active host(s) on 172.20.10.0/28.

+-----------------+-------------------+--------------------------+----------------------------+-----------+
| IP Address      | MAC Address       | Hostname                 | Vendor / Manufacturer      | Latency   |
+=================+===================+==========================+============================+===========+
| 172.20.10.1     | 56:32:C7:17:DC:64 | N/A                      | Apple, Inc. (Private/Rando | 2.0 ms    |
| 172.20.10.2     | 48:45:E6:D4:7F:49 | YASHUU-PC                | Unidentified Vendor        | 1.0 ms    |
+-----------------+-------------------+--------------------------+----------------------------+-----------+
[+] JSON Report saved to      : network_report.json
[+] CSV Report saved to       : network_report.csv
[+] Markdown Report saved to  : network_report.md
[+] HTML Report saved to      : network_report.html
```

---

## 6. Generated Reports

- [`network_report.json`](network_report.json): Structured JSON payload for automated pipelines.
- [`network_report.csv`](network_report.csv): Tabular spreadsheet format.
- [`network_report.md`](network_report.md): GitHub-ready Markdown summary.
- [`network_report.html`](network_report.html): Interactive visual dashboard with card metrics and responsive table.
