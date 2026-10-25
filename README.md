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

| Chain | Ticker | `--chain` | P2P port |
|---|---|---|---|
| Alioth | ALIO | `alioth` | 55801 |
| Borrelly | BORR | `borrelly` | 58400 |
| Cassiopeia | CASS | `cassiopeia` | 53053 |
| Delphinus | DELP | `delphinus` | 57690 |
| Digitalcoin | DGC | `digitalcoin` | 7999 |
| Enceladus | ENCE | `enceladus` | 58610 |
| Fenrir | FENR | `fenrir` | 54825 |
| Galatea | GALA | `galatea` | 55785 |
| Halley | HALL | `halley` | 53836 |
| Indus | INDU | `indus` | 54700 |
| InfiniLooP | IL8P | `infiniloop` | 9449 |
| Lynx | LYNX | `lynx` | 22566 |

Chain parameters (address prefixes, genesis hash, ports) come from [`src/kernel/chainparams.cpp`](https://github.com/getlynx/Lynx/blob/main/src/kernel/chainparams.cpp) in getlynx/Lynx. InfiniLooP's history from before it moved to the Lynx codebase (scrypt block hashes, `nTime` transactions up to height 2,800,000) is handled too.

## Ports

Each chain has its own Electrum ports, worked out from its P2P port, and they are the same on every server:

- **SSL** (Electrum wallets) = P2P port + 3
- **WSS** (WebSocket over TLS, for web clients) = P2P port + 4
- **Admin** (`electrumx_rpc`, local to the server only, never opened in the firewall) = P2P port + 5

A full deployment runs all twelve chains on one server. On the public servers `electrum1.getlynx.io` and `electrum2.getlynx.io`:

| Chain | `--chain` | SSL | WSS | Admin (local) | Wallet server | Web client |
|---|---|---|---|---|---|---|
| Alioth | `alioth` | 55804 | 55805 | 55806 | `electrum1.getlynx.io:55804` | `wss://electrum1.getlynx.io:55805` |
| Borrelly | `borrelly` | 58403 | 58404 | 58405 | `electrum1.getlynx.io:58403` | `wss://electrum1.getlynx.io:58404` |
| Cassiopeia | `cassiopeia` | 53056 | 53057 | 53058 | `electrum1.getlynx.io:53056` | `wss://electrum1.getlynx.io:53057` |
| Delphinus | `delphinus` | 57693 | 57694 | 57695 | `electrum1.getlynx.io:57693` | `wss://electrum1.getlynx.io:57694` |
| Digitalcoin | `digitalcoin` | 8002 | 8003 | 8004 | `electrum1.getlynx.io:8002` | `wss://electrum1.getlynx.io:8003` |
| Enceladus | `enceladus` | 58613 | 58614 | 58615 | `electrum1.getlynx.io:58613` | `wss://electrum1.getlynx.io:58614` |
| Fenrir | `fenrir` | 54828 | 54829 | 54830 | `electrum1.getlynx.io:54828` | `wss://electrum1.getlynx.io:54829` |
| Galatea | `galatea` | 55788 | 55789 | 55790 | `electrum1.getlynx.io:55788` | `wss://electrum1.getlynx.io:55789` |
| Halley | `halley` | 53839 | 53840 | 53841 | `electrum1.getlynx.io:53839` | `wss://electrum1.getlynx.io:53840` |
| Indus | `indus` | 54703 | 54704 | 54705 | `electrum1.getlynx.io:54703` | `wss://electrum1.getlynx.io:54704` |
| InfiniLooP | `infiniloop` | 9452 | 9453 | 9454 | `electrum1.getlynx.io:9452` | `wss://electrum1.getlynx.io:9453` |
| Lynx | `lynx` | 22569 | 22570 | 22571 | `electrum1.getlynx.io:22569` | `wss://electrum1.getlynx.io:22570` |

The same ports work on `electrum2.getlynx.io`. Configure both in wallets, so they can switch if one is down.

**Provider firewall.** If your VPS provider has its own firewall, a full deployment needs these inbound TCP ports open (80 is for Let's Encrypt certificates; the rest are SSL and WSS):

```
80, 8002, 8003, 9452, 9453, 22569, 22570, 53056, 53057, 53839, 53840, 54703, 54704, 54828, 54829, 55788, 55789, 55804, 55805, 57693, 57694, 58403, 58404, 58613, 58614
```

A server with fewer chains needs only 80 plus those chains' SSL and WSS ports. The firewall on the server itself is set up by the installer.

The ports are generated into `lynx/chains/<chain>.env` by `lynx/tools/sync_chainparams.py`, which refuses any new chain whose ports would collide with another chain's.

## Installing a server

### Recommended VPS

A server can run one chain or several. Each chain gets its own node and its own ElectrumX, on that chain's ports.

| | One chain | All 12 chains |
|---|---|---|
| OS | **Debian 13** (trixie), fresh install | **Debian 13** (trixie), fresh install |
| CPU | **2 vCPU** | **6 vCPU** |
| RAM | **4 GB** | **16 GB** |
| Disk | **80 GB SSD** | **640 GB SSD** |
| Network | Public IPv4 (IPv6 optional) | Public IPv4 (IPv6 optional) |

Measured on Lynx with one chain: ElectrumX peaks at about 2.1 GB of RAM while indexing (about 3.3 million blocks, under 75 minutes on 2 vCPU / 4 GB), and the node uses about 0.35 GB. Spark adds a 4 GB swap file. The all-chains figures allow for twelve nodes plus twelve ElectrumX servers with room to index one large chain (Lynx, InfiniLooP, Digitalcoin) at a time; the other nine chains are small. Use SSD or NVMe, not spinning disks.

**Run at least two servers for each chain, in different places.** Wallets list several servers and switch when one is down. With all chains on one server, an outage there affects every chain, so a second all-chains server elsewhere (for example one in North America and one in Europe) is what keeps service up.

### Step 1: set up the node with Spark

[Spark](https://github.com/getlynx/Lynx/tree/main/contrib/installer) installs and runs each chain's node. On the fresh Debian 13 VPS, as root, once per chain:

```bash
bash <(curl -sL install.getlynx.io) --chain=lynx
```

Use the chain names from the table above. Spark installs the node as a systemd service (named after the chain), writes its config to `/var/lib/<chain>/<chain>.conf` with RPC credentials bound to the local machine, sets up its firewall (SSH and the node's P2P port only), adds swap if needed, and starts syncing. ElectrumX needs no extra node settings: the transaction index it relies on is on by default in Lynx Core.

Wait until each node is **fully synced** before step 2. Log in again so the Spark console loads, then:

```bash
gbi        # same as: <chain>-cli -datadir=/var/lib/<chain> getblockchaininfo
```

The node is ready when it shows `"initialblockdownload": false`. The installer checks this too and stops if the node is still syncing.

### Step 2: install ElectrumX

Before running the installer, make sure:

- the server's **hostname** has an A record (and an AAAA record, if you publish one) pointing at this VPS; the installer gets a Let's Encrypt certificate for it and checks every record;
- your provider's firewall, if it has one, allows inbound **TCP 80** (certificates) and each chain's **SSL and WSS ports** (see [Ports](#ports)); the firewall on the VPS itself is handled by the installer.

Then, as root, for one chain:

```bash
curl -sL https://raw.githubusercontent.com/getlynx/LynxElectrumX/main/lynx/build.sh \
  | bash -s -- --chain lynx --domain electrum.example.com --version main
```

or for every chain whose Spark node is installed on the server (a comma-separated list such as `--chain lynx,alioth` works too):

```bash
curl -sL https://raw.githubusercontent.com/getlynx/LynxElectrumX/main/lynx/build.sh \
  | bash -s -- --chain all --domain electrum.example.com --version main
```

Replace `electrum.example.com` with the server's hostname. This takes about 5–10 minutes. The installer:

1. installs the system packages it needs;
2. checks out a pinned version of this repository into `/opt/lynx-electrumx` and builds a Python environment with pinned dependencies;
3. reads each node's RPC settings from its Spark config, and refuses to continue unless every node is synced and really is the chosen chain (genesis hash check);
4. checks the hostname's DNS records point at this server;
5. gets one Let's Encrypt certificate for the hostname, shared by all chains on the server, and confirms automatic renewal works;
6. opens every chain's Electrum ports in Spark's firewall (IPv4, and IPv6 wherever Spark's firewall covers it);
7. writes `/etc/electrumx/<chain>.conf` and starts `electrumx@<chain>.service` for each chain, then prints a summary with each chain's ports.

ElectrumX then indexes each chain from genesis; a chain's ports open once its indexing is complete. On a server with several chains, start the large chains (Lynx, InfiniLooP, Digitalcoin) one run at a time if RAM is tight.

Every option can also be given as an environment variable, so the installer can run unattended:

| Option | Environment | Default | |
|---|---|---|---|
| `--chain` | `LEX_CHAIN` | (required) | a chain, a comma-separated list, or `all` |
| `--domain` | `LEX_DOMAIN` | (required) | public hostname |
| `--email` | `LEX_EMAIL` | `domains@getlynx.io` | Let's Encrypt contact |
| `--tls` | `LEX_TLS` | `certbot` | or `selfsigned`, for testing only |
| `--version` | `LEX_VERSION` | the release tag in `build.sh` | tag, branch or commit to install |
| `--db` | `LEX_DB` | `leveldb` | or `rocksdb` |
| `--repo` | `LEX_REPO` | this repository | e.g. a fork or local clone |
| `--daemon-url` | `LEX_DAEMON_URL` | read from the node config | `http://user:pass@host:port/` (one chain only) |
| `--force` | `LEX_FORCE=1` | | allow a system other than Debian 13 |
| `--follow-logs` | | | follow the log when done |

Running the installer again is safe. It changes only what differs and restarts a chain's ElectrumX only when the code, its configuration or the certificate changed. Chains already set up but not named in `--chain` are left alone. A server set up by an earlier single-chain version is moved to this layout automatically, keeping its database.

### Check that it works

```bash
lynx-electrumx-rpc                        # the chains on this server, and whether each is running
lynx-electrumx-rpc lynx getinfo           # "db height" catches up with "daemon height"
journalctl -fu electrumx@lynx             # live log for one chain
```

Once a chain's indexing is complete, its log shows `caught up to height …` and then `SSL server listening on …`. From any other machine, using that chain's SSL port:

```bash
echo '{"id":1,"method":"server.version","params":["test","1.4"]}' \
  | openssl s_client -quiet -connect electrum.example.com:22569 -servername electrum.example.com
```

should answer with `"result":["ElectrumX 2.0.0","1.4"]`.

### Connect a wallet

In the wallet's server settings, enter the hostname with the chain's **SSL port** from [Ports](#ports), for example `electrum1.getlynx.io:22569` for Lynx. Web clients use the chain's WSS port, for example `wss://electrum1.getlynx.io:22570`. Plain TCP is not offered.

### Update

Re-run the installer with the new version:

```bash
/opt/lynx-electrumx/src/lynx/build.sh --chain all --domain electrum.example.com --version <tag>
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

- **After every node restart** (a reboot, or a Spark update), the wallet is locked again and staking stops until you repeat step 3. If you automate this, keep the passphrase in a root-only file (`chmod 600`), never in `/etc/electrumx/<chain>.conf`.
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
- **Servers offer TLS only**: SSL and WebSocket over TLS, on each chain's own ports (see [Ports](#ports)).

## Development

### Layout

```
src/electrumx/lib/coins_lynx.py   Lynx-family base class, protocol cap, InfiniLooP history (hand-written)
src/electrumx/lib/lynx_chains.py  one class per chain (generated; do not edit)
lynx/build.sh                     the installer
lynx/chains/<chain>.env           per-chain installer profile and ports (generated; do not edit)
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
| `lynx/tools/sync_chainparams.py` | Regenerate `lynx_chains.py` and the chain profiles (with their ports) after `chainparams.cpp` in getlynx/Lynx changes, or to add a chain. It refuses if two chains' ports would clash. Run it by hand, review `git diff`, run `pytest`. |
| `lynx/tools/make_block_fixture.sh` | On a host with a chain's node, write a block test fixture for `tests/blocks/`. |
| `lynx/tools/compare_servers.py` | Ask two servers the same questions and report differences; use before moving DNS to a new server. |
| `lynx/tools/load_test.py` | See how a server treats one heavy client, to tune `COST_SOFT_LIMIT` and `COST_HARD_LIMIT`. Run against your own servers only. |

### Adding a chain

1. Add the chain to `CHAINS` in `lynx/tools/sync_chainparams.py` and run it.
2. Add a block fixture with `make_block_fixture.sh`. The chain's profile and ports are generated in step 1.
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
