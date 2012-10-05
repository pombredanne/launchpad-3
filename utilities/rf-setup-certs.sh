#!/bin/sh

PASS='launchpad'

# -extensions v3_ca

# Create a conf listing all the domains the cert is valid for.

cat << EOF > /tmp/launchpad-req.conf
[ req ]
default_bits=1024
default_keyfile=privkey.pem
prompt=no
distinguished_name=req_distinguished_name
attributes=req_attributes
output_password=$PASS
x509_extensions=v3_ca

[ req_distinguished_name ]
C=UK
ST=test-place
L=test-city
O=launchpad.dev
OU=launchpad
CN=launchpad.dev
emailAddress=test@eg.dom

[ req_attributes ]
challengePassword=A challenge password

[ v3_ca ]
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer
basicConstraints=CA:true
EOF

cat << EOF > /tmp/launchpad-x509.conf
subjectAltName=DNS:launchpad.dev,DNS:*.launchpad.dev,DNS:testopenid.dev
EOF

# Generate a Private Key
openssl genrsa -passout pass:$PASS -des3 -out launchpad.key 1024
# Generate a CSR (Certificate Signing Request)
openssl req -passin pass:$PASS -config /tmp/launchpad-req.conf -new -key launchpad.key -out launchpad.csr
# Remove Passphrase from Key
cp launchpad.key launchpad.key.org
openssl rsa -passin pass:$PASS -in launchpad.key.org -out launchpad.key
# Generating a Self-Signed Certificate
openssl x509 -passin pass:$PASS -extfile /tmp/launchpad-x509.conf -req -days 3650 -in launchpad.csr -signkey launchpad.key -out launchpad.crt
#  Installing the Private Key and Certificate
sudo cp launchpad.crt /etc/apache2/ssl
sudo cp launchpad.key /etc/apache2/ssl
sudo service apache2 restart
# Add the cert to the local db.
certutil -d sql:$HOME/.pki/nssdb -D -n 'launchpad.dev'
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n 'launchpad.dev' -i /etc/apache2/ssl/launchpad.crt

# cleanup
rm /tmp/launchpad-req.conf
rm /tmp/launchpad-x509.conf
