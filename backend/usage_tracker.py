"""
usage_tracker.py
Track LLM API usage per user, per provider, per day.
Enforces quotas: Free=50/day, Premium=500/day, Team=unlimited.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

USAGE_FILE = Path.home() / ".qamill" / "usage.json"


class UsageTracker:
    """Track LLM usage per user, provider, and day."""

    def __init__(self):
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        USAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _today_key(self) -> str:
        """ISO date string for today (YYYY-MM-DD)."""
        return datetime.utcnow().strftime("%Y-%m-%d")

    def track_usage(
        self,
        user_email: str,
        provider: str,
        tokens_used: int = 1,
        task: str = "test_generation",
    ) -> None:
        """
        Record an LLM API call.
        Args:
            user_email: User's email (from OAuth or local account)
            provider: LLM provider (claude, gpt, grok, github, ollama)
            tokens_used: Approximate tokens consumed
            task: What the user was doing (test_generation, analysis, etc.)
        """
        data = self._load()
        today = self._today_key()

        # Initialize user's entry if needed
        if user_email not in data:
            data[user_email] = {"tier": "free", "daily": {}}

        # Initialize today's entry if needed
        if today not in data[user_email]["daily"]:
            data[user_email]["daily"][today] = []

        # Append usage record
        record = {
            "timestamp": int(time.time()),
            "provider": provider,
            "tokens": tokens_used,
            "task": task,
        }
        data[user_email]["daily"][today].append(record)

        # Clean up old entries (keep last 90 days only)
        cutoff_date = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
        for date_key in list(data[user_email]["daily"].keys()):
            if date_key < cutoff_date:
                del data[user_email]["daily"][date_key]

        self._save(data)

    def get_today_usage(self, user_email: str) -> dict:
        """
        Get today's usage for a user.
        Returns:
            {
                "total_calls": int,
                "total_tokens": int,
                "by_provider": {"claude": 10, "gpt": 5, ...},
                "by_task": {"test_generation": 12, "analysis": 3, ...},
                "quota_limit": int,
                "quota_remaining": int,
            }
        """
        data = self._load()
        user_data = data.get(user_email, {"tier": "free", "daily": {}})
        today = self._today_key()
        today_records = user_data.get("daily", {}).get(today, [])

        # Calculate stats
        total_calls = len(today_records)
        total_tokens = sum(r.get("tokens", 1) for r in today_records)

        by_provider = {}
        by_task = {}
        for record in today_records:
            provider = record.get("provider", "unknown")
            task = record.get("task", "unknown")
            by_provider[provider] = by_provider.get(provider, 0) + 1
            by_task[task] = by_task.get(task, 0) + 1

        # Quota based on tier
        tier = user_data.get("tier", "free")
        quotas = {"free": 50, "premium": 500, "team": 999999}
        quota_limit = quotas.get(tier, 50)
        quota_remaining = max(0, quota_limit - total_calls)

        return {
            "tier": tier,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "by_provider": by_provider,
            "by_task": by_task,
            "quota_limit": quota_limit,
            "quota_remaining": quota_remaining,
            "quota_exceeded": total_calls >= quota_limit,
        }

    def get_usage_summary(self, user_email: str, days: int = 30) -> dict:
        """Get usage summary over N days."""
        data = self._load()
        user_data = data.get(user_email, {"tier": "free", "daily": {}})

        all_records = []
        for i in range(days):
            date_key = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            all_records.extend(user_data.get("daily", {}).get(date_key, []))

        total_calls = len(all_records)
        total_tokens = sum(r.get("tokens", 1) for r in all_records)

        by_provider = {}
        for record in all_records:
            provider = record.get("provider", "unknown")
            by_provider[provider] = by_provider.get(provider, 0) + 1

        return {
            "tier": user_data.get("tier", "free"),
            "period_days": days,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "by_provider": by_provider,
            "avg_calls_per_day": total_calls / days if days > 0 else 0,
        }

    def set_tier(self, user_email: str, tier: str) -> None:
        """Upgrade user tier (free, premium, team)."""
        data = self._load()
        if user_email not in data:
            data[user_email] = {"tier": tier, "daily": {}}
        else:
            data[user_email]["tier"] = tier
        self._save(data)

    def check_quota(self, user_email: str) -> tuple[bool, str]:
        """
        Check if user has quota remaining.
        Returns: (has_quota, message)
        """
        usage = self.get_today_usage(user_email)
        if usage["quota_exceeded"]:
            return False, f"Daily quota exceeded ({usage['total_calls']}/{usage['quota_limit']}). Upgrade or try again tomorrow."
        if usage["quota_remaining"] <= 5:
            return True, f"⚠️ Only {usage['quota_remaining']} requests remaining today"
        return True, ""


# Global instance
tracker = UsageTracker()
