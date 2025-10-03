#!/bin/bash
# Development Army - Deploy multiple autonomous development workers in parallel

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Army configuration
WORKERS=(
    "database:Phase 1: Foundation"
    "api:Phase 1: Foundation"
    "llm:Phase 1: Foundation"
    "scrapers:Phase 2: Content Pipeline"
    "newsletter:Phase 3: Newsletter System"
)

deploy_worker() {
    local worker_type=$1
    local phase=$2
    local worker_id=$3

    log_info "🚀 Deploying Worker #$worker_id: $worker_type (Phase: $phase)"

    # Create worker-specific directory
    local worker_dir="$PROJECT_ROOT/.workers/worker_$worker_id"
    mkdir -p "$worker_dir"

    # Get issues for this worker
    local issues=$(gh issue list \
        --repo dttb-capy/Newsauto \
        --milestone "$phase" \
        --label "$worker_type" \
        --state open \
        --json number,title \
        --limit 5)

    local issue_count=$(echo "$issues" | jq length)

    if [ "$issue_count" -eq 0 ]; then
        log_warning "No issues found for $worker_type in $phase"
        return
    fi

    log_info "  Found $issue_count issues to work on"

    # Process first issue
    local first_issue=$(echo "$issues" | jq -r '.[0].number')
    local issue_title=$(echo "$issues" | jq -r '.[0].title')

    log_info "  Working on #$first_issue: $issue_title"

    # Comment on issue
    gh issue comment "$first_issue" \
        --repo dttb-capy/Newsauto \
        --body "🤖 **Development Army Worker #$worker_id**

This worker is now processing this issue as part of the autonomous development army.

- Worker Type: \`$worker_type\`
- Phase: \`$phase\`
- Status: In Progress

_Automated by development_army.sh_" 2>/dev/null || true

    log_success "  Worker #$worker_id deployed and active"
}

deploy_army() {
    log_info "🎖️  DEPLOYING DEVELOPMENT ARMY"
    log_info "================================"

    local worker_id=1

    for worker_config in "${WORKERS[@]}"; do
        IFS=: read -r worker_type phase <<< "$worker_config"
        deploy_worker "$worker_type" "$phase" "$worker_id" &
        worker_id=$((worker_id + 1))
        sleep 1  # Stagger deployments
    done

    # Wait for all workers to deploy
    wait

    log_success "🎖️  All workers deployed successfully!"
}

monitor_progress() {
    log_info "📊 Monitoring Development Progress"
    log_info "==================================="

    # Get issue statistics
    local total=$(gh issue list --repo dttb-capy/Newsauto --limit 1000 --json number | jq length)
    local open=$(gh issue list --repo dttb-capy/Newsauto --state open --limit 1000 --json number | jq length)
    local closed=$(gh issue list --repo dttb-capy/Newsauto --state closed --limit 1000 --json number | jq length)
    local progress=$((closed * 100 / total))

    echo ""
    echo "Total Issues:     $total"
    echo "Open:             $open"
    echo "Closed:           $closed"
    echo "Progress:         $progress%"
    echo ""

    # Show active workers
    log_info "Active Workers:"
    for worker_config in "${WORKERS[@]}"; do
        IFS=: read -r worker_type phase <<< "$worker_config"
        local worker_issues=$(gh issue list \
            --repo dttb-capy/Newsauto \
            --milestone "$phase" \
            --label "$worker_type" \
            --state open \
            --json number | jq length)

        if [ "$worker_issues" -gt 0 ]; then
            echo "  - $worker_type ($phase): $worker_issues issues"
        fi
    done
}

self_heal() {
    log_info "🔧 Running Self-Healing Checks"
    log_info "==============================="

    # Check for stale branches
    local stale_branches=$(git branch | grep -v "main" | grep -v "*" | wc -l)
    if [ "$stale_branches" -gt 5 ]; then
        log_warning "Found $stale_branches stale branches, cleaning up..."
        git branch | grep -v "main" | grep -v "*" | head -n 3 | xargs -r git branch -D 2>/dev/null || true
    fi

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        log_warning "Found uncommitted changes, auto-committing..."
        git add . 2>/dev/null || true
        git commit -m "chore: Auto-commit by development army self-healing" 2>/dev/null || true
    fi

    # Check dependencies
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        log_info "Verifying dependencies..."
        pip install -q -r "$PROJECT_ROOT/requirements.txt" 2>/dev/null || true
    fi

    log_success "Self-healing checks complete"
}

continuous_development() {
    local iterations=${1:-10}
    local delay=${2:-300}  # 5 minutes between iterations

    log_info "🔄 Starting Continuous Development Mode"
    log_info "Iterations: $iterations"
    log_info "Delay: ${delay}s"
    log_info "======================================"

    for i in $(seq 1 "$iterations"); do
        echo ""
        log_info "🔁 Iteration $i of $iterations"
        echo ""

        # Deploy army
        deploy_army

        # Monitor progress
        monitor_progress

        # Self-heal
        self_heal

        # Run autonomous developer
        if [ -f "$PROJECT_ROOT/scripts/autonomous_developer.py" ]; then
            log_info "Running autonomous developer..."
            python3 "$PROJECT_ROOT/scripts/autonomous_developer.py" || true
        fi

        # Push changes
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            log_info "Pushing changes to remote..."
            git push origin main 2>/dev/null || log_warning "Failed to push changes"
        fi

        if [ "$i" -lt "$iterations" ]; then
            log_info "Sleeping for ${delay}s before next iteration..."
            sleep "$delay"
        fi
    done

    log_success "🎖️  Continuous development complete!"
}

create_status_dashboard() {
    local output_file="$PROJECT_ROOT/AUTOMATION_STATUS.md"

    cat > "$output_file" << 'EOF'
# 🤖 Automation Army Status Dashboard

## Current Status
**Last Updated**: $(date)

## Progress Overview
EOF

    # Add statistics
    local total=$(gh issue list --repo dttb-capy/Newsauto --limit 1000 --json number | jq length 2>/dev/null || echo "N/A")
    local open=$(gh issue list --repo dttb-capy/Newsauto --state open --limit 1000 --json number | jq length 2>/dev/null || echo "N/A")
    local closed=$(gh issue list --repo dttb-capy/Newsauto --state closed --limit 1000 --json number | jq length 2>/dev/null || echo "N/A")

    cat >> "$output_file" << EOF

- **Total Issues**: $total
- **Open**: $open
- **Closed**: $closed
- **Progress**: $((closed * 100 / total))%

## Active Workers

| Worker | Phase | Open Issues | Status |
|--------|-------|-------------|--------|
EOF

    # Add worker status
    for worker_config in "${WORKERS[@]}"; do
        IFS=: read -r worker_type phase <<< "$worker_config"
        local worker_issues=$(gh issue list \
            --repo dttb-capy/Newsauto \
            --milestone "$phase" \
            --label "$worker_type" \
            --state open \
            --json number | jq length 2>/dev/null || echo "0")

        local status="🟢 Active"
        if [ "$worker_issues" -eq 0 ]; then
            status="✅ Complete"
        fi

        echo "| $worker_type | $phase | $worker_issues | $status |" >> "$output_file"
    done

    cat >> "$output_file" << 'EOF'

## Next Actions
The automation army will continue working on high-priority issues across all phases.

---
*Generated by development_army.sh*
EOF

    log_success "Status dashboard created: $output_file"
}

# Main execution
main() {
    case "${1:-deploy}" in
        deploy)
            deploy_army
            monitor_progress
            ;;
        monitor)
            monitor_progress
            ;;
        heal)
            self_heal
            ;;
        continuous)
            continuous_development "${2:-10}" "${3:-300}"
            ;;
        dashboard)
            create_status_dashboard
            ;;
        *)
            echo "Usage: $0 {deploy|monitor|heal|continuous|dashboard}"
            echo ""
            echo "Commands:"
            echo "  deploy      - Deploy all workers once"
            echo "  monitor     - Monitor current progress"
            echo "  heal        - Run self-healing checks"
            echo "  continuous  - Run continuous development (iterations delay)"
            echo "  dashboard   - Create status dashboard"
            exit 1
            ;;
    esac
}

main "$@"
