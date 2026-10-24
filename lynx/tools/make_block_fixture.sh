#!/bin/bash
# Write a block test fixture (tests/blocks/<chain>_mainnet_<height>.json)
# from a synced Spark node. Run it on any host with the chain installed.
#
#   make_block_fixture.sh <chain> [height ...]    # default: 10 blocks below the tip
#
# Output files go to the current directory; copy them into tests/blocks/.
# The fixture is `getblock <hash> 1` plus the raw block hex as "block".

set -euo pipefail

chain="${1:?usage: $0 <chain> [height ...]}"
shift
cli=("$chain-cli" "-datadir=/var/lib/$chain")
command -v "${cli[0]}" >/dev/null || { echo "ERROR: ${cli[0]} not found" >&2; exit 1; }

heights=("$@")
if [ ${#heights[@]} -eq 0 ]; then
    heights=($(( $("${cli[@]}" getblockcount) - 10 )))
fi

for height in "${heights[@]}"; do
    hash="$("${cli[@]}" getblockhash "$height")"
    raw="$("${cli[@]}" getblock "$hash" 0)"
    out="${chain}_mainnet_${height}.json"
    # Drop the closing brace of the verbose JSON and append the raw block.
    {
        "${cli[@]}" getblock "$hash" 1 | sed '$d'
        printf '  ,"block": "%s"\n}\n' "$raw"
    } > "$out"
    echo "wrote $out ($(( ${#raw} / 2 )) bytes)"
done
