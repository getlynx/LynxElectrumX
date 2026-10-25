# Running a LynxElectrumX server

`lynx/build.sh` turns a Debian 13 VPS that runs synced [Spark](https://github.com/getlynx/Lynx/tree/main/contrib/installer) nodes into ElectrumX servers for those chains: one ElectrumX per chain, each on its own ports, all sharing the server's hostname and certificate. See the [main README](../README.md#installing-a-server) for VPS sizes, setting up nodes with Spark, and each chain's ports.

## Before you start

1. A Debian 13 VPS with each chain's node installed by Spark and fully synced:
   `bash <(curl -sL install.getlynx.io) --chain=<chain>`
2. A DNS A record (and AAAA record, if you publish one) for the server's hostname pointing at the VPS. Let's Encrypt checks every record.
3. Root access.

## Install

```bash
git clone https://github.com/getlynx/LynxElectrumX.git
sudo LynxElectrumX/lynx/build.sh --chain all --domain electrum.example.com
```

`--chain` takes one chain (`lynx`), a comma-separated list (`lynx,alioth`), or `all`: every chain whose Spark node is installed here. The script checks every node first, then installs a pinned version of this repository into `/opt/lynx-electrumx`, gets a certificate, opens the firewall and starts one `electrumx@<chain>` service per chain. Each ElectrumX then indexes its chain from genesis.

| Option | Environment | Default | |
|---|---|---|---|
| `--chain` | `LEX_CHAIN` | (required) | chain(s) from `lynx/chains/`, or `all` |
| `--domain` | `LEX_DOMAIN` | (required) | public hostname |
| `--email` | `LEX_EMAIL` | `domains@getlynx.io` | Let's Encrypt contact |
| `--tls` | `LEX_TLS` | `certbot` | or `selfsigned` (testing only) |
| `--version` | `LEX_VERSION` | set in `build.sh` | tag, branch or commit to install |
| `--db` | `LEX_DB` | `leveldb` | or `rocksdb` |
| `--repo` | `LEX_REPO` | GitHub URL | e.g. an SSH URL |
| `--daemon-url` | `LEX_DAEMON_URL` | read from node config | `http://user:pass@host:port/` (one chain only) |
| `--force` | `LEX_FORCE=1` | | allow non-Debian-13 |
| `--follow-logs` | | | follow the log when done (one chain only) |

Running `build.sh` again is safe. It only changes what differs and restarts a chain's ElectrumX only if the code, its configuration or the certificate changed. Chains not named in `--chain` are left alone, so chains can be added one run at a time.

A server installed by v2.0.0-lynx.0 (one chain: `/etc/electrumx.conf`, `/db`, `electrumx.service`) is moved to this layout on the first run: the old service is removed and its database moved to `/db/<chain>`, so it does not re-index. Its ports change to the chain's ports from the main README.

## Checking on it

```bash
lynx-electrumx-rpc                        # chains on this server and whether each is running
lynx-electrumx-rpc lynx getinfo           # sync height, sessions (any electrumx_rpc command works)
systemctl status electrumx@lynx
journalctl -fu electrumx@lynx
```

## Before moving DNS to a new server

Compare its answers with a current server for the same chain, giving each server's port for that chain:

```bash
python3 lynx/tools/compare_servers.py electrum5.getlynx.io:50002 electrum1.getlynx.io:22569 --samples 50
```

It checks headers, merkle proofs, transactions and address histories at random heights, and that protocol 1.7's outpoint methods are refused. It exits non-zero on any unexpected difference. It works while the new server is still syncing, comparing only heights the new server has indexed.

To see how a heavy client (many addresses from one IP) is treated under the current `COST_SOFT_LIMIT`/`COST_HARD_LIMIT`, run against your own server only:

```bash
python3 lynx/tools/load_test.py electrum1.getlynx.io:22569 --random --scripthashes 1500
```

## Maintenance

There is no routine maintenance. In particular, the monthly steps the old 1.x servers needed must **not** be carried over:

- **No history compaction.** ElectrumX 2.0's database cannot hit the old flush-count overflow, and the compaction tool no longer exists.
- **No `chown` of `/etc/letsencrypt`.** ElectrumX reads its own copy of the certificate in `/etc/electrumx/tls/<hostname>/`, refreshed by the certbot deploy hook. `certbot.timer` handles renewal.
- **No firewall re-run.** `electrumx-patch-firewall.timer` re-applies the ports every 10 minutes.

`systemctl list-timers certbot.timer electrumx-patch-firewall.timer` shows both scheduled jobs.

## Updating

```bash
sudo /opt/lynx-electrumx/src/lynx/build.sh --chain all --domain electrum.example.com --version <new tag>
```

All chains on a server run the same code, so update them together. Read the release notes first. A major ElectrumX version can require a full resync.

## What gets installed where

| Path | What |
|---|---|
| `/opt/lynx-electrumx/src` | this repository, checked out at `--version` (shared by all chains) |
| `/opt/lynx-electrumx/venv` | Python environment with ElectrumX (shared) |
| `/etc/electrumx/<chain>.conf` | one chain's ElectrumX settings (contains its node's RPC credentials; `root:electrumx`, 640) |
| `/etc/electrumx/tls/<hostname>/` | the certificate and key ElectrumX reads (shared) |
| `/db/<chain>` | one chain's ElectrumX database |
| `electrumx@<chain>.service` | one chain's server, running as user `electrumx` |
| `/usr/local/bin/lynx-electrumx-rpc` | `electrumx_rpc` for a chain by name |
| `/usr/local/lib/lynx-electrumx/certbot/` | certbot hooks |
| `/usr/local/sbin/lynx-electrumx-firewall` | firewall helper |
| `electrumx-patch-firewall.service`, `.timer` | keep the firewall open (see below) |
| `/var/log/lynx-electrumx-build.log` | build log |

