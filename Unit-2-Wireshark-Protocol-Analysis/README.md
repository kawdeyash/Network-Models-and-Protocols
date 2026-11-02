# NPC Assignment 2: Protocol Analysis with Wireshark

**Course / Module:** Unit 2: Network Models and Protocols  
**Author:** Yash Kawade  
**PRN:** 2125UCSM1118  
**Repository:** [Network-Models-and-Protocols](https://github.com/kawdeyash/Network-Models-and-Protocols)  

---

## 1. Aim
To capture and analyze network packets using Wireshark, identify the TCP three-way handshake (`SYN`, `SYN-ACK`, `ACK`), and observe the subsequent HTTP `GET` request and response.

---

## 2. Software & Environment Requirements
- **Operating System:** Kali Linux
- **Network Analyzer:** Wireshark (v4.x)
- **Web Browser:** Mozilla Firefox
- **Active Network Interface:** `eth0`
- **Target URL:** `http://neverssl.com`

---

## 3. Procedure
1. Open Wireshark in Kali Linux and select the active network interface (`eth0`).
2. Start packet capture.
3. Open a browser and navigate to `http://neverssl.com`.
4. Wait for the webpage to load, then stop the packet capture.
5. Apply the display filter `http` to locate HTTP traffic.
6. Identify the HTTP `GET` request and its corresponding TCP stream (`tcp.stream eq 7`).
7. Analyze the TCP three-way handshake: `SYN`, `SYN-ACK`, and `ACK`.
8. Record IP addresses, TCP ports, and sequence/acknowledgment numbers.
9. Export the packet capture to `.pcapng` format and document findings.

---

## 4. Observations & Packet Analysis

### TCP Three-Way Handshake
The captured TCP connection establishes a reliable connection prior to HTTP data exchange:

| Packet | Packet No. | Source IP | Source Port | Destination IP | Destination Port | Flags / Description |
|---|---|---|---|---|---|---|
| **SYN** | 87 | `192.168.17.130` | 34078 | `34.223.124.45` | 80 | Connection initiation |
| **SYN-ACK** | 103 | `34.223.124.45` | 80 | `192.168.17.130` | 34078 | Acknowledgment + SYN from server |
| **ACK** | 104 | `192.168.17.130` | 34078 | `34.223.124.45` | 80 | Connection established |

### HTTP GET Request & Response
Following handshake completion, client transmits an HTTP GET request:

| Packet | Packet No. | Source IP | Source Port | Destination IP | Destination Port | Protocol / Info |
|---|---|---|---|---|---|---|
| **HTTP GET** | 105 | `192.168.17.130` | 34078 | `34.223.124.45` | 80 | `GET / HTTP/1.1` |
| **HTTP 200 OK** | 108 | `34.223.124.45` | 80 | `192.168.17.130` | 34078 | `HTTP/1.1 200 OK (text/html)` |

---

## 5. Transport Layer Analysis
- **Protocol:** Transmission Control Protocol (TCP)
- **Client Ephemeral Port:** `34078`
- **Server Port:** `80` (Standard HTTP Port)
- **Mechanism:** Strict sequence tracking and handshake guarantee reliable byte-stream delivery before application layer protocol (HTTP) payload transfer.

---

## 6. Screenshots

### Figure 1: TCP Three-Way Handshake & HTTP GET Packet (`tcp.stream == 7`)
Packets 87 (SYN), 103 (SYN-ACK), 104 (ACK), and 105 (HTTP GET):
![Figure 1: TCP Three-Way Handshake](./screenshots/Figure_1_TCP_Handshake.png)

### Figure 2: HTTP GET Request & HTTP 200 OK Response (`http` filter)
Filter displaying HTTP GET request and 200 OK response:
![Figure 2: HTTP Traffic](./screenshots/Figure_2_HTTP_Traffic.png)

---

## 7. Repository Structure
```text
Protocol-Analysis-with-Wireshark/
│
├── screenshots/
│   ├── Figure_1_TCP_Handshake.png
│   └── Figure_2_HTTP_Traffic.png
│
├── protocol_analysis.pcapng
├── Protocol_Analysis_with_Wireshark_Report.docx
├── Protocol_Analysis_with_Wireshark_Report.pdf
└── README.md
```

| File / Folder | Purpose |
|---|---|
| `screenshots/` | Captured Wireshark verification screenshots |
| `protocol_analysis.pcapng` | Raw Wireshark packet capture file |
| `Protocol_Analysis_with_Wireshark_Report.pdf` | Final lab report in PDF format |
| `Protocol_Analysis_with_Wireshark_Report.docx` | Editable lab report in Word format |
| `README.md` | Project documentation and protocol analysis summary |

