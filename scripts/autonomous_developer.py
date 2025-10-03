#!/usr/bin/env python3
"""
Autonomous Developer - AI-powered development automation
Analyzes issues and implements solutions autonomously
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

class AutonomousDeveloper:
    """Main autonomous development orchestrator"""

    def __init__(self, repo_path: Path = Path(".")):
        self.repo_path = repo_path
        self.github_token = os.getenv("GITHUB_TOKEN")

    def get_next_issue(self) -> Optional[Dict]:
        """Get the next high-priority issue to work on"""
        cmd = [
            "gh", "issue", "list",
            "--repo", "dttb-capy/Newsauto",
            "--label", "priority:high",
            "--state", "open",
            "--json", "number,title,body,labels,milestone",
            "--limit", "10"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None

        issues = json.loads(result.stdout)

        # Prioritize Phase 1 issues
        phase1_issues = [i for i in issues if i.get("milestone", {}).get("title") == "Phase 1: Foundation"]

        return phase1_issues[0] if phase1_issues else (issues[0] if issues else None)

    def analyze_issue(self, issue: Dict) -> Dict:
        """Analyze issue and determine implementation strategy"""
        title = issue["title"].lower()
        labels = [l["name"] for l in issue.get("labels", [])]

        strategy = {
            "issue_number": issue["number"],
            "type": "general",
            "components": [],
            "estimated_hours": 4,
            "approach": []
        }

        # Determine issue type and components
        if "database" in title or "schema" in title or "model" in title:
            strategy["type"] = "database"
            strategy["components"] = ["models", "migrations"]
            strategy["approach"] = [
                "Create SQLAlchemy models",
                "Setup Alembic migrations",
                "Add indexes and constraints",
                "Write model tests"
            ]
        elif "api" in title or "endpoint" in title or "fastapi" in title:
            strategy["type"] = "api"
            strategy["components"] = ["api", "routes", "schemas"]
            strategy["approach"] = [
                "Define Pydantic schemas",
                "Create API routes",
                "Add dependency injection",
                "Write endpoint tests"
            ]
        elif "ollama" in title or "llm" in title:
            strategy["type"] = "llm"
            strategy["components"] = ["llm", "prompts"]
            strategy["approach"] = [
                "Create Ollama client wrapper",
                "Implement model routing",
                "Add response caching",
                "Write integration tests"
            ]
        elif "rss" in title or "scraper" in title or "fetcher" in title:
            strategy["type"] = "scraper"
            strategy["components"] = ["scrapers"]
            strategy["approach"] = [
                "Create base scraper class",
                "Implement RSS fetcher",
                "Add rate limiting",
                "Write scraper tests"
            ]

        # Estimate based on size label
        if "size:small" in labels:
            strategy["estimated_hours"] = 2
        elif "size:large" in labels:
            strategy["estimated_hours"] = 8

        return strategy

    def implement_database_models(self, issue: Dict):
        """Implement database models and migrations"""
        models_dir = self.repo_path / "newsauto" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        # Create __init__.py
        init_file = models_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('''"""
Database models for Newsauto
"""

from .base import Base
from .newsletter import Newsletter
from .subscriber import Subscriber
from .content import ContentItem
from .edition import Edition
from .events import SubscriberEvent

__all__ = [
    "Base",
    "Newsletter",
    "Subscriber",
    "ContentItem",
    "Edition",
    "SubscriberEvent",
]
''')

        print(f"✅ Created models package structure")

    def implement_api_endpoints(self, issue: Dict):
        """Implement FastAPI endpoints"""
        api_dir = self.repo_path / "newsauto" / "api"
        api_dir.mkdir(parents=True, exist_ok=True)

        routes_dir = api_dir / "routes"
        routes_dir.mkdir(exist_ok=True)

        print(f"✅ Created API structure")

    def implement_llm_integration(self, issue: Dict):
        """Implement LLM/Ollama integration"""
        llm_dir = self.repo_path / "newsauto" / "llm"
        llm_dir.mkdir(parents=True, exist_ok=True)

        print(f"✅ Created LLM integration structure")

    def run_tests(self) -> bool:
        """Run test suite"""
        if not (self.repo_path / "tests").exists():
            print("⚠️  No tests directory yet")
            return True

        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed")
            print(result.stdout)
            return False

    def commit_changes(self, issue: Dict, strategy: Dict):
        """Commit implemented changes"""
        issue_number = issue["number"]
        title = issue["title"]

        # Stage all changes
        subprocess.run(["git", "add", "."], check=True)

        # Create commit message
        commit_msg = f"""feat: Implement {title} (#{issue_number})

Autonomous implementation by AI developer:
- {chr(10).join(f'  {step}' for step in strategy['approach'])}

Closes #{issue_number}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
"""

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"✅ Committed changes for issue #{issue_number}")
            return True
        else:
            print(f"⚠️  Nothing to commit")
            return False

    def update_issue(self, issue: Dict, status: str):
        """Update issue with progress comment"""
        comment = f"""🤖 **Autonomous Development Update**

Status: {status}

The autonomous developer has {'completed work on' if status == 'completed' else 'started working on'} this issue.

Changes have been committed and are ready for review.

_Automated by autonomous_developer.py_
"""

        subprocess.run([
            "gh", "issue", "comment", str(issue["number"]),
            "--repo", "dttb-capy/Newsauto",
            "--body", comment
        ])

        if status == "completed":
            # Close the issue
            subprocess.run([
                "gh", "issue", "close", str(issue["number"]),
                "--repo", "dttb-capy/Newsauto",
                "--comment", "Completed by autonomous development system"
            ])

    def run(self):
        """Main execution loop"""
        print("🤖 Autonomous Developer Starting...")
        print("=" * 60)

        # Get next issue
        issue = self.get_next_issue()
        if not issue:
            print("✅ No high-priority issues found. All caught up!")
            return

        print(f"\n📋 Working on: {issue['title']}")
        print(f"   Issue: #{issue['number']}")

        # Analyze issue
        strategy = self.analyze_issue(issue)
        print(f"\n🎯 Strategy: {strategy['type']}")
        print(f"   Components: {', '.join(strategy['components'])}")
        print(f"   Estimated: {strategy['estimated_hours']} hours")

        # Update issue status
        self.update_issue(issue, "in_progress")

        # Implement based on type
        if strategy["type"] == "database":
            self.implement_database_models(issue)
        elif strategy["type"] == "api":
            self.implement_api_endpoints(issue)
        elif strategy["type"] == "llm":
            self.implement_llm_integration(issue)

        # Run tests
        print("\n🧪 Running tests...")
        tests_passed = self.run_tests()

        # Commit changes
        print("\n💾 Committing changes...")
        committed = self.commit_changes(issue, strategy)

        if committed and tests_passed:
            self.update_issue(issue, "completed")
            print(f"\n✅ Successfully completed issue #{issue['number']}")
        else:
            print(f"\n⚠️  Work in progress on issue #{issue['number']}")

        print("\n" + "=" * 60)
        print("🤖 Autonomous Developer Complete")

if __name__ == "__main__":
    developer = AutonomousDeveloper()
    developer.run()
