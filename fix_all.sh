#!/bin/bash

# --- 1. FIX KEEPALIVED (Remove Auth, Simplify) ---
echo "Repairing Keepalived Configs..."
cat > /home/server/keepalived_fw1.conf <<EOF
vrrp_instance VI_1 {
    state MASTER
    interface fw1-eth0
    virtual_router_id 51
    priority 150
    advert_int 1
    # Auth removed to prevent mismatch issues in simulation
    virtual_ipaddress {
        10.0.0.1
    }
}
EOF

cat > /home/server/keepalived_fw2.conf <<EOF
vrrp_instance VI_1 {
    state BACKUP
    interface fw2-eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    virtual_ipaddress {
        10.0.0.1
    }
}
EOF

# --- 2. FIX SNORT RULES (Add the missing rules) ---
echo "Repairing Snort Rules..."
sudo mkdir -p /etc/snort/rules
cat > /etc/snort/rules/local.rules <<EOF
# Regle pour detecter le scan Nmap (Flags SYN)
alert tcp any any -> any any (msg:"Scan Nmap"; flags:S; sid:1000001; rev:1;)
# Regle pour detecter le Ping
alert icmp any any -> any any (msg:"Ping Detecte"; sid:1000002; rev:1;)
# Regle pour tentative SSH
alert tcp any any -> any 22 (msg:"Tentative SSH"; flags:S; sid:1000003; rev:1;)
EOF

# Ensure Snort log dir exists
sudo mkdir -p /var/log/snort
sudo chmod 777 /var/log/snort

# --- 3. FIX FIREWALL SCRIPT (Prioritize VRRP) ---
echo "Repairing Firewall Script..."
cat > /home/server/firewall.sh <<EOF
#!/bin/bash
# Enable Forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
# Disable RP Filter (Critical for VIP)
for i in /proc/sys/net/ipv4/conf/*/rp_filter; do echo 0 > \$i; done

# Flush
iptables -F
iptables -X
iptables -Z

# Policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# --- CRITICAL: ALLOW VRRP (Keepalived) FIRST ---
iptables -A INPUT -p vrrp -j ACCEPT
iptables -A INPUT -d 224.0.0.0/8 -j ACCEPT
iptables -A INPUT -p icmp -j ACCEPT

# Allow Loopback
iptables -A INPUT -i lo -j ACCEPT

# --- VPN Access ---
# Allow connection TO the VPN server (UDP 1194)
iptables -A INPUT -p udp --dport 1194 -j ACCEPT
# Allow traffic inside the VPN tunnel (tun0)
iptables -A INPUT -i tun+ -j ACCEPT
iptables -A FORWARD -i tun+ -j ACCEPT
iptables -A FORWARD -o tun+ -j ACCEPT

# --- STATEFULNESS ---
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# --- ZONES ---
# WAN -> DMZ (Web)
iptables -A FORWARD -i fw+-eth0 -o fw+-eth1 -d 10.0.1.10 -p tcp --dport 80 -j ACCEPT
iptables -A FORWARD -i fw+-eth0 -o fw+-eth1 -d 10.0.1.10 -p tcp --dport 443 -j ACCEPT

# LAN -> DMZ
iptables -A FORWARD -i fw+-eth2 -o fw+-eth1 -j ACCEPT

# LOGGING (Log dropped packets for debugging)
iptables -A FORWARD -j LOG --log-prefix "FW_DROP: " --log-level 4
EOF
chmod +x /home/server/firewall.sh

echo "--- ALL FIXES APPLIED ---"
