# Changes from upstream

This repository is [spesmilo/electrumx](https://github.com/spesmilo/electrumx) with support for the chains built from [getlynx/Lynx](https://github.com/getlynx/Lynx). Changes to upstream files are kept as small as possible so upstream releases merge cleanly. Every one of them is listed here.

## Changed upstream files

| File | Change | Why |
|---|---|---|
| `README.md` | Rewritten for LynxElectrumX. | Upstream's README describes upstream; theirs is at [spesmilo/electrumx](https://github.com/spesmilo/electrumx). On merges, keep ours. |
| `src/electrumx/lib/coins.py` | Removed upstream's `class Lynx(Coin)`. | Replaced by the generated class in `lynx_chains.py`. Upstream's had the wrong `RPC_PORT` (9139; Lynx uses 8332). |
| `src/electrumx/lib/coins.py` | Removed upstream's `class Digitalcoin(Coin)`. | Replaced by the generated class. Digitalcoin now runs on the Lynx codebase (SegWit, proof of stake); upstream's had the wrong `RPC_PORT` (9413; now 7998). |
| `src/electrumx/lib/coins.py` | Added `from electrumx.lib.lynx_chains import *` at the end of the file. | `Coin.lookup_coin_class()` only finds classes that are names in `coins.py`. |

When merging upstream, check that upstream has not changed or re-added a class with the same `NAME` as one of ours. `tests/lib/test_coins_lynx.py::test_no_duplicate_coin_names` fails if it has.

## New files

| File | Purpose |
|---|---|
| `src/electrumx/lib/coins_lynx.py` | Hand-written. `LynxFamily` base class (SegWit transactions, 80-byte headers), the `LynxElectrumX` session class, and `InfiniLooPMixin` for InfiniLooP's pre-Lynx history. |
| `src/electrumx/lib/lynx_chains.py` | **Generated** by `lynx/tools/sync_chainparams.py`. One class per enabled chain. Do not edit by hand. |
| `lynx/tools/sync_chainparams.py` | Regenerates `lynx_chains.py` from `src/kernel/chainparams.cpp` in getlynx/Lynx. |
| `tests/lib/test_coins_lynx.py` | Coin lookup, protocol cap and address tests for the Lynx-family chains. |

## Behaviour differences

- **Protocol capped at 1.6** for Lynx-family chains (`LynxElectrumX.PROTOCOL_MAX`). Protocol 1.7's `blockchain.outpoint.*` methods need the node's `txospenderindex` (Bitcoin Core 31+). Lynx Core 28.x does not have it, and spent outputs would be reported as unspent.
- **Peers advertise SSL only** (`PEERS` entries use `s`). The Electrum peer protocol has no WebSocket port, and these servers do not offer plain TCP.
- **InfiniLooP history**: blocks with `nVersion` <= 6 are identified by their scrypt hash, and transactions in blocks up to 2,800,000 carry an extra `nTime` field (`InfiniLooPMixin`, mirroring `GetHash()` and `UnserializeTransaction()` in getlynx/Lynx).

## Updating chain parameters

`src/kernel/chainparams.cpp` in getlynx/Lynx is the source of truth for each chain's ports, address prefixes and genesis hash. After it changes, or to enable another chain:

1. Add the chain to `CHAINS` in `lynx/tools/sync_chainparams.py` if it is new.
2. Run `python3 lynx/tools/sync_chainparams.py`.
3. Add a block fixture for a new chain: run `lynx/tools/make_block_fixture.sh <chain>` on a host with the chain's node and copy the file into `tests/blocks/`. Add a `lynx/chains/<chain>.env` profile.
4. Review `git diff`, run `pytest`, commit.
