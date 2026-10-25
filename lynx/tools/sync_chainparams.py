#!/usr/bin/env python3
'''Regenerate the Lynx-family coin classes and chain profiles from getlynx/Lynx.

getlynx/Lynx src/kernel/chainparams.cpp is the source of truth for every
chain's ports, address prefixes and genesis hash. From it this writes:

    src/electrumx/lib/lynx_chains.py   one ElectrumX coin class per chain
    lynx/chains/<chain>.env            build.sh profile per chain, with the
                                       chain's Electrum ports

Run it by hand whenever that file changes or a chain is added below, then
review with `git diff` and run pytest.

    python3 lynx/tools/sync_chainparams.py               # getlynx/Lynx main
    python3 lynx/tools/sync_chainparams.py --ref <sha>   # a specific commit or tag
    python3 lynx/tools/sync_chainparams.py --file path/to/chainparams.cpp
'''

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = 'getlynx/Lynx'
SOURCE_PATH = 'src/kernel/chainparams.cpp'
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'src/electrumx/lib/lynx_chains.py'
PROFILES = ROOT / 'lynx/chains'

# Electrum ports follow from each chain's P2P port, the way the node's RPC
# and onion ports usually do (P2P + 1 and + 2), so every server uses the
# same ports for a chain and several chains can share one server.
SSL_OFFSET, WSS_OFFSET, ADMIN_OFFSET = 3, 4, 5

# Servers that run every chain; each chain announces them as Electrum peers
# on its own SSL port.
SHARED_SERVERS = ['electrum1.getlynx.io', 'electrum2.getlynx.io']

# The three chains with long histories need a bigger cache while indexing.
BIG = {'cache_mb': 1200, 'min_disk_gb': 30, 'min_ram_gb': 2}
SMALL = {'cache_mb': 300, 'min_disk_gb': 5, 'min_ram_gb': 1}

# Chains that get an ElectrumX coin class, keyed by chain id in
# chainparams.cpp. Everything here is what chainparams.cpp does not know:
#   size    BIG or SMALL: installer cache size and resource warnings
#   peers   extra Electrum peers to announce, e.g. 'host s' (SSL on 50002)
#   mixins  extra base classes from coins_lynx.py for chain-specific behaviour
CHAINS = {
    'alioth': {'size': SMALL},
    'borrelly': {'size': SMALL},
    'cassiopeia': {'size': SMALL},
    'delphinus': {'size': SMALL},
    'digitalcoin': {'size': BIG},
    'enceladus': {'size': SMALL},
    'fenrir': {'size': SMALL},
    'galatea': {'size': SMALL},
    'halley': {'size': SMALL},
    'indus': {'size': SMALL},
    'infiniloop': {'size': BIG, 'mixins': ['InfiniLooPMixin']},
    'lynx': {
        'size': BIG,
        # The ElectrumX 1.x servers, on the old standard port 50002.
        'peers': [
            'electrum5.getlynx.io s',
            'electrum6.getlynx.io s',
            'electrum7.getlynx.io s',
            'electrum8.getlynx.io s',
            'electrum9.getlynx.io s',
        ],
    },
}

REQUIRED = ('coinSymbol', 'genesishash', 'nDefaultPort', 'nRPCPort', 'nOnionPort',
            'pubkeyPrefix', 'scriptPrefix', 'secretPrefix')
SPEC_LINE = re.compile(r'^\s*spec\.(\w+)\["(\w+)"\]\s*=\s*(.+?);', re.M)

HEADER = '''\
# GENERATED FILE - do not edit by hand.
# Source: {source}
# Regenerate with: python3 lynx/tools/sync_chainparams.py

\'\'\'Coin classes for the Lynx-family chains (see coins_lynx.py).\'\'\'

from electrumx.lib.coins_lynx import {imports}

__all__ = [{names}
]
'''

CLASS = '''

class {cls}({bases}):
    NAME = "{name}"
    SHORTNAME = "{symbol}"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("{p2pkh:02x}")
    P2SH_VERBYTES = (bytes.fromhex("{p2sh:02x}"),)
    WIF_BYTE = bytes.fromhex("{wif:02x}")
    GENESIS_HASH = ('{genesis_a}'
                    '{genesis_b}')
    RPC_PORT = {rpc_port}
    PEERS = [{peers}]
'''

PROFILE = '''\
# GENERATED FILE - do not edit by hand. Chain profile for {name}, sourced
# by lynx/build.sh. Regenerate with: python3 lynx/tools/sync_chainparams.py

# Must equal NAME of the coin class in src/electrumx/lib/lynx_chains.py.
COIN_NAME="{name}"

# Where the Spark installer puts the node (bash <(curl -sL install.getlynx.io)).
NODE_SERVICE="{chain}"
NODE_CONF="/var/lib/{chain}/{chain}.conf"
NODE_COOKIE="/var/lib/{chain}/.cookie"

# Electrum ports: the chain's P2P port ({p2p}) + {ssl_offset}, + {wss_offset} and + {admin_offset}.
# Only TLS is public; the admin port is local to the server.
SSL_PORT={ssl}
WSS_PORT={wss}
ADMIN_PORT={admin}

# Warn (not fail) below these. Estimates; revisit after the first full sync.
MIN_DISK_GB={min_disk_gb}
MIN_RAM_GB={min_ram_gb}

# ElectrumX UTXO/history cache while indexing, in MB.
CACHE_MB={cache_mb}
'''


