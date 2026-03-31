"""
DeepSeek Coordinator Service

Implements the dual-AI architecture where DeepSeek handles data-side intelligence
(signal extraction, clustering, pattern detection, market sizing, trend correlation)
and Claude handles creative intelligence (opportunity narratives, validation analysis,
user-facing chat).

Pipeline:
  Raw Scraped Data
    -> [DeepSeek] Signal extraction & quality scoring
    -> [DeepSeek] Clustering & deduplication
    -> [DeepSeek] Market data aggregation & trend detection
    -> [Claude]   Creative opportunity narratives & validation
    -> Database
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


class DeepSeekCoordinatorService:
    """
    Data-side AI coordinator using DeepSeek for structured analysis tasks.

    DeepSeek handles:
      - Signal extraction from raw scraped text
      - Clustering similar signals into opportunity groups
      - Market data aggregation and sizing
      - Trend detection and correlation
      - Structured data preparation for Claude's creative pass

    Claude handles (via OpportunityProcessor):
      - Writing professional opportunity narratives
      - Generating creative business model suggestions
      - Producing user-facing insights and recommendations
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = model or DEEPSEEK_MODEL

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _call_deepseek(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        """Make a DeepSeek API call (OpenAI-compatible endpoint)."""
        if not self.is_configured:
            raise ValueError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]

    def _parse_json_response(self, text: str) -> Any:
        """Extract JSON from a response that may contain markdown fences."""
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())

    # ------------------------------------------------------------------
    # Stage 1: Signal Extraction & Quality Scoring
    # ------------------------------------------------------------------

    async def extract_signals(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract structured business signals from raw scraped data.

        DeepSeek analyzes each batch of raw items and returns:
          - problem_statement: clear articulation of the pain point
          - signal_strength: 0-100 quality score
          - category: business category
          - geographic_hints: any location info found
          - keywords: extracted keywords for clustering
        """
        if not raw_items:
            return []

        # Process in batches to stay within token limits
        batch_size = 10
        all_signals = []

        for i in range(0, len(raw_items), batch_size):
            batch = raw_items[i : i + batch_size]
            signals = await self._extract_signal_batch(batch)
            all_signals.extend(signals)

        return all_signals

    async def _extract_signal_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of raw items through DeepSeek for signal extraction."""
        items_text = ""
        for idx, item in enumerate(batch):
            title = item.get("title", "")
            body = item.get("body") or item.get("selftext") or item.get("text", "")
            source = item.get("source_platform", "unknown")
            items_text += f"\n--- ITEM {idx + 1} (source: {source}) ---\n"
            items_text += f"Title: {title}\n"
            items_text += f"Content: {body[:1000]}\n"

        system_prompt = (
            "You are a data analyst specializing in business opportunity detection. "
            "Your job is to extract structured business signals from raw social media "
            "and web data. Be analytical and precise. Return ONLY valid JSON."
        )

        prompt = f"""Analyze these {len(batch)} raw data items and extract business signals.

For each item, determine:
1. Is this a genuine business pain point or market gap? (not spam, memes, or off-topic)
2. What is the core problem being described?
3. How strong is the signal? (0-100 based on specificity, urgency, and volume indicators)
4. What business category does it belong to?
5. Any geographic information present?

{items_text}

Respond with a JSON array. Each element must have:
{{
  "item_index": <0-based index>,
  "is_valid_signal": true/false,
  "problem_statement": "Clear 1-2 sentence problem description",
  "signal_strength": 0-100,
  "category": "One of: Technology, Healthcare, Finance, Education, Retail, Food & Beverage, Real Estate, Transportation, Entertainment, B2B Services, Consumer Services, Home Services, Pets & Animals, Manufacturing, Other",
  "subcategory": "More specific",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "geographic_hints": {{"country": null, "region": null, "city": null}},
  "urgency": "low/medium/high/critical",
  "estimated_audience_size": "small/medium/large/massive"
}}

Only include items where is_valid_signal is true."""

        try:
            response = await self._call_deepseek(prompt, system_prompt)
            signals = self._parse_json_response(response)

            # Attach original data back to signals
            for signal in signals:
                idx = signal.get("item_index", 0)
                if 0 <= idx < len(batch):
                    signal["raw_data"] = batch[idx]

            return signals
        except Exception as e:
            logger.error(f"DeepSeek signal extraction failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Stage 2: Clustering & Deduplication
    # ------------------------------------------------------------------

    async def cluster_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group similar signals into opportunity clusters.

        DeepSeek identifies overlapping themes and merges related signals
        into consolidated opportunity groups with aggregated evidence.
        """
        if len(signals) <= 1:
            return [
                {
                    "cluster_id": 0,
                    "theme": signals[0].get("problem_statement", "") if signals else "",
                    "signals": signals,
                    "signal_count": len(signals),
                    "avg_strength": signals[0].get("signal_strength", 50) if signals else 0,
                    "category": signals[0].get("category", "Other") if signals else "Other",
                }
            ] if signals else []

        # Prepare signal summaries for clustering
        summaries = []
        for idx, s in enumerate(signals):
            summaries.append(
                f"[{idx}] ({s.get('category', 'Other')}) "
                f"{s.get('problem_statement', 'N/A')} "
                f"[strength: {s.get('signal_strength', 0)}, "
                f"keywords: {', '.join(s.get('keywords', [])[:5])}]"
            )

        system_prompt = (
            "You are a data clustering specialist. Group similar business signals "
            "into coherent opportunity themes. Merge duplicates. Return ONLY valid JSON."
        )

        prompt = f"""Here are {len(signals)} extracted business signals. Group similar ones into clusters.

Signals:
{chr(10).join(summaries)}

Rules:
- Signals about the same problem/industry should be in one cluster
- Each signal can only belong to one cluster
- A cluster with more signals is stronger evidence
- Preserve the original signal indices for reference

Return a JSON array of clusters:
[
  {{
    "cluster_id": 0,
    "theme": "One-sentence theme describing this opportunity cluster",
    "signal_indices": [0, 3, 7],
    "category": "Primary category",
    "subcategory": "Specific subcategory",
    "combined_keywords": ["key1", "key2"],
    "avg_strength": 75,
    "evidence_summary": "Brief summary of why these signals form a coherent opportunity"
  }}
]"""

        try:
            response = await self._call_deepseek(prompt, system_prompt)
            clusters_raw = self._parse_json_response(response)

            # Attach actual signal objects to clusters
            clusters = []
            for c in clusters_raw:
                indices = c.get("signal_indices", [])
                cluster_signals = [signals[i] for i in indices if i < len(signals)]
                clusters.append(
                    {
                        "cluster_id": c.get("cluster_id", len(clusters)),
                        "theme": c.get("theme", ""),
                        "signals": cluster_signals,
                        "signal_count": len(cluster_signals),
                        "avg_strength": c.get("avg_strength", 0),
                        "category": c.get("category", "Other"),
                        "subcategory": c.get("subcategory"),
                        "combined_keywords": c.get("combined_keywords", []),
                        "evidence_summary": c.get("evidence_summary", ""),
                    }
                )

            return clusters
        except Exception as e:
            logger.error(f"DeepSeek clustering failed: {e}")
            # Fallback: each signal is its own cluster
            return [
                {
                    "cluster_id": idx,
                    "theme": s.get("problem_statement", ""),
                    "signals": [s],
                    "signal_count": 1,
                    "avg_strength": s.get("signal_strength", 50),
                    "category": s.get("category", "Other"),
                }
                for idx, s in enumerate(signals)
            ]

    # ------------------------------------------------------------------
    # Stage 3: Market Data Aggregation & Trend Detection
    # ------------------------------------------------------------------

    async def analyze_market_context(
        self, clusters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich opportunity clusters with market intelligence.

        DeepSeek provides structured market analysis:
          - Market size estimates
          - Competition landscape
          - Growth trajectory
          - Geographic opportunity mapping
          - Risk factors
        """
        if not clusters:
            return []

        cluster_summaries = []
        for c in clusters:
            cluster_summaries.append(
                f"- Cluster '{c.get('theme', '')}' "
                f"(category: {c.get('category', 'Other')}, "
                f"signals: {c.get('signal_count', 0)}, "
                f"avg_strength: {c.get('avg_strength', 0)})"
            )

        system_prompt = (
            "You are a market research analyst. Provide structured market intelligence "
            "for business opportunity clusters. Use realistic estimates based on known "
            "market data. Be conservative and data-driven. Return ONLY valid JSON."
        )

        prompt = f"""Analyze these {len(clusters)} opportunity clusters and provide market context.

Clusters:
{chr(10).join(cluster_summaries)}

For each cluster, provide:
{{
  "cluster_id": <matching ID>,
  "market_size_estimate": "$XM-$YB range",
  "market_size_usd_low": <number in millions>,
  "market_size_usd_high": <number in millions>,
  "competition_level": "low/medium/high",
  "existing_players": ["Company1", "Company2"],
  "growth_rate_annual": <percentage>,
  "geographic_hotspots": ["City1", "City2"],
  "target_demographics": "Primary customer segment description",
  "revenue_model_suggestions": ["SaaS subscription", "Marketplace fees"],
  "entry_barriers": "low/medium/high",
  "risk_factors": ["risk1", "risk2"],
  "trend_direction": "growing/stable/declining",
  "time_to_market_months": <number>,
  "confidence_score": 0-100
}}

Return as a JSON array matching the cluster order."""

        try:
            response = await self._call_deepseek(prompt, system_prompt, max_tokens=6000)
            market_data = self._parse_json_response(response)

            # Merge market data into clusters
            market_by_id = {m.get("cluster_id", i): m for i, m in enumerate(market_data)}

            enriched = []
            for c in clusters:
                cid = c["cluster_id"]
                market = market_by_id.get(cid, {})
                enriched.append({**c, "market_context": market})

            return enriched
        except Exception as e:
            logger.error(f"DeepSeek market analysis failed: {e}")
            # Return clusters without market context
            return [{**c, "market_context": {}} for c in clusters]

    # ------------------------------------------------------------------
    # Stage 4: Prepare Structured Data for Claude
    # ------------------------------------------------------------------

    def prepare_for_claude(
        self, enriched_clusters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform DeepSeek's structured analysis into prompts for Claude.

        Claude will use this structured data to generate:
          - Professional opportunity narratives
          - Creative business model descriptions
          - Compelling one-line summaries
          - Actionable next steps
        """
        claude_tasks = []

        for cluster in enriched_clusters:
            market = cluster.get("market_context", {})

            # Build a structured brief for Claude
            brief = {
                "theme": cluster.get("theme", ""),
                "category": cluster.get("category", "Other"),
                "subcategory": cluster.get("subcategory"),
                "signal_count": cluster.get("signal_count", 0),
                "avg_signal_strength": cluster.get("avg_strength", 0),
                "evidence_summary": cluster.get("evidence_summary", ""),
                "combined_keywords": cluster.get("combined_keywords", []),
                "market_size_estimate": market.get("market_size_estimate", "Unknown"),
                "competition_level": market.get("competition_level", "medium"),
                "existing_players": market.get("existing_players", []),
                "growth_rate": market.get("growth_rate_annual"),
                "geographic_hotspots": market.get("geographic_hotspots", []),
                "target_demographics": market.get("target_demographics", ""),
                "revenue_models": market.get("revenue_model_suggestions", []),
                "entry_barriers": market.get("entry_barriers", "medium"),
                "risk_factors": market.get("risk_factors", []),
                "trend_direction": market.get("trend_direction", "stable"),
                "time_to_market": market.get("time_to_market_months"),
                "confidence_score": market.get("confidence_score", 50),
                # Include raw signal samples for Claude to reference
                "sample_signals": [
                    s.get("problem_statement", "")
                    for s in cluster.get("signals", [])[:5]
                ],
            }

            claude_tasks.append(brief)

        return claude_tasks

    # ------------------------------------------------------------------
    # Full Pipeline: Orchestrate DeepSeek -> Claude
    # ------------------------------------------------------------------

    async def process_raw_data(
        self,
        raw_items: List[Dict[str, Any]],
        skip_market_analysis: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the full DeepSeek coordination pipeline on raw scraped data.

        Returns structured data ready for Claude's creative pass.

        Args:
            raw_items: List of raw scraped data dicts
            skip_market_analysis: Skip Stage 3 for faster processing

        Returns:
            {
                "stats": { ... pipeline statistics ... },
                "claude_tasks": [ ... structured briefs for Claude ... ],
                "clusters": [ ... enriched clusters ... ]
            }
        """
        stats = {
            "total_raw_items": len(raw_items),
            "valid_signals": 0,
            "clusters_formed": 0,
            "pipeline_started_at": datetime.utcnow().isoformat(),
        }

        # Stage 1: Signal Extraction
        logger.info(f"[DeepSeek Coordinator] Stage 1: Extracting signals from {len(raw_items)} items")
        signals = await self.extract_signals(raw_items)
        stats["valid_signals"] = len(signals)

        if not signals:
            stats["pipeline_completed_at"] = datetime.utcnow().isoformat()
            return {"stats": stats, "claude_tasks": [], "clusters": []}

        # Stage 2: Clustering
        logger.info(f"[DeepSeek Coordinator] Stage 2: Clustering {len(signals)} signals")
        clusters = await self.cluster_signals(signals)
        stats["clusters_formed"] = len(clusters)

        # Stage 3: Market Analysis (optional)
        if not skip_market_analysis:
            logger.info(f"[DeepSeek Coordinator] Stage 3: Market analysis for {len(clusters)} clusters")
            clusters = await self.analyze_market_context(clusters)

        # Stage 4: Prepare for Claude
        logger.info("[DeepSeek Coordinator] Stage 4: Preparing structured data for Claude")
        claude_tasks = self.prepare_for_claude(clusters)

        stats["pipeline_completed_at"] = datetime.utcnow().isoformat()

        return {
            "stats": stats,
            "claude_tasks": claude_tasks,
            "clusters": clusters,
        }


# Module-level singleton
_coordinator: Optional[DeepSeekCoordinatorService] = None


def get_deepseek_coordinator() -> DeepSeekCoordinatorService:
    """Get or create the DeepSeek coordinator singleton."""
    global _coordinator
    if _coordinator is None:
        _coordinator = DeepSeekCoordinatorService()
    return _coordinator
