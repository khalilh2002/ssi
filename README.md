# Network Security Project – Run Guide

This repository contains a **network security / infrastructure topology** including firewall rules, OpenVPN, Keepalived (HA), SSH hardening, Snort IDS, and validation scripts.

The **main entry point** of the project is:

```
main_topo
```

⚠️ **Important**: `main_topo` **must be located in `/home/server/`** to run correctly.

---

## 1. Prerequisites

### System

* Linux (tested on Arch / Ubuntu)
* Root or sudo access

### Required packages (minimum)

Make sure the following are installed:

* Python 3.10+
* OpenVPN
* iptables
* keepalived
* snort
* openssh
* iproute2
* bridge-utils (if using virtual bridges)

Example (Debian/Ubuntu):

```bash
sudo apt update
sudo apt install -y python3 openvpn iptables keepalived snort openssh-server iproute2 bridge-utils
```

Example (Arch):

```bash
sudo pacman -S python openvpn iptables keepalived snort openssh iproute2 bridge-utils
```

---

## 2. Project Placement (MANDATORY)

Move the project to `/home/server`:

```bash
sudo mkdir -p /home/server
sudo cp -r ./final\ \(2\)/* /home/server/
cd /home/server
```

Ensure permissions:

```bash
sudo chown -R root:root /home/server
```

---

## 3. File Structure Overview

Key components:

* `main_topo` → **MAIN FILE (entry point)**
* `firewall.sh` → iptables firewall rules
* `fix_all.sh` → global fix / setup script
* `apply_final_fix.sh` → final corrections
* `fix_configs.sh` → deploy secure configurations
* `fix_multicast.sh` → multicast fixes (Keepalived)
* `AutoValidator.py` → automatic validation

Configs directory:

* `Configs/Keepalived/` → HA configuration
* `Configs/openvpn/` → OpenVPN server + PKI
* `Configs/SSH/` → hardened SSH config
* `Configs/snort/` → IDS rules
* `Configs/Web/` → web server configs

---

## 4. Make Scripts Executable

Before running anything:

```bash
sudo chmod +x *.sh
sudo chmod +x main_topo
```

---

## 5. Run Order (DO NOT SKIP)

### Step 1 – Apply base fixes

```bash
sudo ./fix_all.sh
```

### Step 2 – Apply configuration files

```bash
sudo ./fix_configs.sh
```

### Step 3 – Fix multicast (Keepalived requirement)

```bash
sudo ./fix_multicast.sh
```

### Step 4 – Apply final adjustments

```bash
sudo ./apply_final_fix.sh
```

---

## 6. Run the Main Topology

This is the **core execution step**:

```bash
sudo ./main_topo
```

This will:

* Deploy the network topology
* Apply firewall rules
* Enable HA (Keepalived)
* Configure OpenVPN
* Secure SSH
* Activate IDS rules
* **Automatically run all project tests and validations**

---

## 7. Validation

Run the automatic validator:

```bash
sudo python3 AutoValidator.py
```

Validation results will be written to:

```
rapport_validation.json
```

---

## 8. OpenVPN Client Access

Client configuration:

```
admin.ovpn
```

To connect:

```bash
sudo openvpn --config admin.ovpn
```

---

## 9. Common Issues / Warnings

* ❌ Running outside `/home/server` → **WILL FAIL**
* ❌ Missing root privileges → services won’t start
* ❌ Wrong permissions on PKI files → OpenVPN fails
* ❌ Multicast disabled → Keepalived won’t work

---

## 10. One-Line Summary

> Place the project in `/home/server`, make scripts executable, run the fix scripts **in order**, then execute `main_topo` as root.

---

## 11. Author / Context

This project is intended for **academic / TP validation** involving:

* Network security
* High availability
* VPN
* Firewalling
* IDS

Use strictly in controlled environments.
