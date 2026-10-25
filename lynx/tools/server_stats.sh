#!/bin/bash
# Measure how a LynxElectrumX server copes with memory, for sizing decisions.
#
#   server_stats.sh [minutes]      # default 10; samples every 5 seconds
#
# Prints a snapshot (memory per ElectrumX and node, disk) and a summary of
# the sampling period. Run it on each server under the same conditions
# (e.g. at rest, then during a load test) and compare.
#
# What matters most:
#   memory pressure  share of time tasks stalled waiting for memory
#                    (/proc/pressure/memory). Near 0 is healthy; "full"
#                    above ~1% means clients wait.
#   swap-in rate     pages read back from swap. Swap-out of idle pages is
#                    harmless; steady swap-in means the working set does not
#                    fit in RAM.
#   available RAM    headroom left for growth.

set -euo pipefail

minutes="${1:-10}"
interval=5
samples=$(( minutes * 60 / interval ))

mem_kb() { awk -v k="$1:" '$1 == k { print $2 }' /proc/meminfo; }
vmstat_val() { awk -v k="$1" '$1 == k { print $2 }' /proc/vmstat; }
# Cumulative stall time in microseconds; 0 if the kernel has no pressure info.
pressure_total() { sed -n "s/^$2 .*total=\([0-9]*\).*/\1/p" "/proc/pressure/$1" 2>/dev/null || echo 0; }
have_pressure=0
[ -r /proc/pressure/memory ] && have_pressure=1

echo "== $(hostname)  $(date -u '+%F %T UTC')  $(nproc) vCPU  $(awk '/^MemTotal:/ { printf "%.1f GB RAM", $2 / 1048576 }' /proc/meminfo)"
echo
echo "== ElectrumX memory per chain (current / peak / in swap)"
for unit in $(systemctl list-units --plain --no-legend 'electrumx@*' | awk '{ print $1 }'); do
    cur=$(systemctl show -p MemoryCurrent --value "$unit")
    peak=$(systemctl show -p MemoryPeak --value "$unit" 2>/dev/null || echo 0)
    swap=$(systemctl show -p MemorySwapCurrent --value "$unit" 2>/dev/null || echo 0)
    printf '  %-26s %6d MB  %6d MB  %6d MB\n' "$unit" $(( ${cur/\[not set\]/0} / 1048576 )) \
        $(( ${peak/\[not set\]/0} / 1048576 )) $(( ${swap/\[not set\]/0} / 1048576 ))
done
echo
echo "== Nodes (resident memory)"
ps -eo rss=,args= | awk '/-datadir=\/var\/lib\// && !/awk/ {
    match($0, /-datadir=[^ ]+/); printf "  %-26s %6d MB\n", substr($0, RSTART + 9, RLENGTH - 9), $1 / 1024 }' | sort -k2 -n
echo
echo "== Disk"
df -h / | tail -1 | awk '{ print "  root filesystem: " $3 " used of " $2 " (" $5 ")" }'
printf '  ElectrumX databases: %s\n' "$(du -sh /db 2>/dev/null | cut -f1)"
echo

echo "== Sampling for $minutes minute(s), every ${interval}s ..."
min_avail=999999999 max_avail=0 sum_avail=0 max_swap=0
pswpin0=$(vmstat_val pswpin) pswpout0=$(vmstat_val pswpout)
mem_some0=$(pressure_total memory some) mem_full0=$(pressure_total memory full)
io_some0=$(pressure_total io some)
start=$(date +%s)
for ((i = 0; i < samples; i++)); do
    avail=$(mem_kb MemAvailable)
    swap_used=$(( $(mem_kb SwapTotal) - $(mem_kb SwapFree) ))
    (( avail < min_avail )) && min_avail=$avail
    (( avail > max_avail )) && max_avail=$avail
    (( swap_used > max_swap )) && max_swap=$swap_used
    sum_avail=$(( sum_avail + avail ))
    sleep "$interval"
done
elapsed=$(( $(date +%s) - start ))
elapsed_us=$(( elapsed * 1000000 ))
total_kb=$(mem_kb MemTotal)

pct() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.2f%%", (b > 0 ? 100 * a / b : 0) }'; }
echo
echo "== Summary over ${elapsed}s"
printf '  available RAM     min %.1f GB  avg %.1f GB  max %.1f GB   (min = %s of total)\n' \
    "$(awk -v v="$min_avail" 'BEGIN { print v / 1048576 }')" \
    "$(awk -v v="$sum_avail" -v n="$samples" 'BEGIN { print v / n / 1048576 }')" \
    "$(awk -v v="$max_avail" 'BEGIN { print v / 1048576 }')" "$(pct "$min_avail" "$total_kb")"
printf '  swap in use       max %.2f GB\n' "$(awk -v v="$max_swap" 'BEGIN { print v / 1048576 }')"
printf '  swap-in           %d pages (%.1f per second)   <- should be ~0\n' \
    $(( $(vmstat_val pswpin) - pswpin0 )) "$(awk -v d=$(( $(vmstat_val pswpin) - pswpin0 )) -v t="$elapsed" 'BEGIN { print d / t }')"
printf '  swap-out          %d pages (%.1f per second)\n' \
    $(( $(vmstat_val pswpout) - pswpout0 )) "$(awk -v d=$(( $(vmstat_val pswpout) - pswpout0 )) -v t="$elapsed" 'BEGIN { print d / t }')"
if [ "$have_pressure" = 1 ]; then
    printf '  memory pressure   some %s  full %s   <- full should be ~0\n' \
        "$(pct $(( $(pressure_total memory some) - mem_some0 )) "$elapsed_us")" \
        "$(pct $(( $(pressure_total memory full) - mem_full0 )) "$elapsed_us")"
    printf '  I/O pressure      some %s\n' "$(pct $(( $(pressure_total io some) - io_some0 )) "$elapsed_us")"
else
    echo "  memory pressure   not available (kernel without /proc/pressure)"
fi
printf '  load average      %s (%d vCPU)\n' "$(cut -d' ' -f1-3 /proc/loadavg)" "$(nproc)"
