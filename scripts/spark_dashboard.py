#!/usr/bin/env python3
"""
Spark Intelligence Dashboard

A Streamlit dashboard showing:
1. What Spark is learning from X trends
2. Ecosystem intelligence (Moltbook, OpenClaw, BASE, Solana, Bittensor)
3. Content recommendations based on trends
4. Cognitive insight growth over time

Run:
    streamlit run scripts/spark_dashboard.py --server.port 8502
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import streamlit as st
    import pandas as pd
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("Streamlit not installed. Run: pip install streamlit pandas")

from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory


def load_research_reports():
    """Load all research reports."""
    report_dir = Path.home() / '.spark' / 'research_reports'
    reports = []

    if report_dir.exists():
        for f in sorted(report_dir.glob('report_*.json'), reverse=True)[:30]:
            try:
                reports.append(json.loads(f.read_text()))
            except:
                pass

    return reports


def load_collective_intelligence():
    """Load SparkNet collective intelligence."""
    collective_dir = Path.home() / '.spark' / 'sparknet' / 'collective'
    collective = {}

    if collective_dir.exists():
        for f in collective_dir.glob('*.json'):
            try:
                collective[f.stem] = json.loads(f.read_text())
            except:
                pass

    return collective


def get_ecosystem_insights():
    """Get ecosystem-specific insights from Spark."""
    learner = get_cognitive_learner()

    ecosystems = {
        'moltbook': [],
        'openclaw': [],
        'base': [],
        'solana': [],
        'bittensor': [],
        'vibe_coding': [],
    }

    for key, insight in learner.insights.items():
        text = (insight.insight + ' ' + insight.context).lower()

        for eco in ecosystems.keys():
            if eco in text or eco.replace('_', ' ') in text:
                ecosystems[eco].append({
                    'insight': insight.insight,
                    'confidence': insight.confidence,
                    'validations': insight.times_validated,
                    'created': insight.created_at[:10] if insight.created_at else 'unknown',
                })

    return ecosystems


def get_content_recommendations():
    """Get content recommendations."""
    try:
        from scripts.content_recommendations import generate_recommendations
        return generate_recommendations()
    except:
        return {'content_ideas': [], 'ready_to_post': []}


def run_cli_dashboard():
    """Run a CLI version of the dashboard."""
    print("\n" + "=" * 70)
    print("  SPARK INTELLIGENCE DASHBOARD (CLI Mode)")
    print("=" * 70)

    learner = get_cognitive_learner()
    stats = learner.get_stats()

    print(f"\n📊 COGNITIVE INSIGHTS: {stats['total_insights']}")
    print(f"   Average Reliability: {stats['avg_reliability']:.0%}")
    print(f"   Promoted: {stats['promoted_count']}")

    print("\n   By Category:")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        print(f"     - {cat}: {count}")

    # Ecosystem insights
    print("\n🌐 ECOSYSTEM INTELLIGENCE:")
    ecosystems = get_ecosystem_insights()
    for eco, insights in ecosystems.items():
        if insights:
            print(f"\n   {eco.upper()} ({len(insights)} insights)")
            for i in sorted(insights, key=lambda x: -x['confidence'])[:3]:
                print(f"     • {i['insight'][:60]}... ({i['confidence']:.0%})")

    # Collective intelligence
    print("\n🤖 SPARKNET COLLECTIVE:")
    collective = load_collective_intelligence()
    for name, data in collective.items():
        if isinstance(data, list):
            print(f"   {name}: {len(data)} items")

    # Recent research
    print("\n📰 RECENT RESEARCH REPORTS:")
    reports = load_research_reports()
    for r in reports[:3]:
        print(f"   - {r.get('date', 'unknown')}: {r.get('insights_count', 0)} insights")

    # Content recommendations
    print("\n✍️  CONTENT RECOMMENDATIONS:")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from content_recommendations import generate_recommendations
        recs = generate_recommendations()
        for i, idea in enumerate(recs.get('content_ideas', [])[:5], 1):
            print(f"   {i}. [{idea['framework']}] {idea['angle'][:50]}...")
    except Exception as e:
        print(f"   (Error loading recommendations: {e})")

    print("\n" + "=" * 70)
    print("  Run with Streamlit for full dashboard:")
    print("  streamlit run scripts/spark_dashboard.py --server.port 8502")
    print("=" * 70)


def run_streamlit_dashboard():
    """Run the Streamlit dashboard."""
    st.set_page_config(
        page_title="Spark Intelligence Dashboard",
        page_icon="🧠",
        layout="wide"
    )

    st.title("🧠 Spark Intelligence Dashboard")
    st.markdown("*Real-time view of what Spark is learning from the AI agent ecosystem*")

    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", [
        "Overview",
        "Ecosystem Intel",
        "Content Recommendations",
        "Research History",
        "SparkNet Collective"
    ])

    # Load data
    learner = get_cognitive_learner()
    stats = learner.get_stats()

    if page == "Overview":
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Insights", stats['total_insights'])
        col2.metric("Avg Reliability", f"{stats['avg_reliability']:.0%}")
        col3.metric("Promoted", stats['promoted_count'])
        col4.metric("Pending", stats['unpromoted_count'])

        st.subheader("Insights by Category")
        cat_data = pd.DataFrame([
            {'Category': k, 'Count': v}
            for k, v in stats['by_category'].items()
        ])
        st.bar_chart(cat_data.set_index('Category'))

        # Recent high-confidence insights
        st.subheader("Recent High-Confidence Insights")
        high_conf = [
            (k, i) for k, i in learner.insights.items()
            if i.confidence >= 0.8
        ]
        high_conf.sort(key=lambda x: x[1].created_at or '', reverse=True)

        for key, insight in high_conf[:10]:
            with st.expander(f"[{insight.category.value}] {insight.insight[:60]}..."):
                st.write(f"**Insight:** {insight.insight}")
                st.write(f"**Context:** {insight.context}")
                st.write(f"**Confidence:** {insight.confidence:.0%}")
                st.write(f"**Validations:** {insight.times_validated}")
                st.write(f"**Created:** {insight.created_at}")

    elif page == "Ecosystem Intel":
        st.subheader("🌐 Ecosystem Intelligence")

        ecosystems = get_ecosystem_insights()

        tabs = st.tabs(list(ecosystems.keys()))
        for tab, (eco, insights) in zip(tabs, ecosystems.items()):
            with tab:
                st.write(f"**{len(insights)} insights about {eco}**")

                if insights:
                    df = pd.DataFrame(insights)
                    df = df.sort_values('confidence', ascending=False)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"No insights about {eco} yet. Run daily research to gather more.")

    elif page == "Content Recommendations":
        st.subheader("✍️ Content Recommendations")

        # Topic filter
        topic = st.selectbox("Filter by topic", [
            None, "moltbook", "openclaw", "base_chain", "solana_ai", "vibe_coding", "bittensor"
        ])

        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from content_recommendations import generate_recommendations, CONTENT_FRAMEWORKS
            recs = generate_recommendations(topic=topic)

            # Ready to post
            st.subheader("🚀 Ready to Post")
            for r in recs.get('ready_to_post', []):
                with st.container():
                    st.markdown(f"**{r['framework']}**")
                    st.code(r['hook'])
                    st.caption(r['next_steps'])
                    st.divider()

            # All ideas
            st.subheader("💡 All Content Ideas")
            for idea in recs.get('content_ideas', []):
                with st.expander(f"[{idea['framework']}] {idea['angle']}"):
                    st.write(f"**Structure:** {idea['structure']}")
                    st.write(f"**Example:** {idea['example']}")
                    st.write(f"**Target:** {idea['target']}")

        except Exception as e:
            st.error(f"Error loading recommendations: {e}")

    elif page == "Research History":
        st.subheader("📰 Research History")

        reports = load_research_reports()

        if reports:
            # Timeline
            dates = [r.get('date', '') for r in reports]
            counts = [r.get('insights_count', 0) for r in reports]
            df = pd.DataFrame({'Date': dates, 'Insights': counts})
            st.line_chart(df.set_index('Date'))

            # Reports
            for report in reports[:10]:
                with st.expander(f"Report: {report.get('date', 'unknown')}"):
                    st.json(report)
        else:
            st.info("No research reports yet. Run daily research to generate reports.")

    elif page == "SparkNet Collective":
        st.subheader("🤖 SparkNet Collective Intelligence")

        collective = load_collective_intelligence()

        if collective:
            for name, data in collective.items():
                with st.expander(f"{name} ({len(data) if isinstance(data, list) else 'object'})"):
                    st.json(data)
        else:
            st.info("SparkNet collective not populated yet.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--cli', action='store_true', help='Run CLI version')
    args, unknown = parser.parse_known_args()

    if args.cli or not STREAMLIT_AVAILABLE:
        run_cli_dashboard()
    else:
        run_streamlit_dashboard()
