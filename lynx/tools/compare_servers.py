#!/usr/bin/env python3
'''Compare two Electrum servers' answers to the same requests.

Meant for checking a new LynxElectrumX server against an existing one before
moving DNS. Both servers are asked the same questions at a protocol version
they both speak; answers that must match are compared, answers that may
legitimately differ (versions, banners, fees, mempool) are only shown.

    python3 lynx/tools/compare_servers.py electrum5.getlynx.io electrum10.getlynx.io
    python3 lynx/tools/compare_servers.py old.example:50002 new.example:50002 --samples 50

The test data comes from the chain itself: blocks at random heights, their
first transactions, and the scripts those transactions pay to. Results are
compared only up to a height both servers have indexed, so a new server that
is still syncing can be checked too.

Exit status: 0 if nothing differed unexpectedly, 1 otherwise.
'''

import argparse
import asyncio
import hashlib
import json
import random
import ssl
import sys

COMPARE_PROTOCOL = ['1.4', '1.4.2']   # what ElectrumX 1.16 servers speak
CONFIRMATIONS = 6                     # stay this far below the lower tip


class RPCError(Exception):
    pass


class Server:
    def __init__(self, spec, insecure):
        host, _, port = spec.partition(':')
        self.host, self.port = host, int(port or 50002)
        self.insecure = insecure
        self.pending = {}
        self.next_id = 0

    def __str__(self):
        return f'{self.host}:{self.port}'

    async def connect(self, versions):
        ctx = ssl.create_default_context()
        if self.insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port, ssl=ctx, limit=1 << 26)
        self.read_task = asyncio.create_task(self._read())
        self.version = await self.call('server.version', ['compare_servers', versions])
        return self

    async def _read(self):
        try:
            while line := await self.reader.readline():
                msg = json.loads(line)
                future = self.pending.pop(msg.get('id'), None)
                if future and not future.done():
                    future.set_result(msg)
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(ConnectionError(f'{self} closed the connection'))

    async def call(self, method, params=()):
        self.next_id += 1
        future = asyncio.get_running_loop().create_future()
        self.pending[self.next_id] = future
        request = {'jsonrpc': '2.0', 'id': self.next_id, 'method': method, 'params': list(params)}
        self.writer.write(json.dumps(request).encode() + b'\n')
        await self.writer.drain()
        msg = await asyncio.wait_for(future, 120)
        if msg.get('error'):
            raise RPCError(msg['error'])
        return msg['result']

    async def attempt(self, method, params=()):
        '''Like call(), but return errors as values so they can be compared.'''
        try:
            return await self.call(method, params)
        except RPCError as e:
            return {'error': e.args[0].get('message') if isinstance(e.args[0], dict) else str(e)}

    async def close(self):
        self.read_task.cancel()
        self.writer.close()


class Report:
    def __init__(self, verbose):
        self.verbose = verbose
        self.same = self.diffs = 0

    def compare(self, label, a, b):
        if a == b:
            self.same += 1
            if self.verbose:
                print(f'  same  {label}')
        else:
            self.diffs += 1
            print(f'  DIFF  {label}\n          old: {short(a)}\n          new: {short(b)}')

    def show(self, label, a, b):
        print(f'  info  {label}\n          old: {short(a)}\n          new: {short(b)}')

    def check(self, label, ok, detail):
        if ok:
            self.same += 1
            print(f'  ok    {label}: {short(detail)}')
        else:
            self.diffs += 1
            print(f'  FAIL  {label}: {short(detail)}')


