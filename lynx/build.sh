#!/bin/bash
# LynxElectrumX installer: turns a Debian 13 VPS running a synced Spark node
# (bash <(curl -sL install.getlynx.io)) into an ElectrumX server for that chain.
#
#   build.sh --chain lynx --domain electrum.example.com [options]
#
# Every option can also be set with the environment variable shown, so the
# script runs unattended. It only prompts for a missing --chain or --domain
# when a terminal is attached.
#
#   --chain NAME        LEX_CHAIN       chain profile in lynx/chains/ (required)
#   --domain HOST       LEX_DOMAIN      public hostname of this server (required)
#   --email ADDR        LEX_EMAIL       Let's Encrypt contact (default: domains@getlynx.io)
#   --tls MODE          LEX_TLS         certbot (default) or selfsigned (testing only)
#   --version REF       LEX_VERSION     LynxElectrumX tag to install (default: see below)
#   --db ENGINE         LEX_DB          leveldb (default) or rocksdb
#   --repo URL          LEX_REPO        LynxElectrumX git URL
#   --daemon-url URL    LEX_DAEMON_URL  node RPC URL; skips reading the node config
#   --force             LEX_FORCE=1     allow a system other than Debian 13
#   --follow-logs                       follow the ElectrumX log when done
#
# Re-running is safe and changes only what differs. To update, re-run with a
# newer --version. Log: /var/log/lynx-electrumx-build.log

set -euo pipefail
export LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive

DEFAULT_VERSION="v2.0.0-lynx.0"
DEFAULT_REPO="https://github.com/getlynx/LynxElectrumX.git"

PREFIX="/opt/lynx-electrumx"
SRC="$PREFIX/src"
VENV="$PREFIX/venv"
HOOK_DIR="/usr/local/lib/lynx-electrumx"
CONF="/etc/electrumx.conf"
TLS_DIR="/etc/electrumx/tls"
DB_DIRECTORY="/db"
LOG="/var/log/lynx-electrumx-build.log"

CHAIN="${LEX_CHAIN:-}"
DOMAIN="${LEX_DOMAIN:-}"
EMAIL="${LEX_EMAIL:-domains@getlynx.io}"
TLS="${LEX_TLS:-certbot}"
RELEASE="${LEX_VERSION:-$DEFAULT_VERSION}"
DB_ENGINE="${LEX_DB:-leveldb}"
REPO="${LEX_REPO:-$DEFAULT_REPO}"
DAEMON_URL="${LEX_DAEMON_URL:-}"
FORCE="${LEX_FORCE:-0}"
FOLLOW_LOGS=0

info() { echo "==> $*"; }
warn() { echo "WARNING: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

usage() {
    sed -n '2,/^$/s/^# \{0,1\}//p' "$0" 2>/dev/null || true
    exit "${1:-0}"
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --chain) CHAIN="${2:?--chain needs a value}"; shift ;;
            --domain) DOMAIN="${2:?--domain needs a value}"; shift ;;
            --email) EMAIL="${2:?--email needs a value}"; shift ;;
            --tls) TLS="${2:?--tls needs a value}"; shift ;;
            --version) RELEASE="${2:?--version needs a value}"; shift ;;
            --db) DB_ENGINE="${2:?--db needs a value}"; shift ;;
            --repo) REPO="${2:?--repo needs a value}"; shift ;;
            --daemon-url) DAEMON_URL="${2:?--daemon-url needs a value}"; shift ;;
            --force) FORCE=1 ;;
            --follow-logs) FOLLOW_LOGS=1 ;;
            -h|--help) usage 0 ;;
            *) echo "unknown option: $1" >&2; usage 2 ;;
        esac
        shift
    done

    if [ -z "$CHAIN" ] && [ -t 0 ]; then read -rp "Chain (e.g. lynx): " CHAIN; fi
    if [ -z "$DOMAIN" ] && [ -t 0 ]; then read -rp "Public hostname of this server: " DOMAIN; fi
    [ -n "$CHAIN" ] || die "--chain is required"
    [ -n "$DOMAIN" ] || die "--domain is required"
    CHAIN="${CHAIN,,}"
    case "$TLS" in certbot|selfsigned) ;; *) die "--tls must be certbot or selfsigned" ;; esac
    case "$DB_ENGINE" in leveldb|rocksdb) ;; *) die "--db must be leveldb or rocksdb" ;; esac
}

