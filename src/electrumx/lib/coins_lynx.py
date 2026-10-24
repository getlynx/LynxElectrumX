# Copyright (c) 2026, the Lynx developers
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Hand-maintained pieces shared by every chain built from getlynx/Lynx.

The per-chain classes themselves live in lynx_chains.py, which is generated
by lynx/tools/sync_chainparams.py from getlynx/Lynx src/kernel/chainparams.cpp.
'''

import electrumx.lib.tx as lib_tx
from electrumx.lib.coins import Block, Coin, ScryptMixin
from electrumx.server.session import ElectrumX


class LynxElectrumX(ElectrumX):
    '''Session class for Lynx-family chains.'''

    # Protocol 1.7's blockchain.outpoint.* methods find confirmed spends via
    # gettxspendingprevout, which needs txospenderindex (Bitcoin Core 31+).
    # Lynx Core 28.x lacks it and would report spent outputs as unspent.
    PROTOCOL_MAX = (1, 6)


class LynxFamily(Coin):
    '''Base class for chains built from the Lynx codebase.

    All of them share 80-byte headers, double-SHA256 block hashes and SegWit
    transactions. Proof-of-stake blocks append a block signature after the
    transactions; the deserializer never reads it, so it needs no handling.
    '''

    # Coin.lookup_coin_class() reads NAME on every subclass; NET = None
    # keeps this base class itself from ever being selected.
    NAME = 'LynxFamily'
    NET = None
    SESSIONCLS = LynxElectrumX
    DESERIALIZER = lib_tx.DeserializerSegWit
    TX_COUNT = 1
    TX_COUNT_HEIGHT = 1
    TX_PER_BLOCK = 1
    REORG_LIMIT = 5000


class InfiniLooPMixin(ScryptMixin):
    '''InfiniLooP's history from before it moved to the Lynx codebase.

    Legacy InfiniLooP was Blackcoin-style: blocks with nVersion <= 6 are
    identified by their scrypt hash (ScryptMixin), and transactions up to
    and including LEGACY_TX_HEIGHT carry an nTime field after nVersion.
    Later blocks and the mempool use the normal Lynx (SegWit) format.
    '''

    DESERIALIZER = lib_tx.DeserializerSegWit
    LEGACY_DESERIALIZER = lib_tx.DeserializerTxTime
    # getlynx/Lynx: consensus.infiniloopTransitionHeight
    LEGACY_TX_HEIGHT = 2800000

    @classmethod
    def block(cls, raw_block: bytes, height: int) -> Block:
        if height > cls.LEGACY_TX_HEIGHT:
            return super().block(raw_block, height)
        header = cls.block_header(raw_block, height)
        txs = cls.LEGACY_DESERIALIZER(raw_block, start=len(header)).read_tx_block()
        return Block(raw_block, header, txs)
