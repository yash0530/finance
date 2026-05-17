#!/usr/bin/env python3
"""
llm_service.py — Multi-provider LLM abstraction for the Portfolio Intelligence Tool.

Supports:
  - Anthropic Claude  (claude-3-5-haiku, claude-opus-4, etc.)
  - Google Gemini     (gemini-2.0-flash, gemini-2.5-pro, etc.)
  - Ollama (local)    (llama3.2, mistral, etc.)

Cost-optimized routing:
  task_type='sentiment'   → model_fast  (cheap, low latency)
  task_type='explanation' → model_fast
  task_type='analysis'    → model_deep  (best quality)
  task_type='thesis'      → model_deep
  task_type='edgar'       → model_deep  (long context required)
"""

import json
import re
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from db import get_llm_settings, get_llm_api_key

logger = logging.getLogger(__name__)

# ============================================================================
# Task routing constants
# ============================================================================

FAST_TASKS = {"sentiment", "explanation", "summary", "quick"}
DEEP_TASKS = {"analysis", "thesis", "edgar", "rebalance", "compare"}


def _route_model(task_type: str, settings: Dict) -> str:
    """Return the appropriate model name for the given task type."""
    if task_type in DEEP_TASKS:
        return settings.get("model_deep", "llama3.2")
    return settings.get("model_fast", "llama3.2")


# ============================================================================
# Provider Implementations
# ============================================================================

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, model: str) -> str:
        """Send a completion request and return the response text."""
        ...

    def complete_json(self, system_prompt: str, user_prompt: str, model: str) -> Dict:
        """Send a completion request and parse the response as JSON.

        Tries to extract a JSON block from the response even if the model
        includes extra prose around it.
        """
        raw = self.complete(system_prompt, user_prompt, model)
        return _extract_json(raw)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider via the official SDK."""

    def __init__(self, api_key: str):
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            )

    def complete(self, system_prompt: str, user_prompt: str, model: str) -> str:
        message = self._client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return message.content[0].text


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider via the official SDK."""

    def __init__(self, api_key: str):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._genai = genai
        except ImportError:
            raise RuntimeError(
                "google-generativeai not installed. Run: pip install google-generativeai"
            )

    def complete(self, system_prompt: str, user_prompt: str, model: str) -> str:
        gem_model = self._genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt
        )
        response = gem_model.generate_content(user_prompt)
        return response.text


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider via its REST API."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        import requests
        self._requests = requests
        self._base_url = base_url.rstrip("/")

    def complete(self, system_prompt: str, user_prompt: str, model: str) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        resp = self._requests.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ============================================================================
# Provider Factory
# ============================================================================

def _build_provider(settings: Dict, api_key: str) -> BaseLLMProvider:
    """Instantiate the correct provider based on current settings."""
    provider = settings.get("provider", "ollama")

    if provider == "claude":
        if not api_key:
            raise ValueError("Claude selected but no API key configured. Go to Settings.")
        return ClaudeProvider(api_key)

    elif provider == "gemini":
        if not api_key:
            raise ValueError("Gemini selected but no API key configured. Go to Settings.")
        return GeminiProvider(api_key)

    elif provider == "ollama":
        base_url = settings.get("base_url", "http://localhost:11434")
        return OllamaProvider(base_url)

    else:
        raise ValueError(f"Unknown LLM provider: '{provider}'. Choose claude, gemini, or ollama.")


# ============================================================================
# Public API
# ============================================================================

def _get_provider_and_model(task_type: str):
    """Load settings, build provider, select model."""
    settings = get_llm_settings()
    api_key = get_llm_api_key()
    provider = _build_provider(settings, api_key)
    model = _route_model(task_type, settings)
    return provider, model


def generate_thesis(context_bundle: Dict) -> Dict:
    """Generate a full investment thesis from a context bundle.

    Args:
        context_bundle: Dict with keys: ticker, company_name, sector,
                        fundamentals, technicals, sentiment, edgar_summary,
                        portfolio_context (optional)

    Returns:
        Structured thesis dict with summary, bull_case, bear_case,
        recommendation, conviction, target_price_range, action_items.
    """
    provider, model = _get_provider_and_model("thesis")

    system_prompt = """You are a senior equity research analyst at a top hedge fund.
You produce concise, high-conviction investment theses backed by data.
Always respond with valid JSON matching the exact schema provided.
Do not include markdown code fences or any text outside the JSON object."""

    user_prompt = f"""Analyze this stock and produce an investment thesis.

{_format_context_bundle(context_bundle)}

Respond ONLY with a JSON object matching this exact schema:
{{
  "summary": "<one sentence verdict>",
  "bull_case": ["<reason 1>", "<reason 2>", "<reason 3>"],
  "bear_case": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "key_catalysts": ["<upcoming event or catalyst>"],
  "recommendation": "<BUY | HOLD | TRIM | AVOID>",
  "conviction": "<HIGH | MEDIUM | LOW>",
  "target_price_range": {{"low": 0, "high": 0, "timeframe": "12 months"}},
  "action_items": ["<specific actionable step>"]
}}"""

    return provider.complete_json(system_prompt, user_prompt, model)


