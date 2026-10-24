# GENERATED FILE - do not edit by hand.
# Source: https://github.com/getlynx/Lynx/blob/a9285182c3feeabad4c3949ec841bc2e6c80ebce/src/kernel/chainparams.cpp
# Regenerate with: python3 lynx/tools/sync_chainparams.py

'''Coin classes for the Lynx-family chains (see coins_lynx.py).'''

from electrumx.lib.coins_lynx import InfiniLooPMixin, LynxFamily

__all__ = [
    'Alioth',
    'Borrelly',
    'Cassiopeia',
    'Delphinus',
    'Digitalcoin',
    'Enceladus',
    'Fenrir',
    'Galatea',
    'Halley',
    'Indus',
    'InfiniLooP',
    'Lynx',
]


class Alioth(LynxFamily):
    NAME = "Alioth"
    SHORTNAME = "ALIO"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("d7")
    P2SH_VERBYTES = (bytes.fromhex("ef"),)
    WIF_BYTE = bytes.fromhex("d6")
    GENESIS_HASH = ('fa9f9bd23d7ed9984c1fe756caeaa3af'
                    '9e63887f4b1fe4807f3915af74c61a7b')
    RPC_PORT = 55802
    PEERS = []


class Borrelly(LynxFamily):
    NAME = "Borrelly"
    SHORTNAME = "BORR"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("bd")
    P2SH_VERBYTES = (bytes.fromhex("57"),)
    WIF_BYTE = bytes.fromhex("75")
    GENESIS_HASH = ('c936175d9ea6f49a595f7cd75ce065c5'
                    'bb08ed5abc0e5d8b42b04735d916e4a7')
    RPC_PORT = 58401
    PEERS = []


class Cassiopeia(LynxFamily):
    NAME = "Cassiopeia"
    SHORTNAME = "CASS"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("fc")
    P2SH_VERBYTES = (bytes.fromhex("c1"),)
    WIF_BYTE = bytes.fromhex("88")
    GENESIS_HASH = ('d288cc1734cefc4a36a13c5de8d66335'
                    '6dcc6b1ca7a6d1f0fd3b6a6a34b0d0c3')
    RPC_PORT = 53054
    PEERS = []


class Delphinus(LynxFamily):
    NAME = "Delphinus"
    SHORTNAME = "DELP"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("a3")
    P2SH_VERBYTES = (bytes.fromhex("89"),)
    WIF_BYTE = bytes.fromhex("95")
    GENESIS_HASH = ('2d749f17c25d34c4cd443dc44a0e895e'
                    '99bce4d59a6d38404c2ab4bc3a244237')
    RPC_PORT = 57691
    PEERS = []


class Digitalcoin(LynxFamily):
    NAME = "Digitalcoin"
    SHORTNAME = "DGC"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("1e")
    P2SH_VERBYTES = (bytes.fromhex("05"),)
    WIF_BYTE = bytes.fromhex("80")
    GENESIS_HASH = ('5e039e1ca1dbf128973bf6cff98169e4'
                    '0a1b194c3b91463ab74956f413b2f9c8')
    RPC_PORT = 7998
    PEERS = []


class Enceladus(LynxFamily):
    NAME = "Enceladus"
    SHORTNAME = "ENCE"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("55")
    P2SH_VERBYTES = (bytes.fromhex("76"),)
    WIF_BYTE = bytes.fromhex("8d")
    GENESIS_HASH = ('68274c0a8bcb86634a341a8a98294c48'
                    '83e70953a07f7db6c9982eb1b1a66efe')
    RPC_PORT = 58611
    PEERS = []


class Fenrir(LynxFamily):
    NAME = "Fenrir"
    SHORTNAME = "FENR"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("05")
    P2SH_VERBYTES = (bytes.fromhex("ef"),)
    WIF_BYTE = bytes.fromhex("d0")
    GENESIS_HASH = ('43204086224f60f8ab041f5fc6b3c6b7'
                    '2b01323fb9408fc7c49412d916188c7d')
    RPC_PORT = 54826
    PEERS = []


class Galatea(LynxFamily):
    NAME = "Galatea"
    SHORTNAME = "GALA"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("4a")
    P2SH_VERBYTES = (bytes.fromhex("33"),)
    WIF_BYTE = bytes.fromhex("97")
    GENESIS_HASH = ('0ea1f114252089752aa0016f27d7e8fa'
                    'ee61a8e7586700b2a87c7b368eb7468d')
    RPC_PORT = 55786
    PEERS = []


class Halley(LynxFamily):
    NAME = "Halley"
    SHORTNAME = "HALL"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("36")
    P2SH_VERBYTES = (bytes.fromhex("3f"),)
    WIF_BYTE = bytes.fromhex("78")
    GENESIS_HASH = ('77fe25810bdd8930db8e69fd85b7912a'
                    '984a6a362ad8b2e528f3bd765c02a778')
    RPC_PORT = 53837
    PEERS = []


class Indus(LynxFamily):
    NAME = "Indus"
    SHORTNAME = "INDU"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("0c")
    P2SH_VERBYTES = (bytes.fromhex("0b"),)
    WIF_BYTE = bytes.fromhex("7e")
    GENESIS_HASH = ('18d80573782f9dfc69e2230a876f86e5'
                    '87f081ef3eb1ab81ca66a20d6625f00a')
    RPC_PORT = 54701
    PEERS = []


class InfiniLooP(InfiniLooPMixin, LynxFamily):
    NAME = "InfiniLooP"
    SHORTNAME = "IL8P"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("21")
    P2SH_VERBYTES = (bytes.fromhex("55"),)
    WIF_BYTE = bytes.fromhex("99")
    GENESIS_HASH = ('000001ed1ed7503c6ef472314d8138b7'
                    '440ebd0c5c8b539481705032bbed295a')
    RPC_PORT = 9459
    PEERS = []


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