def fetch(url, accept=None):
    req = urllib.request.Request(url, headers={'Accept': accept} if accept else {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def load_source(args):
    if args.file:
        return Path(args.file).read_text(), f'{args.file} (local file)'
    sha = fetch(f'https://api.github.com/repos/{REPO}/commits/{args.ref}',
                accept='application/vnd.github.sha').strip()
    text = fetch(f'https://raw.githubusercontent.com/{REPO}/{sha}/{SOURCE_PATH}')
    return text, f'https://github.com/{REPO}/blob/{sha}/{SOURCE_PATH}'


def parse_specs(text):
    '''Return {chain: {field: value}} from LoadHardcodedChainSpecs().'''
    start = text.find('static void LoadHardcodedChainSpecs')
    if start < 0:
        sys.exit('LoadHardcodedChainSpecs() not found in chainparams.cpp')
    end = text.find('\n}\n', start)
    specs = {}
    for field, chain, value in SPEC_LINE.findall(text[start:end]):
        specs.setdefault(chain, {})[field] = value.strip().strip('"')
    for chain_id, spec in specs.items():
        missing = [field for field in REQUIRED if field not in spec]
        if missing:
            sys.exit(f'{chain_id}: missing {", ".join(missing)} in chainparams.cpp')
    return specs


def electrum_ports(spec):
    p2p = int(spec['nDefaultPort'])
    return p2p + SSL_OFFSET, p2p + WSS_OFFSET, p2p + ADMIN_OFFSET


def check_ports(specs):
    '''Every node and Electrum port of every chain must be unique, so any
    set of chains can share a server.'''
    owner = {}
    for chain_id, spec in sorted(specs.items()):
        ssl, wss, admin = electrum_ports(spec)
        for label, port in (('P2P', spec['nDefaultPort']), ('RPC', spec['nRPCPort']),
                            ('onion', spec['nOnionPort']), ('Electrum SSL', ssl),
                            ('Electrum WSS', wss), ('Electrum admin', admin)):
            port = int(port)
            if not 0 < port < 65536:
                sys.exit(f'{chain_id} {label} port {port} is out of range')
            if port in owner:
                sys.exit(f'port {port} is used by both {owner[port]} and {chain_id} {label}')
            owner[port] = f'{chain_id} {label}'


def display_name(chain_id, spec):
    name = spec.get('displayName') or chain_id.capitalize()
    if not name.isidentifier():
        sys.exit(f'{chain_id}: display name {name!r} is not a valid class name')
    return name


def chain_class(chain_id, spec, extra):
    genesis = spec['genesishash'].removeprefix('0x').lower()
    if not re.fullmatch('[0-9a-f]{64}', genesis):
        sys.exit(f'{chain_id}: bad genesis hash {spec["genesishash"]!r}')
    name = display_name(chain_id, spec)
    ssl, _, _ = electrum_ports(spec)
    peers = [f'{host} s{ssl}' for host in SHARED_SERVERS] + extra.get('peers', [])
    return CLASS.format(
        cls=name,
        name=name,
        symbol=spec['coinSymbol'],
        p2pkh=int(spec['pubkeyPrefix']),
        p2sh=int(spec['scriptPrefix']),
        wif=int(spec['secretPrefix']),
        genesis_a=genesis[:32],
        genesis_b=genesis[32:],
        rpc_port=int(spec['nRPCPort']),
        bases=', '.join(extra.get('mixins', []) + ['LynxFamily']),
        peers=''.join(f'\n        {json.dumps(peer)},' for peer in peers) + '\n    ',
    )


def chain_profile(chain_id, spec, extra):
    ssl, wss, admin = electrum_ports(spec)
    return PROFILE.format(
        name=display_name(chain_id, spec), chain=chain_id, p2p=spec['nDefaultPort'],
        ssl_offset=SSL_OFFSET, wss_offset=WSS_OFFSET, admin_offset=ADMIN_OFFSET,
        ssl=ssl, wss=wss, admin=admin, **extra['size'])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--ref', default='main', help='getlynx/Lynx branch, tag or commit')
    parser.add_argument('--file', help='read a local chainparams.cpp instead of GitHub')
    args = parser.parse_args()

    text, source = load_source(args)
    specs = parse_specs(text)
    unknown = sorted(set(CHAINS) - set(specs))
    if unknown:
        sys.exit(f'chains not in chainparams.cpp: {", ".join(unknown)}')
    check_ports(specs)

    classes, names = [], []
    mixins = sorted({m for extra in CHAINS.values() for m in extra.get('mixins', [])})
    for chain_id, extra in CHAINS.items():
        spec = specs[chain_id]
        names.append(display_name(chain_id, spec))
        classes.append(chain_class(chain_id, spec, extra))
        (PROFILES / f'{chain_id}.env').write_text(chain_profile(chain_id, spec, extra))
        ssl, wss, admin = electrum_ports(spec)
        print(f'{names[-1]:12} rpc={spec["nRPCPort"]:>5}  electrum ssl={ssl} wss={wss} admin={admin}')
    header = HEADER.format(source=source, names=''.join(f'\n    {n!r},' for n in names),
                           imports=', '.join(mixins + ['LynxFamily']))
    OUTPUT.write_text(header + ''.join(classes))

    skipped = sorted(set(specs) - set(CHAINS))
    print(f'wrote {OUTPUT.relative_to(ROOT)} and lynx/chains/*.env from {source}')
    if skipped:
        print(f'not enabled in CHAINS: {", ".join(skipped)}')
    print('next: git diff, then pytest')


if __name__ == '__main__':
    main()
