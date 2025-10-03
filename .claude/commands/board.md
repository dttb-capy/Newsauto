---
model: sonnet-4
---

Show the current development board status with:

1. **Parse PROJECT_SPEC.md** to extract all 4 phases and their tasks
2. **Query git** to find:
   - Recent commits (last 7 days) grouped by phase
   - Open branches mapped to tasks
   - Closed issues/completed work
3. **Generate ASCII table** showing:

```
┌──────────────────────────────────────────────────────────────────┐
│                    NEWSAUTO DEVELOPMENT BOARD                     │
└──────────────────────────────────────────────────────────────────┘

PHASE 1: FOUNDATION (Week 1) [████████████████████] 100% ✓
├─ [✓] Project setup and structure
├─ [✓] Database schema implementation
├─ [✓] Basic CRUD operations
├─ [✓] Ollama integration
└─ [✓] Simple content fetching

PHASE 2: CONTENT PIPELINE (Week 2) [████████████░░░░] 75%
├─ [✓] RSS feed parser
├─ [✓] Reddit/HN integration
├─ [✓] Content deduplication
├─ [~] LLM summarization (in progress - branch: feat/llm-cache)
└─ [ ] Content scoring

PHASE 3: NEWSLETTER SYSTEM (Week 3) [██░░░░░░░░░░░░░░] 10%
├─ [~] Newsletter generation (in progress)
├─ [ ] Template engine
├─ [ ] Email sending (SMTP)
├─ [ ] Subscriber management
└─ [ ] Basic personalization

PHASE 4: AUTOMATION (Week 4) [░░░░░░░░░░░░░░░░░░░░] 0%
├─ [ ] Scheduling system
├─ [ ] GitHub Actions setup
├─ [ ] Error handling
├─ [ ] Monitoring
└─ [ ] Testing suite

───────────────────────────────────────────────────────────────────

📊 OVERALL PROGRESS: 46% (20/43 tasks complete)

📈 RECENT ACTIVITY (last 7 days):
  • 12 commits across 3 phases
  • 5 issues closed
  • 3 active branches
  • 2 PRs merged

🔥 IN PROGRESS:
  • feat/llm-cache (Phase 2) - @developer - Last commit: 2h ago
  • feat/newsletter-gen (Phase 3) - @developer - Last commit: 5h ago

⚡ VELOCITY: 8.5 tasks/week (trending up +15%)

🎯 NEXT MILESTONE: Phase 2 complete (ETA: 3 days)

───────────────────────────────────────────────────────────────────
View detailed board: PROJECT_URL or run `git log --graph --oneline`
```

**Instructions:**
1. Read `PROJECT_SPEC.md` to get phase definitions
2. Run `git log --since="7 days ago" --format="%s"` for recent commits
3. Run `git branch -a` for active branches
4. Parse commit messages for phase references
5. Calculate completion percentage per phase
6. Generate progress bars using Unicode blocks (█ ▓ ▒ ░)
7. Map branches to tasks by analyzing branch names and recent commits
8. Calculate velocity based on commit frequency

**Legend:**
- [✓] = Complete
- [~] = In Progress
- [ ] = Not Started
- █ = Progress bar fill
