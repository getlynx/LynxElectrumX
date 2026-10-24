#!/bin/bash
# certbot --deploy-hook: copy a new certificate to where ElectrumX reads it
# and restart ElectrumX, which only loads its certificate at startup.
# ElectrumX never reads /etc/letsencrypt, so that stays root-only.
#
# certbot sets RENEWED_LINEAGE (e.g. /etc/letsencrypt/live/<domain>).
# build.sh also runs this directly to install an existing certificate.
set -euo pipefail

TLS_DIR="/etc/electrumx/tls"
: "${RENEWED_LINEAGE:?RENEWED_LINEAGE not set}"

install -d -m 750 -o root -g electrumx "$TLS_DIR"
install -m 644 -o electrumx -g electrumx "$RENEWED_LINEAGE/fullchain.pem" "$TLS_DIR/fullchain.pem"
install -m 600 -o electrumx -g electrumx "$RENEWED_LINEAGE/privkey.pem" "$TLS_DIR/privkey.pem"
logger -t lynx-electrumx-certbot "installed certificate from $RENEWED_LINEAGE"

# try-restart does nothing if ElectrumX is not running yet (first install).
# build.sh sets LEX_NO_RESTART and restarts ElectrumX itself if needed.
if [ -z "${LEX_NO_RESTART:-}" ]; then
    systemctl try-restart electrumx.service
fi
