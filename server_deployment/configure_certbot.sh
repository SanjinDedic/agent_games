#!/bin/bash

source ./setup_variables.sh

APACHE_CONF="/etc/apache2/sites-available/$DOMAIN.conf"
CERTBOT_PATH="/usr/bin/certbot"


# Install certbot if not installed
if ! [ -x "$(command -v certbot)" ]; then
    echo "cerbot is not installed. Installing certbot..."
    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot
fi

sudo certbot certonly --apache -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m $EMAIL

# Check if the SSL certificate was successfully obtained
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ] && [ -f "/etc/letsencrypt/live/$DOMAIN/privkey.pem" ]; then
    echo "SSL certificate successfully obtained for $DOMAIN."
else
    echo "Failed to obtain SSL certificate for $DOMAIN."
    exit 1
fi


echo "Cerificates Setup complete for $DOMAIN."
