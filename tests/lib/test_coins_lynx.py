import re
from pathlib import Path

import pytest

from electrumx.lib import coins, lynx_chains
from electrumx.lib.coins import Coin
from electrumx.lib.coins_lynx import LynxFamily
from electrumx.lib.util import subclasses


@pytest.mark.parametrize('name', ['Lynx', 'lynx', 'LYNX'])
def test_lookup_finds_generated_class(name):
    assert Coin.lookup_coin_class(name, 'mainnet') is lynx_chains.Lynx


def test_no_duplicate_coin_names():
    # lookup_coin_class() returns the first match in alphabetical class-name
    # order, so a second class with the same NAME (e.g. upstream's Lynx coming
    # back in a merge) could silently win.
    seen = {}
    for coin in subclasses(Coin):
        if coin.NET is None:
            continue
        key = (coin.NAME.lower(), coin.NET.lower())
        assert key not in seen, f'{coin.__name__} duplicates {seen[key].__name__}'
        seen[key] = coin


@pytest.mark.parametrize('coin', [getattr(lynx_chains, name) for name in lynx_chains.__all__])
def test_lynx_family_shape(coin):
    assert issubclass(coin, LynxFamily)
    assert getattr(coins, coin.__name__) is coin
    assert coin.SESSIONCLS.protocol_min_max_strings() == ('1.4', '1.6')
    assert len(bytes.fromhex(coin.GENESIS_HASH)) == 32


# Lynx P2PKH prefix 45 ("K") and P2SH prefix 22 ("A"). The hash160s and
# hashXs are the ones upstream uses for Litecoin in test_addresses.py; the
# first address is a real, funded mainnet address.
addresses = [
    ("KNHcTfPz5pdQtAq3DTbtG8bSkdNCaKe7iG",
     "76a914a56237227f25774aabdd47d95ae9564d339b018a88ac", "4b4269614898f03be53ef0"),
    ("KAAMdC1heBS3Zr6Gbj5gRnwewE2J6TJ8q4",
     "76a914206168f5322583ff37f8e55665a4789ae896353288ac", "b8cb80b26e8932f5b12a7e"),
    ("A7hgJMpCyjHyRXWBCVy6eAK7s1pjnjGUcn",
     "a914a773db925b09add367dcc253c1f9bbc1d11ec6fd87", "062d8515e50cb92b8a3a73"),
]


@pytest.mark.parametrize('address,script,hashX', addresses)
def test_lynx_addresses(address, script, hashX):
    coin = lynx_chains.Lynx
    assert coin.pay_to_address_script(address).hex() == script
    assert coin.address_to_hashX(address).hex() == hashX


CHAINS_DIR = Path(__file__).resolve().parents[2] / 'lynx' / 'chains'


def test_every_chain_has_a_profile():
    profiles = {}
    for path in CHAINS_DIR.glob('*.env'):
        match = re.search(r'^COIN_NAME="([^"]+)"', path.read_text(), re.M)
        assert match, f'{path.name} has no COIN_NAME'
        profiles[path.stem] = match.group(1)
    assert sorted(profiles.values()) == sorted(lynx_chains.__all__)
    for chain_id, coin_name in profiles.items():
        assert Coin.lookup_coin_class(coin_name, 'mainnet').NAME == coin_name
        assert chain_id == coin_name.lower()


def test_infiniloop_genesis_uses_scrypt_hash():
    # Version-1 genesis header rebuilt from getlynx/Lynx chainparams.cpp
    # (timestamp 1609281149, nBits 0x1e0fffff, nonce 703813). Blocks with
    # nVersion <= 6 are identified by their scrypt hash; the block fixtures
    # are all version 7 or later, so this is the only check of that rule.
    header = bytes.fromhex(
        '01000000' + '00' * 32
        + '745c0132ab3a421ebdd110b6303bee9d562613d3d35e91751497c90856c944ab'
        + '7daeeb5f' + 'ffff0f1e' + '45bd0a00')
    coin = lynx_chains.InfiniLooP
    assert coin.header_hash_rev(header)[::-1].hex() == coin.GENESIS_HASH
