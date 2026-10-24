# LynxElectrumX

ElectrumX server for [Lynx](https://getlynx.io) and the other chains built from the [Lynx codebase](https://github.com/getlynx/Lynx), with a one-command installer.

```
Based on:   spesmilo/electrumx 2.0.0 (MIT licence)
Language:   Python 3.10+ (Debian 13 ships 3.13)
Protocol:   Electrum 1.4 – 1.6
```

An Electrum server lets light wallets (Electrum and compatible SPV clients) check balances, fetch transaction history and broadcast transactions without running a full node. It connects to a full node, indexes the whole chain, and answers wallet queries over TLS.

This repository is [spesmilo/electrumx](https://github.com/spesmilo/electrumx), the ElectrumX maintained by the Electrum developers, with the Lynx-family coins added and an installer in [`lynx/`](lynx/). Upstream's history is kept, so upstream fixes merge in normally.

## Supported chains

All twelve chains run the same Lynx Core codebase: 80-byte headers, SegWit transactions, proof of stake.

| Chain | Ticker | `--chain` | Node RPC port |
|---|---|---|---|
| Alioth | ALIO | `alioth` | 55802 |
| Borrelly | BORR | `borrelly` | 58401 |
| Cassiopeia | CASS | `cassiopeia` | 53054 |
| Delphinus | DELP | `delphinus` | 57691 |
| Digitalcoin | DGC | `digitalcoin` | 7998 |
| Enceladus | ENCE | `enceladus` | 58611 |
| Fenrir | FENR | `fenrir` | 54826 |
| Galatea | GALA | `galatea` | 55786 |
| Halley | HALL | `halley` | 53837 |
| Indus | INDU | `indus` | 54701 |
| InfiniLooP | IL8P | `infiniloop` | 9459 |
| Lynx | LYNX | `lynx` | 8332 |

Chain parameters (address prefixes, genesis hash, ports) come from [`src/kernel/chainparams.cpp`](https://github.com/getlynx/Lynx/blob/main/src/kernel/chainparams.cpp) in getlynx/Lynx. InfiniLooP's history from before it moved to the Lynx codebase (scrypt block hashes, `nTime` transactions up to height 2,800,000) is handled too.

## Installing a server

### Requirements

- A **Debian 13** VPS. One chain per VPS. Lynx runs on 2 vCPU and 4 GB RAM (with swap; the initial indexing uses the most memory). Leave disk room for the node's data and the ElectrumX database.
- The chain's node installed with **Spark** and **fully synced**:
  ```bash
  bash <(curl -sL install.getlynx.io) --chain=<chain>
  ```
- A **hostname** for the server, with an A record (and an AAAA record, if you publish one) pointing at the VPS. The installer gets a Let's Encrypt certificate for it.
- Inbound **TCP 80, 50002 and 50004** allowed by your provider's firewall, if it has one. The firewall on the VPS itself is handled by the installer.
- Root access.

### Install

As root, on the VPS:

```bash
curl -sL https://raw.githubusercontent.com/getlynx/LynxElectrumX/main/lynx/build.sh \
  | bash -s -- --chain lynx --domain electrum.example.com --version main
```

Replace `lynx` with your chain and `electrum.example.com` with your hostname. This takes about 5–10 minutes. The installer:

1. installs the system packages it needs;
2. checks out a pinned version of this repository into `/opt/lynx-electrumx` and builds a Python environment with pinned dependencies;
3. reads the node's RPC settings from its Spark config, and refuses to continue unless the node is synced and really is the chosen chain (genesis hash check);
4. checks the hostname's DNS records point at this server;
5. gets a Let's Encrypt certificate and confirms automatic renewal works;
6. opens the Electrum ports in Spark's firewall (IPv4, and IPv6 wherever Spark's firewall covers it);
7. installs and starts the `electrumx` service, then prints a summary.

ElectrumX then indexes the chain from genesis. For Lynx (about 3.3 million blocks) this took under 75 minutes on a 2 vCPU, 4 GB VPS. The Electrum ports open once indexing is complete.

Every option can also be given as an environment variable, so the installer can run unattended:

| Option | Environment | Default | |
|---|---|---|---|
| `--chain` | `LEX_CHAIN` | (required) | see the table above |
| `--domain` | `LEX_DOMAIN` | (required) | public hostname |
| `--email` | `LEX_EMAIL` | `domains@getlynx.io` | Let's Encrypt contact |
| `--tls` | `LEX_TLS` | `certbot` | or `selfsigned`, for testing only |
| `--version` | `LEX_VERSION` | the release tag in `build.sh` | tag, branch or commit to install |
| `--db` | `LEX_DB` | `leveldb` | or `rocksdb` |
| `--repo` | `LEX_REPO` | this repository | e.g. a fork or local clone |
| `--daemon-url` | `LEX_DAEMON_URL` | read from the node config | `http://user:pass@host:port/` |
| `--force` | `LEX_FORCE=1` | | allow a system other than Debian 13 |
| `--follow-logs` | | | follow the log when done |

Running the installer again is safe. It changes only what differs and restarts ElectrumX only when the code, configuration or certificate changed.

### Check that it works

```bash
journalctl -fu electrumx                                # live log
/opt/lynx-electrumx/venv/bin/electrumx_rpc getinfo      # "db height" catches up with "daemon height"
```

Once indexing is complete, the log shows `Starting servers`. From any other machine:

```bash
echo '{"id":1,"method":"server.version","params":["test","1.4"]}' \
  | openssl s_client -quiet -connect electrum.example.com:50002 -servername electrum.example.com
```

should answer with `"result":["ElectrumX 2.0.0","1.4"]`.

### Connect a wallet

In the wallet's server settings, enter the hostname with port **50002** (TLS). Web clients can use **wss://electrum.example.com:50004**. Plain TCP (port 50001) is not offered.

### Update

Re-run the installer with the new version:

```bash
/opt/lynx-electrumx/src/lynx/build.sh --chain lynx --domain electrum.example.com --version <tag>
```

Read the release notes first. A major ElectrumX version can require re-indexing from genesis.

### Maintenance

None. Certificates renew automatically (`certbot.timer`), the firewall rules are re-applied every 10 minutes (`electrumx-patch-firewall.timer`), and ElectrumX 2.0 no longer needs the history compaction that 1.x servers required. See the [operator guide](lynx/README.md#maintenance).

## Documentation

| | |
|---|---|
| [`lynx/README.md`](lynx/README.md) | Operator guide: installed files, certificates, firewall, troubleshooting, comparing servers before a cut-over |
| [`lynx/docs/CHANGES-FROM-UPSTREAM.md`](lynx/docs/CHANGES-FROM-UPSTREAM.md) | Every change made to upstream ElectrumX, and why |
| [`docs/`](docs/) | Upstream ElectrumX documentation, including all configuration settings ([`docs/environment.rst`](docs/environment.rst)); also at [readthedocs](https://electrumx-spesmilo.readthedocs.io) |

### Differences from upstream ElectrumX

- **Protocol is capped at 1.6** for these chains. Protocol 1.7's `blockchain.outpoint.*` methods need the node's `txospenderindex` (Bitcoin Core 31+), which Lynx Core 28.x does not have; without it, spent outputs would be reported as unspent.
- **Servers offer TLS only**: SSL on 50002 and WebSocket over TLS on 50004.

## Development

### Layout

```
src/electrumx/lib/coins_lynx.py   Lynx-family base class, protocol cap, InfiniLooP history (hand-written)
src/electrumx/lib/lynx_chains.py  one class per chain (generated; do not edit)
lynx/build.sh                     the installer
lynx/chains/<chain>.env           per-chain installer profile
lynx/templates/                   electrumx.conf and systemd units
lynx/certbot/, lynx/firewall/     certificate hooks and firewall helper
lynx/tools/                       maintenance and testing tools (below)
tests/blocks/<chain>_mainnet_*.json   real blocks used as test fixtures
```

### Tests

```bash
python3 -m venv venv && . venv/bin/activate
pip install -e '.[leveldb]' pytest pytest-asyncio
pytest
```

`tests/lib/test_coins_lynx.py` and the Lynx-family fixtures in `tests/test_blocks.py` cover the chains in this repository. A few upstream altcoin tests need extra hash modules; see `.github/workflows/ci.yml` for the full list.

### Tools

| Tool | Use |
|---|---|
| `lynx/tools/sync_chainparams.py` | Regenerate `lynx_chains.py` after `chainparams.cpp` in getlynx/Lynx changes, or to add a chain. Run it by hand, review `git diff`, run `pytest`. |
| `lynx/tools/make_block_fixture.sh` | On a host with a chain's node, write a block test fixture for `tests/blocks/`. |
| `lynx/tools/compare_servers.py` | Ask two servers the same questions and report differences; use before moving DNS to a new server. |
| `lynx/tools/load_test.py` | See how a server treats one heavy client, to tune `COST_SOFT_LIMIT` and `COST_HARD_LIMIT`. Run against your own servers only. |

### Adding a chain

1. Add the chain to `CHAINS` in `lynx/tools/sync_chainparams.py` and run it.
2. Add a block fixture with `make_block_fixture.sh` and a `lynx/chains/<chain>.env` profile.
3. Run `pytest`. The tests fail if a chain has no fixture or no profile.

### Taking upstream updates

```bash
git fetch upstream --tags
git merge <upstream release tag>
pytest
```

Then tag a new release (`v<upstream version>-lynx.<n>`) and re-run the installer on each server with `--version` set to it. Changes to upstream files are listed in [`CHANGES-FROM-UPSTREAM.md`](lynx/docs/CHANGES-FROM-UPSTREAM.md); keep that list current.

## Credits and licence

ElectrumX was written by Neil Booth and is maintained by the Electrum developers ([spesmilo/electrumx](https://github.com/spesmilo/electrumx)). The Lynx-family additions are by the Lynx developers. Released under the MIT licence; see [LICENCE](LICENCE).
