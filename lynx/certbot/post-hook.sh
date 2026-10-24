#!/bin/bash
# certbot --post-hook: close tcp/80 again. Runs even if issuance failed.
exec /usr/local/sbin/lynx-electrumx-firewall close-http