def score_sentiment(headlines: list[str], ticker: str) -> Dict:
    """Score a list of news headlines for a ticker.

    Returns:
        Dict with score (0-10), label ('bullish'|'neutral'|'bearish'), reasoning.
    """
    provider, model = _get_provider_and_model("sentiment")

    system_prompt = """You are a financial news sentiment analyst.
Score sentiment for stock news as JSON. Be concise."""

    headlines_text = "\n".join(f"- {h}" for h in headlines[:15])
    user_prompt = f"""Score the market sentiment for {ticker} based on these headlines:

{headlines_text}

Respond ONLY with JSON:
{{
  "score": <0.0 to 10.0, where 0=very bearish, 5=neutral, 10=very bullish>,
  "label": "<bullish | neutral | bearish>",
  "reasoning": "<one sentence explanation>"
}}"""

    return provider.complete_json(system_prompt, user_prompt, model)


def summarize_edgar_section(text: str, section: str, ticker: str) -> str:
    """Summarize a section of an SEC filing.

    Args:
        text: Raw filing section text (will be truncated to fit context)
        section: 'business' | 'risk_factors' | 'mda'
        ticker: Ticker symbol for context

    Returns:
        Plain-text summary (3-5 bullet points).
    """
    provider, model = _get_provider_and_model("edgar")

    section_names = {
        "business": "Business Description (Item 1)",
        "risk_factors": "Risk Factors (Item 1A)",
        "mda": "Management Discussion & Analysis (Item 7)"
    }

    system_prompt = f"""You are a financial analyst extracting key insights from SEC filings.
Be concise, factual, and investor-focused. Extract only the most material information."""

    # Truncate to avoid token limits — 8000 chars ≈ ~2000 tokens
    truncated = text[:8000] + ("...[truncated]" if len(text) > 8000 else "")

    user_prompt = f"""Summarize the {section_names.get(section, section)} from {ticker}'s SEC filing.

--- FILING TEXT ---
{truncated}
--- END ---

Provide 4-5 concise bullet points capturing the most investor-relevant information.
Focus on: business model, competitive position, key risks, financial outlook.
Return plain text bullet points only (no JSON, no markdown headers)."""

    return provider.complete(system_prompt, user_prompt, model)


def generate_rebalance_narrative(analysis: Dict) -> str:
    """Generate a plain-English rebalancing recommendation narrative.

    Args:
        analysis: Output from rebalancing_engine.analyze_portfolio()

    Returns:
        3-5 paragraph narrative with specific recommendations.
    """
    provider, model = _get_provider_and_model("rebalance")

    system_prompt = """You are a portfolio manager giving actionable rebalancing advice.
Be direct, specific, and data-driven. Avoid generic financial advice disclaimers."""

    user_prompt = f"""Based on this portfolio analysis, write a rebalancing recommendation:

{json.dumps(analysis, indent=2, default=str)}

Write 3-4 paragraphs:
1. Current state of the portfolio (key observations)
2. Positions to trim or exit (with specific reasoning)
3. Positions to add or increase (with specific reasoning)
4. Overall strategic advice and priority order"""

    return provider.complete(system_prompt, user_prompt, model)


def compare_tickers(reports: list[Dict]) -> Dict:
    """Generate a comparative analysis of multiple tickers.

    Args:
        reports: List of research report dicts (from research_engine)

    Returns:
        Comparison dict with winner, rankings, and per-ticker notes.
    """
    provider, model = _get_provider_and_model("compare")

    tickers = [r.get("ticker", "") for r in reports]

    system_prompt = """You are a senior equity analyst comparing investment opportunities.
Be direct about which is the best opportunity and why. Respond with valid JSON only."""

    summaries = []
    for r in reports:
        t = r.get("ticker", "")
        fund = r.get("fundamentals", {})
        thesis = r.get("thesis", {})
        summaries.append(
            f"{t}: {thesis.get('summary', 'N/A')} | "
            f"Rec: {thesis.get('recommendation', 'N/A')} | "
            f"Conviction: {thesis.get('conviction', 'N/A')} | "
            f"P/E: {fund.get('forward_pe', 'N/A')} | "
            f"Rev Growth: {fund.get('revenue_growth', 'N/A')}"
        )

    user_prompt = f"""Compare these {len(tickers)} stocks: {', '.join(tickers)}

{chr(10).join(summaries)}

Respond ONLY with JSON:
{{
  "winner": "<ticker>",
  "ranking": ["<1st>", "<2nd>", ...],
  "summary": "<2-3 sentence overall comparison>",
  "per_ticker": {{
    "<ticker>": {{
      "strengths": ["<strength 1>"],
      "weaknesses": ["<weakness 1>"],
      "best_for": "<growth investors | value investors | income investors | ...>"
    }}
  }}
}}"""

    return provider.complete_json(system_prompt, user_prompt, model)


