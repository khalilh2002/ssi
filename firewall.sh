#!/bin/bash

# ====================================================
# SCRIPT PARE-FEU - INFRASTRUCTURE SECURISEE
# ====================================================

# -- Definitions des Variables --
ADMIN_IP="10.0.0.20"
WEB_IP="10.0.1.10"
LAN_NET="10.0.2.0/24"
DMZ_NET="10.0.1.0/24"
VPN_PORT="1194"

echo "[*] Initialisation des parametres noyau..."
# Activation IP Forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
# Desactivation RP_Filter (Necessaire pour VIP/HA)
sysctl -w net.ipv4.conf.all.rp_filter=0 > /dev/null
sysctl -w net.ipv4.conf.default.rp_filter=0 > /dev/null

echo "[*] Nettoyage des tables existantes..."
iptables -F
iptables -X
iptables -Z

# -- Politiques par Defaut (DROP) --
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

echo "[*] Application des regles de base..."
# 1. Autoriser Loopback et protocoles de gestion (VRRP, Multicast)
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -p vrrp -j ACCEPT
iptables -A INPUT -d 224.0.0.18 -j ACCEPT

# 2. Autoriser ICMP (Ping) pour diagnostic
iptables -A INPUT -p icmp -j ACCEPT
iptables -A FORWARD -p icmp -j ACCEPT

# 3. Statefulness (Accepter le trafic deja etabli)
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

echo "[*] Configuration Acces VPN..."
# 4. Autoriser Tunneling OpenVPN (Depuis Admin WAN)
iptables -A INPUT -p udp --dport $VPN_PORT -s $ADMIN_IP -j ACCEPT

# 5. Routage VPN (Interface tun+)
# VPN -> Zones Internes
iptables -A FORWARD -i tun+ -o fw+-eth1 -j ACCEPT
iptables -A FORWARD -i tun+ -o fw+-eth2 -j ACCEPT
# Zones Internes -> VPN
iptables -A FORWARD -i fw+-eth1 -o tun+ -j ACCEPT
iptables -A FORWARD -i fw+-eth2 -o tun+ -j ACCEPT

echo "[*] Application des regles de filtrage (ZPF)..."
# 6. Regles Specifiques Zones
# WAN -> DMZ (HTTP/HTTPS uniquement)
iptables -A FORWARD -i fw+ -d $WEB_IP -p tcp --dport 80 -j ACCEPT
iptables -A FORWARD -i fw+ -d $WEB_IP -p tcp --dport 443 -j ACCEPT

# Admin -> DMZ (SSH pour maintenance)
iptables -A FORWARD -i fw+ -s $ADMIN_IP -d $WEB_IP -p tcp --dport 22 -j ACCEPT

# LAN -> DMZ (Acces Interne)
iptables -A FORWARD -s $LAN_NET -d $DMZ_NET -j ACCEPT

# -- Logging et Finalisation --
# Tout ce qui n'est pas autorise est loggue avant d'etre drop par la policy default
iptables -A FORWARD -j LOG --log-prefix "[SEC_BLOCK]: " --log-level 4

echo "[OK] Pare-feu configure avec succes."