def short(value, limit=160):
    text = json.dumps(value, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + f'... ({len(text)} chars)'


def scripthash(script_hex):
    return hashlib.sha256(bytes.fromhex(script_hex)).digest()[::-1].hex()


def confirmed(entries, max_height):
    '''History/UTXO entries mined at or below max_height (drops mempool).'''
    return sorted((e for e in entries if 0 < e['height'] <= max_height),
                  key=lambda e: (e['height'], e['tx_hash'], e.get('tx_pos', 0)))


async def both(old, new, method, params=()):
    return await asyncio.gather(old.attempt(method, params), new.attempt(method, params))


async def compare_servers(args):
    report = Report(args.verbose)
    old = await Server(args.old, args.insecure).connect(COMPARE_PROTOCOL)
    new = await Server(args.new, args.insecure).connect(COMPARE_PROTOCOL)

    print('Server')
    report.show('server.version', old.version, new.version)
    f_old, f_new = await both(old, new, 'server.features')
    for key in ('genesis_hash', 'hash_function', 'pruning'):
        report.compare(f'server.features {key}', f_old.get(key), f_new.get(key))
    for key in ('server_version', 'protocol_min', 'protocol_max', 'hosts'):
        report.show(f'server.features {key}', f_old.get(key), f_new.get(key))
    for method in ('server.banner', 'server.donation_address'):
        report.show(method, *await both(old, new, method))
    p_old, p_new = await both(old, new, 'server.peers.subscribe')
    report.show('server.peers.subscribe', [p[1] for p in p_old], [p[1] for p in p_new])

    print('Headers')
    t_old, t_new = await both(old, new, 'blockchain.headers.subscribe')
    tips_equal = t_old['height'] == t_new['height']
    height = min(t_old['height'], t_new['height']) - CONFIRMATIONS
    report.show('tip height', t_old['height'], t_new['height'])
    print(f'  comparing up to height {height:,}')
    rng = random.Random(args.seed)
    heights = sorted({0, 1, height} | {rng.randint(1, height) for _ in range(args.samples)})
    for h in heights:
        report.compare(f'block.header {h}', *await both(old, new, 'blockchain.block.header', [h]))
    for h in heights[1:4]:
        report.compare(f'block.header {h} cp_height={height}',
                       *await both(old, new, 'blockchain.block.header', [h, height]))
    for h in heights[1:4]:
        a, b = await both(old, new, 'blockchain.block.headers', [h, 50])
        report.compare(f'block.headers {h}+50', (a.get('count'), a.get('hex')), (b.get('count'), b.get('hex')))

    print('Transactions')
    scripthashes = set()
    for h in heights[1:]:
        for pos in (0, 1):
            a, b = await both(old, new, 'blockchain.transaction.id_from_pos', [h, pos, True])
            if 'error' in a and 'error' in b:
                continue    # block has no transaction at this position
            report.compare(f'transaction.id_from_pos {h} {pos}', a, b)
            txid = a['tx_hash'] if 'tx_hash' in a else a
            report.compare(f'transaction.get {txid[:16]}',
                           *await both(old, new, 'blockchain.transaction.get', [txid]))
            report.compare(f'transaction.get_merkle {txid[:16]}',
                           *await both(old, new, 'blockchain.transaction.get_merkle', [txid, h]))
            v_old, v_new = await both(old, new, 'blockchain.transaction.get', [txid, True])
            for v in (v_old, v_new):
                v.pop('confirmations', None)    # depends on each server's tip
            if v_old != v_new:
                report.show(f'transaction.get verbose {txid[:16]} (passed through from the node)', v_old, v_new)
            for out in v_old.get('vout', []):
                script = out.get('scriptPubKey', {}).get('hex')
                if script:
                    scripthashes.add(scripthash(script))

    print(f'Scripthashes ({len(scripthashes)} found in the sampled transactions)')
    for sh in sorted(scripthashes)[:args.max_scripthashes]:
        label = sh[:16]
        a, b = await both(old, new, 'blockchain.scripthash.get_history', [sh])
        if 'error' in a or 'error' in b:
            report.compare(f'scripthash.get_history {label}', a, b)
            continue
        report.compare(f'scripthash.get_history {label}', confirmed(a, height), confirmed(b, height))
        a, b = await both(old, new, 'blockchain.scripthash.listunspent', [sh])
        report.compare(f'scripthash.listunspent {label}', confirmed(a, height), confirmed(b, height))
        if tips_equal:
            report.compare(f'scripthash.get_balance {label}',
                           *await both(old, new, 'blockchain.scripthash.get_balance', [sh]))

    print('Fees and mempool (depend on each node, shown only)')
    report.show('blockchain.estimatefee 2', *await both(old, new, 'blockchain.estimatefee', [2]))
    report.show('blockchain.relayfee', *await both(old, new, 'blockchain.relayfee'))
    histograms = await both(old, new, 'mempool.get_fee_histogram')
    report.show('mempool.get_fee_histogram (entries)', *[len(h) if isinstance(h, list) else h for h in histograms])

    await old.close()
    await new.close()
    return report


async def check_new_protocols(args, report):
    '''Newer-protocol behaviour of the new server on its own.'''
    print('New server at its highest protocol')
    new = await Server(args.new, args.insecure).connect(['1.4', '1.7'])
    report.show('server.version 1.4-1.7', None, new.version)
    if new.version[1] >= '1.6':
        info = await new.attempt('mempool.get_info')
        report.check('mempool.get_info (1.6)', 'error' not in info, info)
    # Lynx-family servers cap the protocol at 1.6 because the node cannot
    # answer blockchain.outpoint.* correctly; the method must be refused.
    outpoint = await new.attempt('blockchain.outpoint.subscribe', ['00' * 32, 0])
    report.check('blockchain.outpoint.subscribe is refused', 'error' in outpoint, outpoint)
    await new.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('old', help='existing server, host[:port] (default port 50002)')
    parser.add_argument('new', help='server under test, host[:port]')
    parser.add_argument('--samples', type=int, default=20, help='random block heights to check')
    parser.add_argument('--max-scripthashes', type=int, default=40)
    parser.add_argument('--seed', type=int, help='random seed, to repeat a run exactly')
    parser.add_argument('--insecure', action='store_true', help='accept self-signed certificates')
    parser.add_argument('-v', '--verbose', action='store_true', help='also list matching answers')
    args = parser.parse_args()
    if args.seed is None:
        args.seed = random.randrange(1 << 32)
    print(f'old: {args.old}   new: {args.new}   seed: {args.seed}\n')

    report = await compare_servers(args)
    await check_new_protocols(args, report)
    print(f'\n{report.same} matched, {report.diffs} differed')
    sys.exit(1 if report.diffs else 0)


if __name__ == '__main__':
    asyncio.run(main())
