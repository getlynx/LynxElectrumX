#!/usr/bin/env python3
'''Check how a server treats one heavy client, to choose COST_SOFT_LIMIT and
COST_HARD_LIMIT.

ElectrumX charges each session for its requests and groups sessions by IP
range. Above COST_SOFT_LIMIT it slows a client down; above COST_HARD_LIMIT it
disconnects it. This opens SESSIONS connections from this machine, has each
subscribe to SCRIPTHASHES real scripthashes and fetch their history, and
reports timings and any throttling or disconnects, like a wallet or partner
service watching many addresses would see.

Only run this against your own servers.

    python3 lynx/tools/load_test.py electrum10.getlynx.io --sessions 1 --scripthashes 1000 \
        --source electrum5.getlynx.io

Test addresses are collected from --source (default: the server itself), so
the collection does not count against the tested server's limits. Only
addresses with at most --max-history transactions are used, like an ordinary
wallet's.
'''

import argparse
import asyncio
import random
import statistics
import time

from compare_servers import RPCError, Server, scripthash


async def find_scripthashes(server, wanted, max_history, rng):
    '''Scripthashes with small histories, paid to by transactions in random blocks.'''
    tip = (await server.call('blockchain.headers.subscribe'))['height']
    found, seen = [], set()
    while len(found) < wanted:
        height = rng.randint(1, tip - 6)
        for pos in range(8):
            try:
                txid = await server.call('blockchain.transaction.id_from_pos', [height, pos])
            except RPCError:
                break
            tx = await server.call('blockchain.transaction.get', [txid, True])
            for out in tx.get('vout', []):
                script = out.get('scriptPubKey', {}).get('hex')
                if not script or script in seen:
                    continue
                seen.add(script)
                sh = scripthash(script)
                try:
                    history = await server.call('blockchain.scripthash.get_history', [sh])
                except RPCError:
                    continue    # too large
                if len(history) <= max_history:
                    found.append(sh)
        print(f'  {len(found)} found', end='\r')
    print()
    return found[:wanted]


async def run_session(args, number, hashes, results):
    timings, errors = [], []
    start = time.monotonic()
    try:
        server = await Server(args.server, args.insecure).connect(['1.4', '1.6'])
        await server.call('blockchain.headers.subscribe')
        for sh in hashes:
            t = time.monotonic()
            await server.call('blockchain.scripthash.subscribe', [sh])
            await server.call('blockchain.scripthash.get_history', [sh])
            timings.append(time.monotonic() - t)
            if len(timings) % 100 == 0:
                recent = timings[-100:]
                print(f'  session {number}: {len(timings):5} done, last 100 median '
                      f'{statistics.median(recent) * 1000:.0f} ms')
        await server.close()
    except (RPCError, ConnectionError, OSError, asyncio.TimeoutError) as e:
        errors.append(f'{type(e).__name__}: {e}')
    results.append((number, time.monotonic() - start, timings, errors))


async def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('server', help='host[:port] (default port 50002)')
    parser.add_argument('--sessions', type=int, default=5)
    parser.add_argument('--scripthashes', type=int, default=100, help='per session')
    parser.add_argument('--source', help='server to collect test addresses from (default: server)')
    parser.add_argument('--max-history', type=int, default=50, help='largest history to use')
    parser.add_argument('--insecure', action='store_true', help='accept self-signed certificates')
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    source = args.source or args.server
    print(f'Collecting {args.scripthashes * args.sessions} scripthashes from {source}...')
    finder = await Server(source, args.insecure).connect(['1.4', '1.4.2'])
    hashes = await find_scripthashes(finder, args.scripthashes * args.sessions, args.max_history, rng)
    await finder.close()

    print(f'Running {args.sessions} sessions x {args.scripthashes} scripthashes')
    results = []
    per = args.scripthashes
    await asyncio.gather(*(run_session(args, n, hashes[n * per:(n + 1) * per], results)
                           for n in range(args.sessions)))

    all_timings = [t for _, _, timings, _ in results for t in timings]
    failed = [(n, errors) for n, _, _, errors in results if errors]
    for n, elapsed, timings, errors in sorted(results):
        status = errors[0] if errors else 'ok'
        print(f'  session {n:3}: {len(timings):5} done in {elapsed:6.1f}s  {status}')
    if all_timings:
        q = statistics.quantiles(all_timings, n=20, method='inclusive') if len(all_timings) > 1 else all_timings * 19
        print(f'per scripthash: median {statistics.median(all_timings) * 1000:.0f} ms, '
              f'p95 {q[18] * 1000:.0f} ms, max {max(all_timings) * 1000:.0f} ms')
    print(f'{args.sessions - len(failed)} of {args.sessions} sessions completed')
    print('Then check the server side: electrumx_rpc sessions  (cost, and any throttling)')


if __name__ == '__main__':
    asyncio.run(main())
