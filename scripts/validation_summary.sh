#!/bin/bash
# Quick validation summary script
# Usage: ./validation_summary.sh <validation_dir>

VALIDATION_DIR="${1:-logs/run_validation/lunarmodules__Penlight.bd26cb9e}"

cd "$VALIDATION_DIR" 2>/dev/null || { echo "Directory not found: $VALIDATION_DIR"; exit 1; }

echo "=== Validation Summary ==="
echo

# Count totals
total=$(ls -1d */ 2>/dev/null | wc -l | tr -d ' ')
valid=0
invalid=0

for dir in */; do
    if [ -f "$dir/report.json" ]; then
        f2p=$(jq '.["FAIL_TO_PASS"] | length' "$dir/report.json" 2>/dev/null)
        p2p=$(jq '.["PASS_TO_PASS"] | length' "$dir/report.json" 2>/dev/null)
        if [ "$f2p" != "null" ] && [ "$f2p" -gt 0 ] && [ "$p2p" != "null" ] && [ "$p2p" -gt 0 ]; then
            valid=$((valid+1))
        else
            invalid=$((invalid+1))
        fi
    fi
done

# Overall stats
echo "Overall Statistics:"
echo "  Total validated: $total"
echo "  Valid bugs (F2P > 0 and P2P > 0): $valid"
echo "  Invalid bugs: $invalid"
if [ $((valid + invalid)) -gt 0 ]; then
    success_rate=$(awk "BEGIN {printf \"%.2f\", $valid * 100 / ($valid + $invalid)}")
    echo "  Success rate: ${success_rate}%"
fi
echo

# Breakdown by type
echo "Valid Bugs by Type:"
for type in ctrl_invert_if flip_operators op_change op_change_const remove_cond remove_loop ctrl_shuffle lm_rewrite lm_modify; do
    count=0
    for dir in */; do
        if [ -f "$dir/report.json" ]; then
            f2p=$(jq '.["FAIL_TO_PASS"] | length' "$dir/report.json" 2>/dev/null)
            p2p=$(jq '.["PASS_TO_PASS"] | length' "$dir/report.json" 2>/dev/null)
            if [ "$f2p" != "null" ] && [ "$f2p" -gt 0 ] && [ "$p2p" != "null" ] && [ "$p2p" -gt 0 ] && echo "$dir" | grep -q "$type"; then
                count=$((count+1))
            fi
        fi
    done
    if [ $count -gt 0 ]; then
        echo "  $type: $count"
    fi
done