check_system() {
    [ "$(id -u)" -eq 0 ] || die "run as root"
    # Read os-release in a subshell: it defines VERSION, NAME and others that
    # would overwrite this script's own variables.
    local os_id os_version os_name
    os_id="$(. /etc/os-release && echo "${ID:-}")"
    os_version="$(. /etc/os-release && echo "${VERSION_ID:-}")"
    os_name="$(. /etc/os-release && echo "${PRETTY_NAME:-unknown}")"
    if [ "$os_id" != "debian" ] || [ "$os_version" != "13" ]; then
        [ "$FORCE" = 1 ] || die "this installer targets Debian 13; found $os_name (use --force to try anyway)"
        warn "not Debian 13 ($os_name); continuing because of --force"
    fi
    command -v systemctl >/dev/null || die "systemd is required"
}

install_packages() {
    local pkgs=(git ca-certificates curl openssl iproute2 bind9-dnsutils
                python3 python3-venv python3-dev build-essential pkg-config)
    if [ "$DB_ENGINE" = rocksdb ]; then
        pkgs+=(librocksdb-dev libsnappy-dev zlib1g-dev libbz2-dev liblz4-dev libzstd-dev)
    else
        pkgs+=(libleveldb-dev)
    fi
    if [ "$TLS" = certbot ]; then pkgs+=(certbot); fi
    info "Installing packages: ${pkgs[*]}"
    apt-get update -q
    apt-get install -yq --no-install-recommends "${pkgs[@]}"
}

# Check out $RELEASE (tag, branch or commit) in $SRC. Sets CODE_CHANGED.
fetch_code() {
    local before="" ref
    if [ -d "$SRC/.git" ]; then
        before="$(git -C "$SRC" rev-parse HEAD)"
        git -C "$SRC" remote set-url origin "$REPO"
        git -C "$SRC" fetch --quiet --tags --force origin
    else
        info "Cloning $REPO"
        install -d -m 755 "$PREFIX"
        git clone --quiet --no-checkout "$REPO" "$SRC"
    fi
    if git -C "$SRC" rev-parse --verify --quiet "refs/tags/$RELEASE^{commit}" >/dev/null; then
        ref="refs/tags/$RELEASE"
    elif git -C "$SRC" rev-parse --verify --quiet "refs/remotes/origin/$RELEASE^{commit}" >/dev/null; then
        ref="refs/remotes/origin/$RELEASE"
    elif git -C "$SRC" rev-parse --verify --quiet "$RELEASE^{commit}" >/dev/null; then
        ref="$RELEASE"
    else
        die "version $RELEASE not found in $REPO"
    fi
    git -C "$SRC" -c advice.detachedHead=false checkout --quiet --force --detach "$ref"
    CODE_CHANGED=0
    [ "$before" = "$(git -C "$SRC" rev-parse HEAD)" ] || CODE_CHANGED=1
    info "LynxElectrumX $RELEASE ($(git -C "$SRC" rev-parse --short HEAD))"
}

load_profile() {
    local profile="$SRC/lynx/chains/$CHAIN.env"
    if [ ! -f "$profile" ]; then
        local available=("$SRC"/lynx/chains/*.env)
        available=("${available[@]##*/}")
        die "no chain profile '$CHAIN'; available: ${available[*]%.env}"
    fi
    # shellcheck disable=SC1090
    . "$profile"
    local var
    for var in COIN_NAME NODE_SERVICE NODE_CONF NODE_COOKIE SSL_PORT WSS_PORT MIN_DISK_GB MIN_RAM_GB CACHE_MB; do
        [ -n "${!var:-}" ] || die "$profile does not set $var"
    done
}

install_venv() {
    info "Installing ElectrumX into $VENV"
    [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --disable-pip-version-check \
        -c "$SRC/lynx/constraints.txt" "${SRC}[$DB_ENGINE]"
    # pip may consider an unchanged version number "already installed";
    # always reinstall the package itself so the checked-out code is used.
    "$VENV/bin/pip" install --quiet --disable-pip-version-check \
        --no-deps --force-reinstall "$SRC"
    EX_VERSION="$("$VENV/bin/python" -c 'import electrumx; print(electrumx.version)')"
    COIN_GENESIS="$("$VENV/bin/python" - "$COIN_NAME" <<'PY'
import sys
from electrumx.lib.coins import Coin
print(Coin.lookup_coin_class(sys.argv[1], 'mainnet').GENESIS_HASH)
PY
)" || die "COIN_NAME=$COIN_NAME is not a coin class in this version"
    COIN_RPC_PORT="$("$VENV/bin/python" -c "from electrumx.lib.coins import Coin; print(Coin.lookup_coin_class('$COIN_NAME', 'mainnet').RPC_PORT)")"
}

