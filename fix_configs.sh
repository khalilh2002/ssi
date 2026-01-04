#!/bin/bash

echo "--- CORRECTION DES CONFIGURATIONS KEEPALIVED ---"

# 1. Correction FW1 (Interface fw1-eth0)
cat > /home/server/keepalived_fw1.conf <<EOF
vrrp_instance VI_1 {
    state MASTER
    interface fw1-eth0
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

# 2. Correction FW2 (Interface fw2-eth0)
cat > /home/server/keepalived_fw2.conf <<EOF
vrrp_instance VI_1 {
    state BACKUP
    interface fw2-eth0
    virtual_router_id 51
    priority 90
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

echo "--- CORRECTION DU SERVEUR WEB (NGINX) ---"

# 3. Création d'une config Nginx de base si elle n'existe pas
# On s'assure que le dossier existe
sudo mkdir -p /etc/nginx/sites-available
sudo mkdir -p /etc/nginx/sites-enabled

# On écrit une config simple qui force le HTTPS
cat > /etc/nginx/sites-available/default <<EOF
server {
    listen 80;
    server_name _;
    return 301 https://\$host\$request_uri;
}
server {
    listen 443 ssl;
    server_name _;
    ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
    ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;
    
    root /var/www/html;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF

# Activation du site
sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Page d'accueil par défaut
sudo mkdir -p /var/www/html
echo "<h1>SITE SECURISE LSI3</h1>" | sudo tee /var/www/html/index.html

# Redémarrage propre de Nginx
sudo service nginx restart

echo "--- CORRECTIONS TERMINEES ---"
