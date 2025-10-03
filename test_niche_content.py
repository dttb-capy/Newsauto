#!/usr/bin/env python
"""
Test fetching content for our premium niches.
Validates that RSS feeds are working and content is being aggregated.
"""

import asyncio
import sys
from datetime import datetime

from newsauto.scrapers.niche_aggregator import NicheContentAggregator
from newsauto.config.niches import niche_configs
from newsauto.config.rss_feeds import validate_feeds


async def main():
    print("=" * 70)
    print("🚀 NICHE CONTENT AGGREGATION TEST")
    print("=" * 70)

    # Validate RSS feed configuration
    print("\n📡 Validating RSS Feed Configuration...")
    issues = validate_feeds()
    if issues:
        print("⚠️ Feed configuration issues found:")
        for niche, problems in issues.items():
            print(f"  - {niche}: {', '.join(problems)}")
    else:
        print("✅ All niches have sufficient RSS feeds configured")

    # Initialize aggregator
    aggregator = NicheContentAggregator()

    # Test top 3 niches
    test_niches = ["cto_engineering_playbook", "veteran_executive_network", "b2b_saas_founder"]

    print(f"\n📚 Testing content fetch for {len(test_niches)} niches...")
    print("-" * 50)

    for niche_key in test_niches:
        if niche_key not in niche_configs:
            print(f"❌ Niche '{niche_key}' not found")
            continue

        niche = niche_configs[niche_key]
        print(f"\n🎯 {niche.name}")
        print(f"   Target: {niche.target_audience}")

        try:
            # Fetch top stories
            stories = await aggregator.get_top_stories_for_niche(
                niche_key, count=3, max_age_days=7
            )

            if stories:
                print(f"   ✅ Found {len(stories)} stories:")
                for i, story in enumerate(stories[:3], 1):
                    title = story.get("title", "Untitled")[:60]
                    score = story.get("relevance_score", 0)
                    print(f"      {i}. {title}... (score: {score:.2f})")
            else:
                print(f"   ⚠️ No stories found (feeds may be down or filtered out)")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("📊 CONTENT AGGREGATION SUMMARY")
    print("-" * 50)

    # Test all niches quickly
    print("\n🔄 Quick test of all niches...")
    all_results = {}

    for niche_key in list(niche_configs.keys()):
        try:
            # Just try to get niche info and a single story
            info = aggregator.get_niche_info(niche_key)
            if info:
                all_results[niche_key] = {
                    "name": info["name"],
                    "feeds": info["feed_count"],
                    "status": "✅ Configured"
                }
        except Exception as e:
            all_results[niche_key] = {
                "name": niche_configs[niche_key].name,
                "feeds": 0,
                "status": f"❌ Error: {str(e)[:30]}"
            }

    print("\nNiche Status:")
    for key, result in all_results.items():
        print(f"  • {result['name']}: {result['feeds']} feeds - {result['status']}")

    print("\n✅ Content aggregation test complete!")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)