# ============================================================================
# Helpers
# ============================================================================

def _format_context_bundle(ctx: Dict) -> str:
    """Format a context bundle dict into a readable prompt string."""
    lines = []
    lines.append(f"COMPANY: {ctx.get('company_name', ctx.get('ticker', ''))} ({ctx.get('ticker', '')})")
    lines.append(f"SECTOR: {ctx.get('sector', 'Unknown')}")
    lines.append("")

    fund = ctx.get("fundamentals", {})
    if fund:
        lines.append("FUNDAMENTALS:")
        lines.append(f"  Revenue (TTM): {fund.get('revenue_fmt', 'N/A')}, YoY Growth: {fund.get('revenue_growth_fmt', 'N/A')}")
        lines.append(f"  Net Income: {fund.get('net_income_fmt', 'N/A')}, Profit Margin: {fund.get('profit_margin_fmt', 'N/A')}")
        lines.append(f"  Forward P/E: {fund.get('forward_pe', 'N/A')}, Trailing P/E: {fund.get('trailing_pe', 'N/A')}")
        lines.append(f"  EPS (TTM): {fund.get('eps', 'N/A')}, Sector Avg P/E: {fund.get('sector_pe_avg', 'N/A')}")
        lines.append(f"  Debt/Equity: {fund.get('debt_equity', 'N/A')}, Current Ratio: {fund.get('current_ratio', 'N/A')}")
        lines.append(f"  Market Cap: {fund.get('market_cap_fmt', 'N/A')}")
        lines.append("")

    tech = ctx.get("technicals", {})
    if tech:
        lines.append("TECHNICAL SIGNALS:")
        lines.append(f"  Price: {tech.get('current_price', 'N/A')}")
        lines.append(f"  52W High: {tech.get('week_52_high', 'N/A')} ({tech.get('pct_from_52w_high', 'N/A')}% from high)")
        lines.append(f"  52W Low: {tech.get('week_52_low', 'N/A')} ({tech.get('pct_from_52w_low', 'N/A')}% from low)")
        lines.append(f"  RSI(14): {tech.get('rsi', 'N/A')}")
        lines.append(f"  50-DMA: {tech.get('ma_50', 'N/A')}, 200-DMA: {tech.get('ma_200', 'N/A')}")
        lines.append(f"  MACD Signal: {tech.get('macd_signal', 'N/A')}")
        lines.append(f"  Chart Patterns: {', '.join(tech.get('patterns', [])) or 'None detected'}")
        lines.append("")

    edgar = ctx.get("edgar_summary", {})
    if edgar:
        lines.append("SEC FILING INSIGHTS:")
        if edgar.get("business"):
            lines.append(f"  Business:\n{edgar['business']}")
        if edgar.get("risks"):
            lines.append(f"  Key Risks:\n{edgar['risks']}")
        if edgar.get("mda"):
            lines.append(f"  Management Outlook:\n{edgar['mda']}")
        lines.append("")

    sent = ctx.get("sentiment", {})
    if sent:
        lines.append("MARKET SENTIMENT (smart-weighted composite):")
        lines.append(f"  Composite Score: {sent.get('composite_score', 'N/A')} / 10")
        lines.append(f"  News Sentiment: {sent.get('news_score', 'N/A')} (weight 40%)")
        lines.append(f"  Analyst Rating: {sent.get('analyst_rating', 'N/A')}, Target: ${sent.get('analyst_target', 'N/A')} (weight 35%)")
        lines.append(f"  Reddit Mentions: {sent.get('reddit_mentions', 'N/A')}, Score: {sent.get('reddit_score', 'N/A')} (weight 15%)")
        if sent.get("top_headlines"):
            lines.append("  Top Headlines:")
            for h in sent["top_headlines"][:3]:
                lines.append(f"    • {h}")
        lines.append("")

    port = ctx.get("portfolio_context")
    if port:
        lines.append("PORTFOLIO CONTEXT:")
        lines.append(f"  Current Weight: {port.get('weight_pct', 'N/A')}%")
        lines.append(f"  Avg Cost Basis: ${port.get('avg_cost', 'N/A')}")
        lines.append(f"  Unrealized P&L: {port.get('unrealized_pnl_pct', 'N/A')}%")
        lines.append("")

    return "\n".join(lines)


def _extract_json(text: str) -> Dict:
    """Extract and parse a JSON object from LLM response text.

    Handles cases where the model wraps JSON in markdown code fences
    or adds prose before/after the JSON block.
    """
    # Strip markdown fences if present
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object within the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Return error structure if all parsing fails
    logger.warning(f"Failed to parse LLM JSON response: {text[:200]}")
    return {"error": "Failed to parse LLM response", "raw": text[:500]}