# Print the value of a node config key, as Bitcoin-Core-style nodes read it:
# top-level "key=", "main.key=", or "key=" inside a [main] section.
conf_get() {
    awk -v key="$1" '
        { sub(/\r$/, ""); sub(/^[ \t]+/, "") }
        /^#/ || $0 == "" { next }
        /^\[/ { section = $0; sub(/^\[[ \t]*/, "", section); sub(/[ \t]*\].*$/, "", section); next }
        {
            eq = index($0, "="); if (!eq) next
            k = substr($0, 1, eq - 1); v = substr($0, eq + 1)
            sub(/[ \t]+$/, "", k); sub(/^[ \t]+/, "", v); sub(/[ \t]+$/, "", v)
            if ((section == "" || section == "main") && k == key) { print v; exit }
            if (section == "" && k == "main." key) { print v; exit }
        }' "$NODE_CONF"
}

# Build DAEMON_URL from the node config written by Spark.
read_node_rpc() {
    [ -f "$NODE_CONF" ] || die "$NODE_CONF not found; install and sync the node first: bash <(curl -sL install.getlynx.io)"
    local user pass port bind host
    user="$(conf_get rpcuser)"
    pass="$(conf_get rpcpassword)"
    port="$(conf_get rpcport)"
    bind="$(conf_get rpcbind)"

    # rpcbind may be "addr", "addr:port", "[v6addr]" or "[v6addr]:port".
    case "$bind" in
        \[*\]:*) host="${bind%%]:*}]"; [ -n "$port" ] || port="${bind##*]:}" ;;
        \[*) host="$bind" ;;
        *:*) host="${bind%%:*}"; [ -n "$port" ] || port="${bind##*:}" ;;
        *) host="$bind" ;;
    esac
    [ -n "$host" ] || host="$(conf_get rpcconnect)"
    [ -n "$host" ] || host="127.0.0.1"
    if [ -z "$port" ]; then
        port="$(ss -tlnH "src ${host//[][]/}" 2>/dev/null | awk 'NR == 1 { n = split($4, a, ":"); print a[n] }')"
    fi
    [ -n "$port" ] || port="$COIN_RPC_PORT"

    if [ -z "$user" ] || [ -z "$pass" ]; then
        [ -r "$NODE_COOKIE" ] || die "no rpcuser/rpcpassword in $NODE_CONF and no cookie at $NODE_COOKIE"
        warn "using the node's cookie file; it changes whenever the node restarts, which will break ElectrumX's connection. Set rpcuser/rpcpassword in $NODE_CONF instead."
        IFS=: read -r user pass < "$NODE_COOKIE"
    fi
    DAEMON_URL="$("$VENV/bin/python" - "$user" "$pass" "$host" "$port" <<'PY'
import sys
from urllib.parse import quote
user, password, host, port = sys.argv[1:]
print(f'http://{quote(user, safe="")}:{quote(password, safe="")}@{host}:{port}/')
PY
)"
    info "Node RPC: $host:$port"
}

# Call a node RPC method; prints the JSON "result".
rpc() {
    local method="$1" params="${2:-[]}"
    curl -sS --max-time 15 -H 'content-type: text/plain;' \
        --data-binary "{\"jsonrpc\":\"1.0\",\"id\":\"build\",\"method\":\"$method\",\"params\":$params}" \
        "$DAEMON_URL" | "$VENV/bin/python" -c '
import json, sys
reply = json.load(sys.stdin)
error = reply.get("error")
if error:
    sys.exit(f"RPC error: {error}")
print(json.dumps(reply["result"]))'
}

