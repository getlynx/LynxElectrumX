#!/bin/bash
# certbot --pre-hook: let the HTTP-01 challenge through the Spark firewall.
# Certbot stores this hook in the renewal config, so renewals use it too.
exec /usr/local/sbin/lynx-electrumx-firewall open-http
