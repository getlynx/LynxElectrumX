# Running a LynxElectrumX server

`lynx/build.sh` turns a Debian 13 VPS that runs a synced [Spark](https://github.com/getlynx/Lynx/tree/main/contrib/installer) node into an ElectrumX server for that node's chain. One chain per VPS.

## Before you start

1. A Debian 13 VPS with the node installed by Spark and fully synced:
   `bash <(curl -sL install.getlynx.io) --chain=<chain>`
2. A DNS A record (and AAAA record, if you publish one) for the server's hostname pointing at the VPS. Let's Encrypt checks every record.
3. Root access.

## Install

```bash
git clone https://github.com/getlynx/LynxElectrumX.git
sudo LynxElectrumX/lynx/build.sh --chain lynx --domain electrum.example.com
```

The script installs a pinned version of this repository into `/opt/lynx-electrumx`, gets a certificate, opens the firewall and starts the `electrumx` service. ElectrumX then indexes the chain from genesis, which takes a while.

| Option | Environment | Default | |
|---|---|---|---|
| `--chain` | `LEX_CHAIN` | (required) | profile in `lynx/chains/` |
| `--domain` | `LEX_DOMAIN` | (required) | public hostname |
| `--email` | `LEX_EMAIL` | `domains@getlynx.io` | Let's Encrypt contact |
| `--tls` | `LEX_TLS` | `certbot` | or `selfsigned` (testing only) |
| `--version` | `LEX_VERSION` | set in `build.sh` | tag, branch or commit to install |
| `--db` | `LEX_DB` | `leveldb` | or `rocksdb` |
| `--repo` | `LEX_REPO` | GitHub URL | e.g. an SSH URL |
| `--daemon-url` | `LEX_DAEMON_URL` | read from node config | `http://user:pass@host:port/` |
| `--force` | `LEX_FORCE=1` | | allow non-Debian-13 |
| `--follow-logs` | | | follow the log when done |

Running `build.sh` again is safe. It only changes what differs and restarts ElectrumX only if the code, configuration or certificate changed.

## Checking on it

```bash
systemctl status electrumx
journalctl -fu electrumx
/opt/lynx-electrumx/venv/bin/electrumx_rpc getinfo     # sync height, sessions
```

## Updating

```bash
sudo /opt/lynx-electrumx/src/lynx/build.sh --chain lynx --domain electrum.example.com --version <new tag>
```

Read the release notes first. A major ElectrumX version can require a full resync.

## What gets installed where

| Path | What |
|---|---|
| `/opt/lynx-electrumx/src` | this repository, checked out at `--version` |
| `/opt/lynx-electrumx/venv` | Python environment with ElectrumX |
| `/etc/electrumx.conf` | ElectrumX settings (contains node RPC credentials; `root:electrumx`, 640) |
| `/etc/electrumx/tls/` | certificate and key ElectrumX reads |
| `/db` | ElectrumX database |
| `/usr/local/lib/lynx-electrumx/certbot/` | certbot hooks |
| `/usr/local/sbin/lynx-electrumx-firewall` | firewall helper |
| `electrumx.service` | the server, running as user `electrumx` |
| `electrumx-patch-firewall.service`, `.timer` | keep the firewall open (see below) |
| `/var/log/lynx-electrumx-build.log` | build log |

## Certificates

Certbot issues the certificate in standalone mode. Its hooks are saved in the renewal configuration, so automatic renewals work the same way:

- **pre-hook** opens tcp/80 in the firewall for the challenge, and the **post-hook** closes it again.
- **deploy-hook** copies the new certificate to `/etc/electrumx/tls/` and restarts ElectrumX. ElectrumX never reads `/etc/letsencrypt`.

`build.sh` runs `certbot renew --dry-run` to confirm renewal works.

## Firewall

Spark's firewall is an iptables chain called `SPARK`. Spark's `patch_firewall.sh` re-applies it every 6 hours and deletes any port rule it did not create. So the ElectrumX ports live in a separate sub-chain, `SPARK_ELECTRUMX`, which Spark leaves alone as long as `electrumx-patch-firewall.service` exists. That service, run at boot and every 10 minutes by its timer, re-creates the sub-chain from `SERVICES` in `/etc/electrumx.conf`.

IPv4 and IPv6 are handled the same way, whenever that family has a `SPARK` chain.

## Troubleshooting

- **"node is still syncing"**: wait for the node to catch up (`gbi` in the Spark console), then re-run.
- **"cannot reach the node RPC"**: check the `rpc*` lines in the node config (e.g. `/var/lib/lynx/lynx.conf`), or pass `--daemon-url`.
- **DNS errors**: every A/AAAA record for the hostname must be an address of this server.
- **Certificate renewal**: `certbot renew --dry-run` shows what fails; the hooks log to the journal with tags `lynx-electrumx-firewall` and `lynx-electrumx-certbot`.
