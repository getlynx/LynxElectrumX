# GENERATED FILE - do not edit by hand.
# Source: https://github.com/getlynx/Lynx/blob/a9285182c3feeabad4c3949ec841bc2e6c80ebce/src/kernel/chainparams.cpp
# Regenerate with: python3 lynx/tools/sync_chainparams.py

'''Coin classes for the Lynx-family chains (see coins_lynx.py).'''

from electrumx.lib.coins_lynx import LynxFamily

__all__ = ['Lynx']


class Lynx(LynxFamily):
    NAME = "Lynx"
    SHORTNAME = "LYNX"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("2d")
    P2SH_VERBYTES = (bytes.fromhex("16"),)
    WIF_BYTE = bytes.fromhex("ad")
    GENESIS_HASH = ('984b30fc9bb5e5ff424ad7f4ec193053'
                    '8a7b14a2d93e58ad7976c23154ea4a76')
    RPC_PORT = 8332
    PEERS = [
        "electrum5.getlynx.io s",
        "electrum6.getlynx.io s",
        "electrum7.getlynx.io s",
        "electrum8.getlynx.io s",
        "electrum9.getlynx.io s",
    ]
