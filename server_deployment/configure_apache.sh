#!/bin/bash

if ! dpkg -l | grep -q apache2; then
    echo "apache2 is not installed. Installing apache2..."
    
    # Install apache2
    sudo apt-get install -y apache2
    
    echo "apache2 has been installed."
else
    echo "apache2 is already installed."
fi

source ./setup_variables.sh

CONF_FILE="/etc/apache2/sites-available/$DOMAIN.conf"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
DEFAULT_CONF="/etc/apache2/sites-available/000-default.conf"

# Create the virtual host configuration
echo "Creating Apache virtual host configuration for $DOMAIN..."

# Remove default configuration if it exists
if [ -f "$DEFAULT_CONF" ]; then
    echo "Removing default Apache configuration..."
    sudo a2dissite 000-default.conf
    sudo rm "$DEFAULT_CONF"
fi

# Check if SSL certificate files exist
if [ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ]; then
    echo "SSL certificates found. Creating HTTPS configuration..."
    sudo tee "$CONF_FILE" > /dev/null << EOL
<VirtualHost *:443>
    ServerName $DOMAIN

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile $CERT_DIR/fullchain.pem
    SSLCertificateKeyFile $CERT_DIR/privkey.pem

    # Reverse Proxy Configuration
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # CORS Headers
    Header set Access-Control-Allow-Origin "*"
    Header set Access-Control-Allow-Methods "GET, POST, OPTIONS"
    Header set Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization, X-Request-With"
    Header set Access-Control-Allow-Credentials "true"

    # Logging
    ErrorLog \${APACHE_LOG_DIR}/$DOMAIN_error.log
    CustomLog \${APACHE_LOG_DIR}/$DOMAIN_access.log combined
</VirtualHost>

<VirtualHost *:80>
    ServerName $DOMAIN
    ServerAlias www.$DOMAIN
    # Redirect HTTP to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}\$1 [R=301,L]
</VirtualHost>
EOL
else
    echo "SSL certificates not found. Creating HTTP-only configuration..."
    sudo tee "$CONF_FILE" > /dev/null << EOL
<VirtualHost *:80>
    ServerName $DOMAIN
    ServerAlias www.$DOMAIN

    # Reverse Proxy Configuration
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # CORS Headers
    Header set Access-Control-Allow-Origin "*"
    Header set Access-Control-Allow-Methods "GET, POST, OPTIONS"
    Header set Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization, X-Request-With"
    Header set Access-Control-Allow-Credentials "true"

    # Logging
    ErrorLog \${APACHE_LOG_DIR}/$DOMAIN_error.log
    CustomLog \${APACHE_LOG_DIR}/$DOMAIN_access.log combined
</VirtualHost>
EOL
fi

# Enable the new site configuration
echo "Enabling the $DOMAIN site configuration..."
sudo a2ensite "$DOMAIN.conf"

# Reload Apache to apply changes
echo "Reloading Apache to apply the new configuration..."
sudo systemctl reload apache2

echo "Apache configuration for $DOMAIN has been set up."
