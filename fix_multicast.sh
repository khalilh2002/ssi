#!/bin/bash

echo "--- 1. UPDATING FIREWALL SCRIPT WITH MULTICAST FIX ---"

cat > /home/server/firewall.sh <<EOF
#!/bin/bash
# 1. Enable Forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
for i in /proc/sys/net/ipv4/conf/*/rp_filter; do echo 0 > \$i; done

# 2. Flush Rules
iptables -F
iptables -X
iptables -Z

# 3. Default Policy
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# --- CRITICAL FIX: ADD MULTICAST ROUTE FOR KEEPALIVED ---
# This prevents "Network is unreachable" errors in VRRP
current_eth0=\$(ip addr show | grep 'inet 10.0.0' | awk '{print \$NF}')
if [ ! -z "\$current_eth0" ]; then
    ip route add 224.0.0.0/8 dev \$current_eth0 2>/dev/null
fi

# 4. Allow VRRP (Keepalived)
iptables -A INPUT -p vrrp -j ACCEPT
iptables -A INPUT -d 224.0.0.0/8 -j ACCEPT
iptables -A INPUT -p icmp -j ACCEPT
iptables -A FORWARD -p icmp -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT

# 5. VPN Access
iptables -A INPUT -p udp --dport 1194 -j ACCEPT
iptables -A INPUT -i tun+ -j ACCEPT
iptables -A FORWARD -i tun+ -j ACCEPT
iptables -A FORWARD -o tun+ -j ACCEPT

# 6. Statefulness
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# 7. WEB ACCESS (WAN -> DMZ)
# We accept traffic destined to the Web Server IP
iptables -A FORWARD -d 10.0.1.10 -p tcp --dport 80 -j ACCEPT
iptables -A FORWARD -d 10.0.1.10 -p tcp --dport 443 -j ACCEPT

# 8. LAN ACCESS
iptables -A FORWARD -s 10.0.2.0/24 -d 10.0.1.0/24 -j ACCEPT

# Log drops
iptables -A FORWARD -j LOG --log-prefix "FW_DROP: " --log-level 4
EOF

chmod +x /home/server/firewall.sh

echo "--- 2. RESETTING KEEPALIVED CONFIGS ---"

# FW1 Config
cat > /home/server/keepalived_fw1.conf <<EOF
vrrp_instance VI_1 {
    state MASTER
    interface fw1-eth0
    virtual_router_id 51
    priority 150
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass 1111
    }
    virtual_ipaddress {
        10.0.0.1
    }
}
EOF

# FW2 Config
cat > /home/server/keepalived_fw2.conf <<EOF
vrrp_instance VI_1 {
    state BACKUP
    interface fw2-eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass 1111
    }
    virtual_ipaddress {
        10.0.0.1
    }
}
EOF

echo "--- FIX APPLIED: You can now run sudo python3 projet_topo.py ---"