check_node() {
    local info_json ibd chain blocks genesis
    info_json="$(rpc getblockchaininfo)" || die "cannot reach the node RPC with the settings from $NODE_CONF (is $NODE_SERVICE running?)"
    read -r chain blocks ibd < <("$VENV/bin/python" -c '
import json, sys
i = json.loads(sys.argv[1])
print(i.get("chain"), i.get("blocks"), str(i.get("initialblockdownload")).lower())' "$info_json")
    [ "$chain" = main ] || warn "node reports chain '$chain', expected 'main'"
    [ "$ibd" = false ] || die "node is still syncing (height $blocks); re-run once it has caught up"
    genesis="$(rpc getblockhash '[0]' | tr -d '"')"
    [ "$genesis" = "$COIN_GENESIS" ] || die "node genesis $genesis does not match $COIN_NAME ($COIN_GENESIS); wrong --chain?"
    info "Node is synced at height $blocks"
}

check_resources() {
    local disk_gb ram_gb probe="$DB_DIRECTORY"
    [ -d "$probe" ] || probe="$(dirname "$DB_DIRECTORY")"
    disk_gb="$(df -BG --output=avail "$probe" | tail -n1 | tr -dc '0-9')"
    ram_gb="$(awk '/^MemTotal:/ { printf "%d", $2 / 1048576 + 0.5 }' /proc/meminfo)"
    [ "$disk_gb" -ge "$MIN_DISK_GB" ] || warn "only ${disk_gb} GB free for $DB_DIRECTORY; $COIN_NAME needs about ${MIN_DISK_GB} GB"
    [ "$ram_gb" -ge "$MIN_RAM_GB" ] || warn "only ${ram_gb} GB RAM; $COIN_NAME needs about ${MIN_RAM_GB} GB"
}

# Let's Encrypt validates over IPv4 and, when an AAAA record exists, IPv6.
# Every record must point at this server or issuance fails.
check_dns() {
    local family rtype records local_addrs addr
    for family in 4 6; do
        rtype=A; [ "$family" = 6 ] && rtype=AAAA
        records="$(dig +short "$rtype" "$DOMAIN" | grep -E '^[0-9a-fA-F.:]+$' || true)"
        if [ -z "$records" ]; then
            [ "$family" = 4 ] && die "$DOMAIN has no A record; point it at this server first"
            continue
        fi
        local_addrs="$(ip "-$family" -o addr show scope global | awk '{ sub(/\/.*/, "", $4); print $4 }')"
        for addr in $records; do
            grep -qixF "$addr" <<< "$local_addrs" ||
                die "$DOMAIN $rtype record $addr is not an address of this server (local: ${local_addrs//$'\n'/ })"
        done
        info "DNS $rtype $DOMAIN -> ${records//$'\n'/ }"
    done
}

setup_user() {
    if ! id electrumx >/dev/null 2>&1; then
        useradd --system --home-dir "$DB_DIRECTORY" --no-create-home --shell /usr/sbin/nologin electrumx
    fi
    install -d -m 750 -o electrumx -g electrumx "$DB_DIRECTORY"
    install -d -m 755 /etc/electrumx
    install -d -m 750 -o root -g electrumx "$TLS_DIR"
}

install_helpers() {
    install -d -m 755 "$HOOK_DIR/certbot"
    install -m 755 "$SRC"/lynx/certbot/*.sh "$HOOK_DIR/certbot/"
    install -m 755 "$SRC/lynx/firewall/lynx-electrumx-firewall" /usr/local/sbin/
}

# Fill a template from lynx/templates with the exported variables.
render() {
    "$VENV/bin/python" - "$SRC/lynx/templates/$1" <<'PY'
import os, string, sys
print(string.Template(open(sys.argv[1]).read()).substitute(os.environ), end='')
PY
}

# install_file SRC DEST MODE OWNER: install only if different. Sets CHANGED=1 if so.
install_file() {
    if ! cmp -s "$1" "$2"; then
        install -m "$3" -o "${4%%:*}" -g "${4##*:}" "$1" "$2"
        CHANGED=1
    fi
    rm -f "$1"
}

write_config() {
    export COIN_NAME DAEMON_URL DB_DIRECTORY DB_ENGINE CACHE_MB SSL_PORT WSS_PORT \
        DOMAIN TLS_DIR RELEASE NODE_CONF NODE_SERVICE PREFIX
    local tmp; tmp="$(mktemp)"
    render electrumx.conf.tmpl > "$tmp"
    CHANGED=0
    install_file "$tmp" "$CONF" 640 root:electrumx
    CONF_CHANGED=$CHANGED
}

setup_tls() {
    if [ "$TLS" = selfsigned ]; then
        if ! openssl x509 -in "$TLS_DIR/fullchain.pem" -noout -checkhost "$DOMAIN" 2>/dev/null | grep -q 'does match'; then
            info "Generating a self-signed certificate for $DOMAIN (testing only)"
            openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 825 \
                -subj "/CN=$DOMAIN" -addext "subjectAltName=DNS:$DOMAIN" \
                -keyout "$TLS_DIR/privkey.pem" -out "$TLS_DIR/fullchain.pem" 2>/dev/null
            chown electrumx:electrumx "$TLS_DIR"/*.pem
            chmod 600 "$TLS_DIR/privkey.pem"
            chmod 644 "$TLS_DIR/fullchain.pem"
        fi
        return
    fi

    info "Requesting a Let's Encrypt certificate for $DOMAIN"
    certbot certonly --standalone --non-interactive --agree-tos --keep-until-expiring \
        -m "$EMAIL" -d "$DOMAIN" --cert-name "$DOMAIN" \
        --pre-hook "$HOOK_DIR/certbot/pre-hook.sh" \
        --post-hook "$HOOK_DIR/certbot/post-hook.sh" \
        --deploy-hook "$HOOK_DIR/certbot/deploy-hook.sh"
    # The deploy hook only runs when a certificate is issued, so install the
    # current one explicitly (covers re-runs and pre-existing certificates).
    RENEWED_LINEAGE="/etc/letsencrypt/live/$DOMAIN" LEX_NO_RESTART=1 "$HOOK_DIR/certbot/deploy-hook.sh"
    info "Testing automatic renewal (certbot renew --dry-run)"
    certbot renew --dry-run --cert-name "$DOMAIN" --quiet ||
        warn "certbot renew --dry-run failed; automatic renewal will not work until this is fixed"
}

setup_firewall() {
    local tmp
    for unit in electrumx-patch-firewall.service electrumx-patch-firewall.timer; do
        tmp="$(mktemp)"; render "$unit" > "$tmp"
        CHANGED=0; install_file "$tmp" "/etc/systemd/system/$unit" 644 root:root
    done
    systemctl daemon-reload
    systemctl enable --quiet electrumx-patch-firewall.service electrumx-patch-firewall.timer
    systemctl start electrumx-patch-firewall.timer
    systemctl start electrumx-patch-firewall.service
    journalctl -u electrumx-patch-firewall.service -n 3 --no-pager -o cat || true
}

setup_service() {
    local tmp; tmp="$(mktemp)"
    render electrumx.service > "$tmp"
    CHANGED=0
    install_file "$tmp" /etc/systemd/system/electrumx.service 644 root:root
    systemctl daemon-reload
    systemctl enable --quiet electrumx.service
    if systemctl is-active --quiet electrumx.service; then
        if [ "$CODE_CHANGED" = 1 ] || [ "$CONF_CHANGED" = 1 ] || [ "$CERT_CHANGED" = 1 ] || [ "$CHANGED" = 1 ]; then
            info "Restarting ElectrumX"
            systemctl restart electrumx.service
        fi
    else
        info "Starting ElectrumX"
        systemctl start electrumx.service
    fi
    sleep 5
    systemctl is-active --quiet electrumx.service ||
        die "ElectrumX failed to start; see: journalctl -u electrumx -n 50"
}

summary() {
    local expiry
    expiry="$(openssl x509 -in "$TLS_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)"
    cat <<EOF

LynxElectrumX $RELEASE ($(git -C "$SRC" rev-parse --short HEAD)), ElectrumX $EX_VERSION
  Coin:         $COIN_NAME   (DB: $DB_ENGINE in $DB_DIRECTORY)
  Services:     ssl://$DOMAIN:$SSL_PORT  wss://$DOMAIN:$WSS_PORT
  Certificate:  $TLS, expires ${expiry:-unknown}
  Config:       $CONF

ElectrumX now indexes the chain from genesis; this takes a while.
  Sync status:  $VENV/bin/electrumx_rpc getinfo
  Logs:         journalctl -fu electrumx
EOF
}

main() {
    parse_args "$@"
    check_system
    touch "$LOG" && chmod 600 "$LOG"
    exec > >(tee -a "$LOG") 2>&1
    info "$(date -u '+%F %T UTC') build.sh --chain $CHAIN --domain $DOMAIN --tls $TLS --version $RELEASE --db $DB_ENGINE"

    install_packages
    fetch_code
    load_profile
    install_venv
    if [ -z "$DAEMON_URL" ]; then read_node_rpc; fi
    check_node
    check_resources
    if [ "$TLS" = certbot ]; then check_dns; fi
    setup_user
    install_helpers
    write_config
    local cert_before; cert_before="$(sha256sum "$TLS_DIR/fullchain.pem" 2>/dev/null || true)"
    setup_tls
    CERT_CHANGED=0
    [ "$cert_before" = "$(sha256sum "$TLS_DIR/fullchain.pem" 2>/dev/null || true)" ] || CERT_CHANGED=1
    setup_firewall
    setup_service
    summary

    if [ "$FOLLOW_LOGS" = 1 ]; then exec journalctl -fu electrumx; fi
}

main "$@"
