#!/usr/bin/env bash
# CleanApp 60-Second Quickstart
# Run this to install the CLI, authenticate, and submit a test report.
#
# Usage:
#   bash quickstart.sh              # Full run (install + init + test submit)
#   bash quickstart.sh --dry-run    # Show commands without executing

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE — showing commands only ==="
    echo ""
fi

run_or_show() {
    if $DRY_RUN; then
        echo "  \$ $*"
    else
        "$@"
    fi
}

echo "╔══════════════════════════════════════════════╗"
echo "║   CleanApp CLI — 60-Second Quickstart       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Step 1: Install
echo "→ Step 1: Installing @cleanapp/cli..."
run_or_show npm install -g @cleanapp/cli
echo ""

# Step 2: Initialize (interactive auth)
echo "→ Step 2: Authenticating with CleanApp..."
echo "  (This will register a fetcher key if you don't have one)"
run_or_show cleanapp init
echo ""

# Step 3: Verify auth
echo "→ Step 3: Verifying authentication..."
run_or_show cleanapp auth whoami
echo ""

# Step 4: Submit a test report
echo "→ Step 4: Submitting a test report..."
run_or_show cleanapp submit \
    --title "Test Report from Agent" \
    --desc "Verification submission — testing CleanApp integration" \
    --lat 0 --lng 0
echo ""

echo "✓ Done. Your agent is now connected to CleanApp."
echo ""
echo "Next steps:"
echo "  • Submit real reports:  cleanapp submit --title '...' --desc '...' --lat ... --lng ..."
echo "  • Bulk submit:         cleanapp bulk-submit --file reports.ndjson"
echo "  • Check status:        cleanapp status --report-id <id>"
echo "  • Check quotas:        cleanapp auth whoami"
echo ""
echo "Docs: github.com/CleanAppio/cleanapp-agent001"
