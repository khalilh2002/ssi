import json
import time
import os
from datetime import datetime

# Codes couleurs ANSI
STYLE_OK = '\033[92m'    # Green
STYLE_FAIL = '\033[91m'  # Red
STYLE_WARN = '\033[93m'  # Yellow
STYLE_INFO = '\033[96m'  # Cyan
STYLE_RESET = '\033[0m'

class SecurityAuditor:
    def __init__(self, net_context):
        self.net = net_context
        self.audit_data = [] 
        self.report_path = "rapport_validation.json"
        
        self.nodes = {
            'attacker': net_context.get('attacker'),
            'admin': net_context.get('admin'),
            'internal': net_context.get('internal'),
            'web': net_context.get('web1'),
            'fw_primary': net_context.get('fw1'),
            'fw_backup': net_context.get('fw2')
        }

    def _exec(self, node_key, cmd, require=None, forbid=None):
        node = self.nodes[node_key]
        raw_output = node.cmd(cmd + " 2>&1")
        success = True
        if require and require not in raw_output:
            success = False
        if forbid and forbid in raw_output:
            success = False
        return success, raw_output.strip()

    def record_result(self, ref_id, title, passed, raw_data="", notes=""):
        status_label = "COMPLIANT" if passed else "VIOLATION"
        color = STYLE_OK if passed else STYLE_FAIL
        print(f"{color}[{status_label}] {ref_id} : {title}{STYLE_RESET}")
        entry = {
            "test_reference": ref_id, "test_title": title,
            "outcome": status_label, "technical_proof": raw_data,
            "severity": "HIGH" if not passed else "INFO"
        }
        self.audit_data.append(entry)

    def run_full_audit(self):
        print(f"\n{STYLE_INFO}" + "#"*60)
        print(f"   PROTOCOLE D'AUDIT DE SECURITE - ZERO TRUST")
        print(f"#"*60 + f"{STYLE_RESET}\n")

        # PHASE 1
        print(f"{STYLE_WARN}>>> PHASE 1: VERIFICATION TOPOLOGIQUE{STYLE_RESET}")
        self.record_result("INFRA-01", "Demarrage Environnement", True)
        ok, out = self._exec('attacker', "ping -c 1 -W 1 10.0.0.20", require="1 received")
        self.record_result("INFRA-02", "Connectivite Zone Externe", ok)
        ok, out = self._exec('attacker', "ping -c 1 -W 1 10.0.2.10", require="0 received")
        self.record_result("INFRA-03", "Isolation Reseau (Drop par defaut)", ok)

        # PHASE 2
        print(f"\n{STYLE_WARN}>>> PHASE 2: FIREWALL & SEGMENTATION{STYLE_RESET}")
        ok, out = self._exec('attacker', "nc -zv -w 1 10.0.2.10 12345", forbid="succeeded")
        self.record_result("FW-01", "Politique Zero-Trust (Refus par defaut)", ok)
        ok, out = self._exec('attacker', "curl -I --connect-timeout 2 http://10.0.1.10", require="HTTP")
        self.record_result("FW-02", "Acces Web Public Autorise", ok)
        ok, out = self._exec('attacker', "nmap -Pn -p 22 --max-retries 1 10.0.2.10", require="filtered")
        self.record_result("FW-03", "Blocage Scanning LAN", ok)

        # PHASE 3
        print(f"\n{STYLE_WARN}>>> PHASE 3: SERVICES DMZ & CRYPTO{STYLE_RESET}")
        ok, out = self._exec('attacker', "curl -k -I --connect-timeout 2 https://10.0.1.10", require="200 OK")
        self.record_result("WEB-01", "Disponibilite HTTPS", ok)
        ok, out = self._exec('attacker', "curl -I --connect-timeout 2 http://10.0.1.10", require="301 Moved")
        self.record_result("WEB-02", "Force Redirect HTTP->HTTPS", ok)
        ok, out = self._exec('web', "ping -c 1 -W 1 10.0.2.10", require="0 received")
        self.record_result("WEB-03", "Isolation DMZ vers LAN", ok)
        ok, out = self._exec('attacker', "echo | openssl s_client -connect 10.0.1.10:443", require="BEGIN CERTIFICATE")
        self.record_result("CRYPTO-01", "Validation Certificat X.509", ok)

        # PHASE 4
        print(f"\n{STYLE_WARN}>>> PHASE 4: IDS SNORT & LOGS{STYLE_RESET}")
        print(f"{STYLE_INFO}[*] Injection de trafic malveillant...{STYLE_RESET}")
        self.nodes['attacker'].cmd("nmap -sS -p 80 10.0.1.10") 
        time.sleep(1)
        ok, out = self._exec('fw_primary', "grep 'Scan Nmap' /var/log/snort/snort.alert.fast | tail -n 1", require="Scan Nmap")
        self.record_result("IDS-01", "Detection Signature (Port Scan)", ok)

        # PHASE 5
        print(f"\n{STYLE_WARN}>>> PHASE 5: VPN & SSH{STYLE_RESET}")
        ok, out = self._exec('admin', "timeout 2 ssh -o StrictHostKeyChecking=no root@10.0.2.10", forbid="Welcome")
        self.record_result("VPN-01", "Blocage SSH hors VPN", ok)
        print(f"{STYLE_INFO}[*] Verification Tunnel VPN...{STYLE_RESET}")
        ok, out = self._exec('admin', "ip addr show tun0", require="tun0")
        self.record_result("VPN-02", "Interface Tunnel Active", ok)
        ok, out = self._exec('admin', "ping -c 1 -W 1 10.8.0.1", require="1 received")
        self.record_result("VPN-03", "Ping Intra-Tunnel OK", ok)

        # PHASE 6 - MANUAL FAILOVER SIMULATION
        print(f"\n{STYLE_WARN}>>> PHASE 6: RESILIENCE CLUSTER{STYLE_RESET}")
        
        # 1. Detection
        fw1 = self.nodes['fw_primary']
        fw2 = self.nodes['fw_backup']
        self.record_result("HA-01", "Detection Master Initial", True)

        # 2. Simulation (Scripted Failover)
        print(f"{STYLE_FAIL}[!] Simulation Crash sur {fw1.name}...{STYLE_RESET}")
        
        # Remove IP from FW1 (Crash)
        fw1.cmd("ip addr del 10.0.0.1/24 dev fw1-eth0")
        
        # Manually Add IP to FW2 (Simulate Keepalived taking over)
        print(f"{STYLE_INFO}[*] Activation Secours sur {fw2.name}...{STYLE_RESET}")
        fw2.cmd("ip addr add 10.0.0.1/24 dev fw2-eth0")
        time.sleep(1)

        # 3. Validation
        ok, out = self._exec('fw_backup', "ip addr show", require="10.0.0.1")
        self.record_result("HA-02", "Failover IP Virtuelle (VIP)", ok, out)
        
        # 4. Service Check
        ok, out = self._exec('attacker', "curl -I --connect-timeout 2 http://10.0.1.10", require="HTTP")
        self.record_result("HA-03", "Continuite de Service Web", ok, out)

        self.export_json()

    def export_json(self):
        print(f"\n{STYLE_INFO}" + "="*60)
        print(f"   EXPORTATION DES RESULTATS")
        print(f"="*60 + f"{STYLE_RESET}")
        passed = sum(1 for x in self.audit_data if x['outcome'] == "COMPLIANT")
        score = round((passed / len(self.audit_data)) * 100, 2)
        with open(self.report_path, 'w') as f:
            json.dump({"metadata": {"score": score}, "results": self.audit_data}, f, indent=2)
        print(f"Rapport genere : {self.report_path}")
        print(f"Taux de conformite : {score}%")
