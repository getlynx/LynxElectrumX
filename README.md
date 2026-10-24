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

### Recommended VPS

| | Recommended | Notes |
|---|---|---|
| OS | **Debian 13** (trixie), fresh install | The installer refuses other systems unless forced. |
| CPU | **2 vCPU** | Plenty once indexed; the initial indexing is the busy part. |
| RAM | **4 GB** | Measured on Lynx: ElectrumX peaks at about 2.1 GB while indexing, the node uses about 0.35 GB. Spark adds a 4 GB swap file. |
| Disk | **80 GB SSD** | Room for the node's chain data, the ElectrumX database and growth. Use SSD or NVMe, not spinning disks. |
| Network | Public IPv4 (IPv6 optional) | Inbound TCP 80, 50002 and 50004 must be reachable. |

A 2 vCPU / 4 GB VPS indexed all of Lynx (about 3.3 million blocks) in under 75 minutes.

### One ElectrumX per VPS

Run **one chain, and so one ElectrumX server, per VPS**. Several ElectrumX servers can technically share a machine, but this repository does not support it, and it is not recommended:

- **Ports.** Wallets expect SSL on 50002 and WebSocket on 50004, and only one server per IP address can use them. A second chain on the same VPS would need non-standard ports that every wallet has to be told about.
- **Memory.** Each server needs its own node plus about 2 GB while indexing. Two on a 4 GB VPS would swap heavily.
- **Isolation.** With one chain per VPS, a problem with one server (or its node) never affects another chain.

### Step 1: set up the node with Spark

[Spark](https://github.com/getlynx/Lynx/tree/main/contrib/installer) installs and runs the chain's node. On the fresh Debian 13 VPS, as root:

```bash
bash <(curl -sL install.getlynx.io) --chain=lynx
```

Use your chain's name from the table above. Spark installs the node as a systemd service (named after the chain), writes its config to `/var/lib/<chain>/<chain>.conf` with RPC credentials bound to the local machine, sets up its firewall (SSH and the node's P2P port only), adds swap if needed, and starts syncing. ElectrumX needs no extra node settings: the transaction index it relies on is on by default in Lynx Core.

Wait until the node is **fully synced** before step 2. Log in again so the Spark console loads, then:

```bash
gbi        # same as: <chain>-cli -datadir=/var/lib/<chain> getblockchaininfo
```

The node is ready when it shows `"initialblockdownload": false`. The installer checks this too and stops if the node is still syncing.

### Step 2: install ElectrumX

Before running the installer, make sure:

- the server's **hostname** has an A record (and an AAAA record, if you publish one) pointing at this VPS; the installer gets a Let's Encrypt certificate for it and checks every record;
- your provider's firewall, if it has one, allows inbound **TCP 80, 50002 and 50004**; the firewall on the VPS itself is handled by the installer.

Then, as root:

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

### Staking on an Electrum server

An Electrum server's node can also stake, so the server helps secure the network as well as serving wallets. Staking adds very little load, and ElectrumX is not slowed down when its node finds a block.

**Encrypt the wallet with a strong passphrase first. This is highly recommended.** ElectrumX itself never uses the wallet: it only reads blocks and transactions and broadcasts transactions. But it holds the node's RPC password, and an Electrum server is a public, internet-facing service. If ElectrumX were ever compromised, an unencrypted (or fully unlocked) wallet could be emptied with that password. With the wallet encrypted and unlocked *for staking only*, Lynx Core refuses every command that sends coins or exports keys (`sendtoaddress`, `send`, `sendall`, `signrawtransactionwithwallet`, `dumpprivkey`, `dumpwallet` and others), so the coins stay safe even then.

1. **Encrypt the wallet** with a long, random passphrase (for example six or more random words) and store it somewhere safe off the server. The leading space keeps the command out of the shell history:
   ```bash
    lynx-cli -datadir=/var/lib/lynx encryptwallet "<passphrase>"
   ```
2. **Make a new wallet backup.** Encrypting creates new keys, so backups made before encryption do not cover coins received afterwards.
3. **Unlock for staking only.** The `0` keeps it unlocked until the node restarts and `true` means staking only. The passphrase is read from the terminal without echoing:
   ```bash
   lynx-cli -datadir=/var/lib/lynx -stdinwalletpassphrase walletpassphrase 0 true
   ```
4. **Send the coins to stake** to an address from this wallet (`getnewaddress`).

Replace `lynx` with your chain in the commands above.

Keep in mind:

- **After every node restart** (a reboot, or a Spark update), the wallet is locked again and staking stops until you repeat step 3. If you automate this, keep the passphrase in a root-only file (`chmod 600`), never in `/etc/electrumx.conf`.
- **A strong passphrase matters.** Someone with the RPC password could still copy the *encrypted* wallet file (`backupwallet`) and try to guess the passphrase offline, or stop staking (`walletlock`). Neither moves coins if the passphrase cannot be guessed.
- **Keep the node's data private.** Check that `/var/lib/<chain>` is not readable by other users (`ls -ld /var/lib/lynx` should show `drwx------`; fix with `chmod 700`).
- **Treat it as a hot wallet.** Stake modest amounts on each server, not reserve funds.

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
