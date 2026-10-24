#!/usr/bin/env python3
'''Regenerate src/electrumx/lib/lynx_chains.py from getlynx/Lynx chainparams.

getlynx/Lynx src/kernel/chainparams.cpp is the source of truth for every
chain's ports, address prefixes and genesis hash. Run this by hand whenever
that file changes or a chain is added below, then review with `git diff`
and run pytest.

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
OUTPUT = Path(__file__).resolve().parents[2] / 'src/electrumx/lib/lynx_chains.py'

# Chains that get an ElectrumX coin class, keyed by chain id in
# chainparams.cpp. Everything here is what chainparams.cpp does not know.
CHAINS = {
    'lynx': {
        'peers': [
            'electrum5.getlynx.io s',
            'electrum6.getlynx.io s',
            'electrum7.getlynx.io s',
            'electrum8.getlynx.io s',
            'electrum9.getlynx.io s',
        ],
    },
}

REQUIRED = ('coinSymbol', 'genesishash', 'nRPCPort',
            'pubkeyPrefix', 'scriptPrefix', 'secretPrefix')
SPEC_LINE = re.compile(r'^\s*spec\.(\w+)\["(\w+)"\]\s*=\s*(.+?);', re.M)

HEADER = '''\
# GENERATED FILE - do not edit by hand.
# Source: {source}
# Regenerate with: python3 lynx/tools/sync_chainparams.py

\'\'\'Coin classes for the Lynx-family chains (see coins_lynx.py).\'\'\'

from electrumx.lib.coins_lynx import LynxFamily

__all__ = [{names}]
'''

CLASS = '''

class {cls}(LynxFamily):
    NAME = "{name}"
    SHORTNAME = "{symbol}"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("{p2pkh:02x}")
    P2SH_VERBYTES = (bytes.fromhex("{p2sh:02x}"),)
    WIF_BYTE = bytes.fromhex("{wif:02x}")
    GENESIS_HASH = ('{genesis_a}'
                    '{genesis_b}')
    RPC_PORT = {rpc_port}
    PEERS = [
{peers}
    ]
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
    return specs


def chain_class(chain_id, spec, extra):
    missing = [field for field in REQUIRED if field not in spec]
    if missing:
        sys.exit(f'{chain_id}: missing {", ".join(missing)} in chainparams.cpp')
    genesis = spec['genesishash'].removeprefix('0x').lower()
    if not re.fullmatch('[0-9a-f]{64}', genesis):
        sys.exit(f'{chain_id}: bad genesis hash {spec["genesishash"]!r}')
    name = spec.get('displayName') or chain_id.capitalize()
    if not name.isidentifier():
        sys.exit(f'{chain_id}: display name {name!r} is not a valid class name')
    return name, CLASS.format(
        cls=name,
        name=name,
        symbol=spec['coinSymbol'],
        p2pkh=int(spec['pubkeyPrefix']),
        p2sh=int(spec['scriptPrefix']),
        wif=int(spec['secretPrefix']),
        genesis_a=genesis[:32],
        genesis_b=genesis[32:],
        rpc_port=int(spec['nRPCPort']),
        peers='\n'.join(f'        {json.dumps(peer)},' for peer in extra['peers']),
    )


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

    out, names = [], []
    for chain_id, extra in CHAINS.items():
        name, code = chain_class(chain_id, specs[chain_id], extra)
        names.append(name)
        out.append(code)
        print(f'{name:12} rpc={specs[chain_id]["nRPCPort"]:>5}  genesis={specs[chain_id]["genesishash"][:18]}...')
    header = HEADER.format(source=source, names=', '.join(repr(n) for n in names))
    OUTPUT.write_text(header + ''.join(out))

    skipped = sorted(set(specs) - set(CHAINS))
    print(f'wrote {OUTPUT.relative_to(OUTPUT.parents[3])} from {source}')
    if skipped:
        print(f'not enabled in CHAINS: {", ".join(skipped)}')
    print('next: git diff, then pytest')


if __name__ == '__main__':
    main()
