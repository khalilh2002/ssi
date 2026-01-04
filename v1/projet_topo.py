#!/usr/bin/python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.cli import CLI
from mininet.log import setLogLevel
import time
import os
import sys
from AutoValidator import SecurityAuditor

# --- Definition de la Topologie ---
class SecuredZoneTopo(Topo):
    def build(self):
        sw_wan = self.addSwitch('s1', dpid='1')
        sw_dmz = self.addSwitch('s2', dpid='2')
        sw_lan = self.addSwitch('s3', dpid='3')

        attacker = self.addHost('attacker', ip='10.0.0.10/24')
        admin = self.addHost('admin', ip='10.0.0.20/24')
        web_srv = self.addHost('web1', ip='10.0.1.10/24')
        int_srv = self.addHost('internal', ip='10.0.2.10/24')

        fw_primary = self.addHost('fw1', ip='10.0.0.2/24')
        fw_backup = self.addHost('fw2', ip='10.0.0.3/24')

        for firewall in [fw_primary, fw_backup]:
            self.addLink(firewall, sw_wan)
            self.addLink(firewall, sw_dmz)
            self.addLink(firewall, sw_lan)

        self.addLink(attacker, sw_wan)
        self.addLink(admin, sw_wan)
        self.addLink(web_srv, sw_dmz)
        self.addLink(int_srv, sw_lan)

# --- Fonctions Utilitaires ---

def clean_environment():
    print("--- [SYS] Purge de l'environnement precedent ---")
    os.system("mn -c > /dev/null 2>&1")
    os.system('pkill -9 -f "keepalived|snort|nginx|openvpn"')
    os.system('rm -f /run/keepalived*.pid /run/vrrp*.pid')

def bootstrap_network(net):
    print("--- [NET] Configuration des Interfaces et Routes ---")
    fw1, fw2 = net.get('fw1', 'fw2')
    
    # Config Firewalls
    for fw, suffix in [(fw1, '2'), (fw2, '3')]:
        fw.cmd(f'ifconfig {fw.name}-eth1 10.0.1.{suffix} netmask 255.255.255.0')
        fw.cmd(f'ifconfig {fw.name}-eth2 10.0.2.{suffix} netmask 255.255.255.0')
        fw.cmd('chmod +x /home/server/firewall.sh')
        fw.cmd('/home/server/firewall.sh')

    # Routes par defaut
    net.get('attacker').cmd('ip route add default via 10.0.0.1')
    net.get('admin').cmd('ip route add default via 10.0.0.1')
    net.get('web1').cmd('ip route add default via 10.0.1.1')
    net.get('internal').cmd('ip route add default via 10.0.2.1')

def start_security_stack(net):
    print("--- [SEC] Demarrage de la Stack Securite ---")
    fw1, fw2 = net.get('fw1', 'fw2')
    web1 = net.get('web1')

    # 1. HA Cluster
    print("    > Cluster HA (Keepalived)...")
    fw1.cmd('keepalived -f /home/server/keepalived_fw1.conf -p /run/keepalived_fw1.pid -D')
    fw2.cmd('keepalived -f /home/server/keepalived_fw2.conf -p /run/keepalived_fw2.pid -D')
    time.sleep(3)
    
    # --- FAIL-SAFE: FORCER LES IPS SI KEEPALIVED CRASH ---
    # On verifie si l'IP WAN (10.0.0.1) est presente
    chk = fw1.cmd("ip addr show fw1-eth0")
    if "10.0.0.1" not in chk:
        print(f"    ! ALERTE: Keepalived echec. ACTIVATION MODE SECOURS (Manual VIPs).")
        
        # 1. Ajout VIP WAN (Pour Attacker -> FW)
        fw1.cmd("ip addr add 10.0.0.1/24 dev fw1-eth0")
        
        # 2. Ajout VIP DMZ (Pour Web1 -> FW) -> CORRIGE VOTRE ERREUR WEB
        fw1.cmd("ip addr add 10.0.1.1/24 dev fw1-eth1")
        
        # 3. Ajout VIP LAN (Pour Internal -> FW)
        fw1.cmd("ip addr add 10.0.2.1/24 dev fw1-eth2")
    else:
        print("    > Keepalived demarre avec succes (VIPs automatiques).")

    # 2. Services Web
    print("    > Serveur Web & SSH...")
    os.system('service nginx stop')
    web1.cmd('nginx > /dev/null 2>&1 &')
    web1.cmd('/usr/sbin/sshd -f /home/server/sshd_config_secure > /dev/null 2>&1 &')

    # 3. IDS & VPN
    print("    > IDS Snort & OpenVPN...")
    fw1.cmd('snort -q -c /etc/snort/snort.conf -i fw1-eth0 -D')
    time.sleep(1)
    fw1.cmd('openvpn --config /home/server/openvpn_server.conf --daemon')
    fw2.cmd('openvpn --config /home/server/openvpn_server.conf --daemon')
def show_dashboard(net):
    print("\n" + "="*40)
    print("   ETAT DU SYSTEME")
    print("="*40)
    attacker = net.get('attacker')
    
    ping_vip = "ONLINE" if "1 received" in attacker.cmd("ping -c 1 -W 1 10.0.0.1") else "OFFLINE"
    http_chk = "ONLINE" if "200" in attacker.cmd("curl -k -I -m 2 https://10.0.1.10") else "ERROR"
    
    print(f" GATEWAY VIP : [{ping_vip}]")
    print(f" SERVICE WEB : [{http_chk}]")
    print("="*40 + "\n")

if __name__ == '__main__':
    setLogLevel('info')
    clean_environment()
    topo = SecuredZoneTopo()
    net = Mininet(topo=topo, controller=OVSController)
    
    try:
        net.start()
        bootstrap_network(net)
        start_security_stack(net)
        show_dashboard(net)
        
        auditor = SecurityAuditor(net)
        auditor.run_full_audit()
        
        print("\n[INFO] Console Mininet prete. Tapez 'exit' pour quitter.")
        CLI(net)
        
    finally:
        print("\n--- [SHUTDOWN] Arret de la simulation ---")
        os.system('pkill -9 -f "keepalived|snort|nginx"')
        net.stop()