## Ports

Each chain's ports come from its P2P port: SSL = P2P + 3, WSS = P2P + 4, admin = P2P + 5. They are generated into `lynx/chains/<chain>.env` by `lynx/tools/sync_chainparams.py`, which refuses any change that would make two chains' node or Electrum ports collide. The admin port listens on localhost only and is never opened in the firewall.

## Certificates

One certificate per server hostname, shared by every chain on it. Certbot issues it in standalone mode. Its hooks are saved in the renewal configuration, so automatic renewals work the same way:

- **pre-hook** opens tcp/80 in the firewall for the challenge, and the **post-hook** closes it again.
- **deploy-hook** copies the new certificate to `/etc/electrumx/tls/<hostname>/` and restarts every running `electrumx@` service. ElectrumX never reads `/etc/letsencrypt`.

`build.sh` runs `certbot renew --dry-run` to confirm renewal works.

## Firewall

Spark's firewall is an iptables chain called `SPARK`. Spark's `patch_firewall.sh` re-applies it every 6 hours and deletes any port rule it did not create. So the ElectrumX ports live in a separate sub-chain, `SPARK_ELECTRUMX`, which Spark leaves alone as long as `electrumx-patch-firewall.service` exists. That service, run at boot and every 10 minutes by its timer, re-creates the sub-chain from the public ports in `SERVICES` of every `/etc/electrumx/<chain>.conf`.

IPv4 and IPv6 are handled the same way, whenever that family has a `SPARK` chain.

## Troubleshooting

- **"node is still syncing"**: wait for the node to catch up (`gbi` in the Spark console), then re-run.
- **"cannot reach the node RPC"**: check the `rpc*` lines in the node config (e.g. `/var/lib/lynx/lynx.conf`), or pass `--daemon-url` (one chain at a time).
- **DNS errors**: every A/AAAA record for the hostname must be an address of this server.
- **Certificate renewal**: `certbot renew --dry-run` shows what fails; the hooks log to the journal with tags `lynx-electrumx-firewall` and `lynx-electrumx-certbot`.
- **One chain's ElectrumX will not start**: `journalctl -u electrumx@<chain> -n 50`. The other chains keep running.
