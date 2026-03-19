#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import signal
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, TypeVar, Union, runtime_checkable
from concurrent.futures import ProcessPoolExecutor

import aiofiles
import aiofiles.os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

class Cfg:
    # SECURITY: Token MUST be set via environment variable TELEGRAM_BOT_TOKEN
    # DO NOT hardcode tokens - see: https://core.telegram.org/bots/api#authorizing-your-bot
    TELEGRAM_TOKEN: str = os.getenv("8558040667:AAHYigQj3m6riweRX3u6pzj5Us6VRR086pU", "")
    # Admin configuration - updated with your ID
    ADMIN_USER_IDS: List[int] = [8581545536]  # @PYZADE
    DATA_DIR: Path = Path.home() / ".dev_assistant"
    MAX_PAYLOAD: int = 10000
    REGEX_TIMEOUT_MS: int = 500
    RATE_LIMIT_PER_MIN: int = 30
    BATCH_FLUSH_SEC: int = 60
    BATCH_MAX_SIZE: int = 100

    @classmethod
    def validate(cls) -> None:
        if not cls.TELEGRAM_TOKEN or ":" not in cls.TELEGRAM_TOKEN:
            raise RuntimeError(
                "Invalid TELEGRAM_BOT_TOKEN format. "
                "Set environment variable: export TELEGRAM_BOT_TOKEN='your_token_here'"
            )
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

class Logger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s'))
        self._logger.addHandler(handler)

    def _log(self, level: int, msg: str, **kwargs) -> None:
        ctx = {"timestamp": datetime.now(timezone.utc).isoformat(), "correlation_id": str(uuid.uuid4())[:8], **kwargs}
        self._logger.log(level, f"{msg} | {json.dumps(ctx, default=str)}")

    def info(self, msg: str, **kwargs) -> None:
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        self._log(logging.ERROR, msg, **kwargs)

logger = Logger("dev_assistant")

class FeatureCategory(Enum):
    DEBUG = auto()
    REVIEW = auto()
    DOCUMENTATION = auto()
    PLANNING = auto()
    SECURITY = auto()
    OPTIMIZATION = auto()
    COLLABORATION = auto()

@dataclass(frozen=True)
class Feature:
    id: int
    name: str
    command: str
    category: FeatureCategory
    description: str
    example: str
    requires_reply: bool = False
    supports_ai: bool = False

@dataclass
class UsageEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_hash: str = ""
    feature_id: int = 0
    payload_length: int = 0
    payload_hash: str = ""
    processing_time_ms: float = 0.0
    response_type: str = ""
    success: bool = True
    error_category: Optional[str] = None
    session_duration_sec: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@runtime_checkable
class FeatureHandler(Protocol):
    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        ...

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        ...

class Registry:
    def __init__(self):
        self._handlers: Dict[int, FeatureHandler] = {}
        self._features: Dict[int, Feature] = {}

    def register(self, feature: Feature, handler: FeatureHandler) -> None:
        self._handlers[feature.id] = handler
        self._features[feature.id] = feature
        logger.info(f"Registered feature {feature.id}: {feature.name}")

    def get(self, feature_id: int) -> Optional[tuple[Feature, FeatureHandler]]:
        if feature_id in self._features:
            return (self._features[feature_id], self._handlers[feature_id])
        return None

    def list_features(self, category: Optional[FeatureCategory] = None) -> List[Feature]:
        features = list(self._features.values())
        if category:
            features = [f for f in features if f.category == category]
        return sorted(features, key=lambda f: f.id)

registry = Registry()

def feature(feature_id: int, name: str, category: FeatureCategory, description: str, example: str, requires_reply: bool = False, supports_ai: bool = False):
    def decorator(cls: type[FeatureHandler]) -> type[FeatureHandler]:
        feat = Feature(id=feature_id, name=name, command=f"/use {feature_id}", category=category, description=description, example=example, requires_reply=requires_reply, supports_ai=supports_ai)
        registry.register(feat, cls())
        return cls
    return decorator

class StateManager:
    def __init__(self, base_path: Path):
        self._base_path = base_path.resolve()
        self._lock = asyncio.Lock()
        self._pending: List[UsageEvent] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._validate_path()

    def _validate_path(self) -> None:
        allowed = Path.home() / ".dev_assistant"
        try:
            self._base_path.relative_to(allowed)
        except ValueError:
            raise RuntimeError(f"Path {self._base_path} outside allowed directory {allowed}")

    async def append_event(self, event: UsageEvent) -> None:
        async with self._lock:
            self._pending.append(event)
            if len(self._pending) >= Cfg.BATCH_MAX_SIZE:
                await self._flush()
            elif self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._scheduled_flush())

    async def _scheduled_flush(self) -> None:
        await asyncio.sleep(Cfg.BATCH_FLUSH_SEC)
        await self._flush()

    async def _flush(self) -> None:
        async with self._lock:
            if not self._pending:
                return
            events_to_write = self._pending
            self._pending = []
            try:
                tmp_path = str(self._base_path.with_suffix('.tmp'))
                existing = await self._load_existing()
                existing.extend([e.to_dict() for e in events_to_write])
                existing = existing[-1000:]
                async with aiofiles.open(tmp_path, 'w') as f:
                    await f.write(json.dumps(existing, indent=2, default=str))
                await aiofiles.os.replace(tmp_path, str(self._base_path))
                logger.info(f"Flushed {len(events_to_write)} events", total_events=len(existing))
            except Exception as e:
                logger.error(f"Flush failed: {e}", error_type=type(e).__name__)
                self._pending.extend(events_to_write)

    async def _load_existing(self) -> List[Dict]:
        if not await aiofiles.os.path.exists(str(self._base_path)):
            return []
        try:
            async with aiofiles.open(str(self._base_path), 'r') as f:
                content = await f.read()
                return json.loads(content) if content else []
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"State load failed: {e}")
            return []

    async def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        events = await self._load_existing()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [e for e in events if datetime.fromisoformat(e['timestamp']) > cutoff]
        by_feature = {}
        hourly_dist = {}
        for e in recent:
            fid = e['feature_id']
            by_feature[fid] = by_feature.get(fid, 0) + 1
            hour = datetime.fromisoformat(e['timestamp']).hour
            hourly_dist[hour] = hourly_dist.get(hour, 0) + 1
        return {
            "period_days": days,
            "total_events": len(recent),
            "unique_users": len(set(e['user_hash'] for e in recent)),
            "top_features": dict(sorted(by_feature.items(), key=lambda x: -x[1])[:5]),
            "hourly_distribution": hourly_dist,
            "avg_processing_ms": sum(e['processing_time_ms'] for e in recent) / len(recent) if recent else 0
        }

class Security:
    @staticmethod
    def hash_user_id(chat_id: int) -> str:
        return hashlib.sha256(f"{chat_id}:{Cfg.TELEGRAM_TOKEN[:10]}".encode()).hexdigest()[:16]

    @staticmethod
    def sanitize_payload(payload: str) -> tuple[str, Optional[str]]:
        if len(payload) > Cfg.MAX_PAYLOAD:
            return (payload[:Cfg.MAX_PAYLOAD], f"Payload truncated to {Cfg.MAX_PAYLOAD} chars")
        dangerous_patterns = [
            (r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', re.IGNORECASE),
            (r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', 0),
        ]
        for pattern, flags in dangerous_patterns:
            if re.search(pattern, payload, flags):
                return (re.sub(pattern, '', payload, flags=flags), "Potentially dangerous content filtered")
        return (payload, None)

    @staticmethod
    async def safe_regex_compile(pattern: str) -> tuple[Optional[re.Pattern], Optional[str]]:
        def compile_in_process(pat: str):
            try:
                return re.compile(pat)
            except Exception as e:
                return e
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as executor:
            try:
                result = await asyncio.wait_for(loop.run_in_executor(executor, compile_in_process, pattern), timeout=Cfg.REGEX_TIMEOUT_MS / 1000)
                if isinstance(result, Exception):
                    return (None, str(result))
                return (result, None)
            except asyncio.TimeoutError:
                return (None, "Regex compilation timeout - possible ReDoS")
            except Exception as e:
                return (None, f"Regex compilation failed: {e}")

class RateLimiter:
    def __init__(self):
        self._buckets: Dict[str, tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, user_hash: str) -> tuple[bool, Optional[int]]:
        async with self._lock:
            now = time.time()
            tokens, last = self._buckets.get(user_hash, (Cfg.RATE_LIMIT_PER_MIN, now))
            elapsed = now - last
            tokens = min(Cfg.RATE_LIMIT_PER_MIN, tokens + elapsed * (Cfg.RATE_LIMIT_PER_MIN / 60))
            if tokens >= 1:
                self._buckets[user_hash] = (tokens - 1, now)
                return (True, None)
            wait_sec = int((1 - tokens) * 60 / Cfg.RATE_LIMIT_PER_MIN) + 1
            return (False, wait_sec)

@feature(1, "PR Review", FeatureCategory.REVIEW, "Analyzes PR descriptions for review focus areas and risk assessment", "/use 1 Add user authentication module with JWT tokens")
class PRReviewHandler:
    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        risk_indicators = []
        lowered = payload.lower()
        if any(k in lowered for k in ["auth", "login", "password", "token", "jwt"]):
            risk_indicators.append("🔐 Security-critical: Review authentication logic carefully")
        if any(k in lowered for k in ["payment", "billing", "transaction", "money"]):
            risk_indicators.append("💰 Financial impact: Verify transaction integrity")
        if any(k in lowered for k in ["migration", "schema", "database", "drop"]):
            risk_indicators.append("🗄️ Database change: Check rollback strategy")
        if "refactor" in lowered and any(k in lowered for k in ["core", "base", "util"]):
            risk_indicators.append("🔧 Core refactor: Verify dependent modules")
        review_checklist = [
            "□ Verify test coverage for new logic",
            "□ Check error handling paths",
            "□ Validate input sanitization",
            "□ Review for race conditions",
            "□ Confirm monitoring/alerting added"
        ]
        response = f"📋 **PR Review Analysis**\n\n**Scope:** {payload[:200]}{'...' if len(payload) > 200 else ''}\n\n"
        if risk_indicators:
            response += "**Risk Flags:**\n" + "\n".join(f"• {r}" for r in risk_indicators) + "\n\n"
        response += "**Review Checklist:**\n" + "\n".join(review_checklist)
        response += "\n\n💡 Pro tip: Use `/use 9` for API contract diff analysis if this changes endpoints"
        return response

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        return (len(payload) >= 10, "PR description too short (min 10 chars)") if len(payload) < 10 else (True, None)

@feature(2, "CI Debug", FeatureCategory.DEBUG, "Root cause analysis from CI/CD logs with pattern recognition", "/use 2 npm test failed: timeout in integration suite")
class CIDebugHandler:
    PATTERNS = {
        r"\btimes?out\b|\btimed out\b": {
            "category": "Timeout",
            "causes": ["External service latency", "Insufficient test timeouts", "Resource contention"],
            "fixes": ["Increase test timeout", "Mock external calls", "Check service health"]
        },
        r"module not found|cannot find module|import error|no module named": {
            "category": "Dependency",
            "causes": ["Missing lockfile sync", "Node/Python version mismatch", "Monorepo hoisting issues"],
            "fixes": ["Regenerate lockfile", "Verify CI environment matches dev", "Check workspace config"]
        },
        r"permission denied|eacces|access denied": {
            "category": "Permissions",
            "causes": ["Container user mismatch", "Missing executable bit", "Secret scope issues"],
            "fixes": ["Fix Dockerfile USER directive", "chmod +x scripts", "Check CI secret permissions"]
        },
        r"out of memory|oom|heap|allocation failed": {
            "category": "Memory",
            "causes": ["Memory leak in tests", "Parallelism too high", "Large dataset processing"],
            "fixes": ["Limit Jest/Pytest workers", "Increase container memory", "Stream large files"]
        },
        r"connection refused|econnrefused|network error": {
            "category": "Network",
            "causes": ["Service not ready", "Port conflict", "Firewall rules"],
            "fixes": ["Add healthcheck waits", "Verify port mappings", "Check security groups"]
        }
    }

    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        text = payload.lower()
        matches = []
        for pattern, info in self.PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(info)
        if not matches:
            return ("🔍 **CI Debug Analysis**\n\nNo obvious patterns detected in logs.\n\n**Recommended next steps:**\n1. Isolate the failing job (re-run independently)\n2. Compare with last passing commit (git bisect)\n3. Enable verbose logging (--verbose, DEBUG=*)\n4. Check for flaky test patterns (use `/use 25`)\n\nPaste a larger log excerpt (up to 500 lines) for deeper analysis.")
        response = "🔍 **CI Debug Analysis**\n\n"
        response += f"**Detected {len(matches)} issue type(s):**\n\n"
        for i, match in enumerate(matches[:3], 1):
            response += f"**{i}. {match['category']} Issue**\n"
            response += f"Likely causes: {', '.join(match['causes'])}\n"
            response += f"Quick fixes: {', '.join(match['fixes'])}\n\n"
        response += "**General recovery:**\n"
        response += "• Re-run with `DEBUG=*` or `--verbose`\n"
        response += "• Check resource metrics (CPU/memory graphs)\n"
        response += "• Verify recent infrastructure changes"
        return response

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        return (True, None)

@feature(3, "Commit Check", FeatureCategory.REVIEW, "Validates Conventional Commits format and suggests improvements", "/use 3 feat(auth): add OAuth2 login flow")
class CommitCheckHandler:
    CONVENTIONAL_COMMIT_REGEX = re.compile(
        r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
        r"(?:\((?P<scope>[\w\-/.]+)\))?"
        r"(?P<breaking>!)?"
        r": (?P<message>.{10,100})$",
        re.IGNORECASE
    )

    TYPE_DESCRIPTIONS = {
        "feat": "✨ New feature",
        "fix": "🐛 Bug fix",
        "docs": "📚 Documentation",
        "style": "💎 Code style (formatting)",
        "refactor": "♻️ Refactoring",
        "perf": "⚡ Performance",
        "test": "✅ Tests",
        "build": "📦 Build system",
        "ci": "🔄 CI/CD",
        "chore": "🔧 Maintenance",
        "revert": "⏪ Revert"
    }

    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        msg = payload.strip()
        match = self.CONVENTIONAL_COMMIT_REGEX.match(msg)
        if not match:
            return self._generate_suggestion(msg)
        groups = match.groupdict()
        analysis = [
            "✅ **Valid Conventional Commit**",
            "",
            f"**Type:** {self.TYPE_DESCRIPTIONS.get(groups['type'].lower(), groups['type'])}",
        ]
        if groups['scope']:
            analysis.append(f"**Scope:** `{groups['scope']}`")
        if groups['breaking']:
            analysis.append("**⚠️ BREAKING CHANGE** - Ensure major version bump")
        analysis.extend([
            "",
            "**Message:** " + groups['message'],
            "",
            "**Quality checks:**",
            "□ Imperative mood (add/fix, not added/fixed)",
            "□ No period at end",
            "□ Concise but descriptive (10-100 chars)"
        ])
        if len(groups['message']) < 20:
            analysis.append("⚡ Tip: Message is brief—consider elaborating in body (git commit -m \"title\" -m \"body\")")
        return "\n".join(analysis)

    def _generate_suggestion(self, msg: str) -> str:
        lowered = msg.lower()
        suggested_type = "chore"
        type_keywords = {
            "feat": ["add", "new", "implement", "introduce"],
            "fix": ["fix", "bug", "repair", "resolve", "correct"],
            "docs": ["doc", "readme", "comment", "guide"],
            "refactor": ["refactor", "restructure", "simplify", "clean"],
            "perf": ["optim", "speed", "fast", "slow", "performance"],
            "test": ["test", "spec", "coverage"]
        }
        for ttype, keywords in type_keywords.items():
            if any(k in lowered for k in keywords):
                suggested_type = ttype
                break
        scope = ""
        words = msg.split()
        if len(words) > 1 and ('/' in words[0] or words[0].isalnum()):
            scope = words[0].strip("/:")
        suggestion = f"{suggested_type}"
        if scope:
            suggestion += f"({scope})"
        suggestion += f": {msg[:60].lower()}"
        return (
            "❌ **Invalid Conventional Commit Format**\n\n"
            f"**Your input:** `{msg[:70]}`\n\n"
            f"**Suggested format:** `{suggestion}`\n\n"
            "**Format:** `<type>(<scope>): <description>`\n"
            "**Types:** feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert\n\n"
            "**Examples:**\n"
            "• `feat(api): add rate limiting middleware`\n"
            "• `fix(db): resolve connection pool exhaustion`\n"
            "• `refactor(core): simplify auth flow`"
        )

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        return (len(payload) >= 5, "Commit message too short") if len(payload) < 5 else (True, None)

@feature(4, "Release Notes", FeatureCategory.DOCUMENTATION, "Generates structured release notes from merged PRs", "/use 4\n- feat: add dark mode\n- fix: resolve login redirect\n- docs: update API reference")
class ReleaseNotesHandler:
    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        items = [line.strip("-• * ") for line in payload.split("\n") if line.strip()]
        if not items:
            return "❌ No items found. Provide bullet points, one per line."
        categories = {
            "🚀 Features": [],
            "🐛 Fixes": [],
            "⚡ Performance": [],
            "🔧 Maintenance": [],
            "📚 Documentation": []
        }
        for item in items:
            lowered = item.lower()
            if any(k in lowered for k in ["feat", "add", "new", "implement"]):
                categories["🚀 Features"].append(item)
            elif any(k in lowered for k in ["fix", "bug", "repair", "resolve"]):
                categories["🐛 Fixes"].append(item)
            elif any(k in lowered for k in ["perf", "optim", "speed", "fast"]):
                categories["⚡ Performance"].append(item)
            elif any(k in lowered for k in ["doc", "readme", "guide", "wiki"]):
                categories["📚 Documentation"].append(item)
            else:
                categories["🔧 Maintenance"].append(item)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = [
            f"## Release {today}",
            "",
            f"**Summary:** {len(items)} changes across {sum(1 for v in categories.values() if v)} categories",
            ""
        ]
        for cat_name, cat_items in categories.items():
            if cat_items:
                lines.append(f"### {cat_name}")
                for item in cat_items:
                    lines.append(f"- {item}")
                lines.append("")
        lines.extend([
            "---",
            "**Full Changelog:** [compare view](https://github.com/...)",
            "",
            "💡 Next steps: Use `/use 17` to draft ADR if this includes architectural changes"
        ])
        return "\n".join(lines)

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        return (True, None)

@feature(12, "SQL Review", FeatureCategory.OPTIMIZATION, "Analyzes SQL queries for performance and anti-patterns", "/use 12 SELECT * FROM users WHERE created_at > '2024-01-01' ORDER BY id")
class SQLReviewHandler:
    ANTI_PATTERNS = [
        (r"SELECT\s+\*", "⚠️ `SELECT *` fetches unnecessary columns—specify needed fields"),
        (r"WHERE\s+.+?LIKE\s+['\"]?%", "🐌 Leading wildcard `LIKE '%...'` bypasses indexes"),
        (r"ORDER\s+BY\s+.+?(?!.*LIMIT)", "📊 `ORDER BY` without `LIMIT` can be expensive on large tables"),
        (r"NOT\s+IN\s*\(", "🚫 `NOT IN` with subqueries can be slow—consider `NOT EXISTS`"),
        (r"SELECT\s+DISTINCT", "🔍 `DISTINCT` suggests possible Cartesian product—verify joins"),
        (r"N\+1|for\s*\(.*in.*\):\s*", "⚡ N+1 query pattern detected—use JOIN or prefetch"),
    ]

    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        q = payload.strip()
        findings = []
        for pattern, warning in self.ANTI_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                findings.append(warning)
        if re.search(r"^SELECT\s+", q, re.IGNORECASE) and "WHERE" not in q.upper():
            findings.append("🌊 No `WHERE` clause—consider adding filters for large tables")
        if re.search(r"WHERE\s+.+?=\s*['\"]\d{4}", q):
            findings.append("🔒 Consider parameterizing literals to enable query plan caching")
        response = "🗄️ **SQL Analysis**\n\n"
        response += f"```sql\n{q[:300]}{'...' if len(q) > 300 else ''}\n```\n\n"
        if findings:
            response += "**Findings:**\n" + "\n".join(f"• {f}" for f in findings) + "\n\n"
        else:
            response += "✅ No obvious anti-patterns detected\n\n"
        response += (
            "**Optimization checklist:**\n"
            "□ Run `EXPLAIN (ANALYZE, BUFFERS)` to verify execution plan\n"
            "□ Check index usage with `EXPLAIN`\n"
            "□ Verify statistics are up to date (`ANALYZE` table)\n"
            "□ Test with production-like data volumes"
        )
        return response

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        has_sql = any(k in payload.upper() for k in ["SELECT", "INSERT", "UPDATE", "DELETE", "WITH"])
        return (has_sql, "No SQL keywords detected") if not has_sql else (True, None)

@feature(13, "Regex Test", FeatureCategory.DEBUG, "Safe regex testing with ReDoS protection", "/use 13 ^[a-z]+@[a-z]+\\.com ;; test@example.com")
class RegexTestHandler:
    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        if " ;; " not in payload:
            return "❌ Format: `/use 13 <pattern> ;; <test_text>`"
        pattern, test_text = payload.split(" ;; ", 1)
        pattern, test_text = pattern.strip(), test_text.strip()
        compiled, error = await Security.safe_regex_compile(pattern)
        if error:
            return f"❌ **Regex Error**\n`{error}`"
        if compiled is None:
            return "❌ Failed to compile regex (timeout or error)"
        try:
            matches = compiled.findall(test_text)
            match_count = len(matches)
            positions = []
            for m in compiled.finditer(test_text):
                positions.append((m.start(), m.end(), m.group()))
            response = "🔍 **Regex Test Results**\n\n"
            response += f"**Pattern:** `{pattern}`\n"
            response += f"**Test text:** `{test_text[:100]}{'...' if len(test_text) > 100 else ''}`\n\n"
            response += f"**Total matches:** {match_count}\n"
            if positions:
                response += "**Match positions:**\n"
                for start, end, match in positions[:10]:
                    response += f"• [{start}:{end}] `{match}`\n"
                if len(positions) > 10:
                    response += f"... and {len(positions) - 10} more\n"
            if len(pattern) > 50 or pattern.count("(") > 5:
                response += "\n⚡ Pattern is complex—test performance on large inputs"
            return response
        except Exception as e:
            return f"❌ Match error: {e}"

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        return (" ;; " in payload, "Missing delimiter ` ;; `") if " ;; " not in payload else (True, None)

@feature(14, "Dockerfile Review", FeatureCategory.REVIEW, "Analyzes Dockerfiles for security and optimization", "/use 14 FROM node:18\nRUN npm install\nCOPY . .\nCMD [\"node\", \"app.js\"]")
class DockerfileReviewHandler:
    async def handle(self, payload: str, context: Dict[str, Any]) -> str:
        content = payload
        issues = []
        suggestions = []
        if re.search(r"FROM\s+.*:latest\b", content, re.IGNORECASE):
            issues.append("🚨 Using `latest` tag—pin to specific version for reproducibility")
        if re.search(r"RUN\s+(apt-get|yum|apk)\s+update", content, re.IGNORECASE):
            if not re.search(r"rm\s+-rf\s+/var/lib/apt/lists", content, re.IGNORECASE):
                issues.append("📦 Package cache not cleaned—add `&& rm -rf /var/lib/apt/lists/*`")
        if re.search(r"COPY\s+\.\s+[/\.]", content) and not re.search(r"\.dockerignore", content, re.IGNORECASE):
            suggestions.append("📋 Ensure `.dockerignore` exists to avoid copying sensitive files")
        if re.search(r"RUN\s+npm\s+install", content, re.IGNORECASE):
            if not re.search(r"package-lock\.json|npm\s+ci", content, re.IGNORECASE):
                issues.append("🔒 Use `npm ci` instead of `npm install` in CI for deterministic builds")
        if content.count("RUN") > 3:
            suggestions.append("⚡ Combine RUN commands to reduce layers (use `&&`)")
        if not re.search(r"USER\s+[^r]", content, re.IGNORECASE):
            issues.append("👤 No non-root USER specified—security risk")
        response = "🐳 **Dockerfile Analysis**\n\n"
        if issues:
            response += "**Security/Correctness Issues:**\n" + "\n".join(f"• {i}" for i in issues) + "\n\n"
        if suggestions:
            response += "**Optimizations:**\n" + "\n".join(f"• {s}" for s in suggestions) + "\n\n"
        if not issues and not suggestions:
            response += "✅ Dockerfile looks good!\n\n"
        response += (
            "**Best practices checklist:**\n"
            "□ Multi-stage build for smaller final image\n"
            "□ Specific base image tag (not latest)\n"
            "□ .dockerignore for node_modules, .env, etc.\n"
            "□ Healthcheck defined\n"
            "□ Non-root user"
        )
        return response

    def validate_payload(self, payload: str) -> tuple[bool, Optional[str]]:
        has_docker = any(k in payload.upper() for k in ["FROM", "RUN", "CMD", "ENTRYPOINT", "COPY", "ADD"])
        return (has_docker, "No Dockerfile instructions detected") if not has_docker else (True, None)

class TelegramInterface:
    def __init__(self, state_manager: StateManager, rate_limiter: RateLimiter):
        self._state = state_manager
        self._rate_limiter = rate_limiter
        self._security = Security()

    async def send_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, parse_mode: str = "Markdown") -> None:
        try:
            if update.message:
                await update.message.reply_text(text, parse_mode=parse_mode)
            elif update.effective_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Failed to send message: {e}", error_type=type(e).__name__)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        welcome = (
            "🚀 **Enterprise Developer Assistant**\n\n"
            "40+ specialized tools for engineering workflows.\n\n"
            "**Quick start:**\n"
            "• `/features` — Browse all capabilities\n"
            "• `/categories` — View by category\n"
            "• `/use <id> <input>` — Execute a tool\n"
            "• `/help` — Detailed usage guide\n\n"
            "**Examples:**\n"
            "• `/use 2 npm test timeout error`\n"
            "• `/use 3 \"feat(api): add rate limit\"`\n"
            "• `/use 12 SELECT * FROM users`"
        )
        await self.send_response(update, context, welcome)

    async def cmd_features(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        features = registry.list_features()
        lines = ["📚 **Available Tools** (sorted by ID)\n"]
        for feat in features:
            lines.append(f"**{feat.id}.** {feat.name} — {feat.description[:50]}...")
        lines.append("\n💡 Use `/feature <id>` for detailed help on any tool")
        await self.send_response(update, context, "\n".join(lines))

    async def cmd_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        lines = ["📂 **Tools by Category**\n"]
        for cat in FeatureCategory:
            feats = registry.list_features(category=cat)
            if feats:
                lines.append(f"\n**{cat.name}** ({len(feats)} tools)")
                for feat in feats:
                    lines.append(f"  {feat.id}. {feat.name}")
        await self.send_response(update, context, "\n".join(lines))

    async def cmd_feature(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await self.send_response(update, context, "❌ Usage: `/feature <id>`")
            return
        try:
            fid = int(context.args[0])
            result = registry.get(fid)
            if not result:
                await self.send_response(update, context, f"❌ Unknown feature ID: {fid}")
                return
            feat, _ = result
            detail = (
                f"**#{feat.id} {feat.name}**\n\n"
                f"**Category:** {feat.category.name}\n"
                f"**Description:** {feat.description}\n\n"
                f"**Usage:** `{feat.command} <input>`\n"
                f"**Example:** `{feat.example}`"
            )
            if feat.requires_reply:
                detail += "\n\n⚠️ This tool works best with reply-based input for multi-line content"
            await self.send_response(update, context, detail)
        except ValueError:
            await self.send_response(update, context, "❌ Feature ID must be a number")

    async def cmd_use(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        start_time = time.perf_counter()
        user_hash = self._security.hash_user_id(update.effective_user.id if update.effective_user else 0)
        allowed, wait_sec = await self._rate_limiter.acquire(user_hash)
        if not allowed:
            await self.send_response(update, context, f"⏳ Rate limit exceeded. Try again in {wait_sec} seconds.")
            return
        if len(context.args) < 2:
            await self.send_response(update, context, "❌ Usage: `/use <feature_id> <input>`")
            return
        try:
            feature_id = int(context.args[0])
        except ValueError:
            await self.send_response(update, context, "❌ Feature ID must be a number")
            return
        result = registry.get(feature_id)
        if not result:
            await self.send_response(update, context, f"❌ Unknown feature ID: {feature_id}")
            return
        feature, handler = result
        raw_payload = " ".join(context.args[1:])
        payload, warning = self._security.sanitize_payload(raw_payload)
        valid, error_msg = handler.validate_payload(payload)
        if not valid:
            await self.send_response(update, context, f"❌ {error_msg}")
            return
        try:
            ctx = {"user_hash": user_hash, "feature": feature}
            response = await handler.handle(payload, ctx)
            if warning:
                response = f"⚠️ {warning}\n\n{response}"
            processing_time = (time.perf_counter() - start_time) * 1000
            await self.send_response(update, context, response)
            event = UsageEvent(
                user_hash=user_hash,
                feature_id=feature_id,
                payload_length=len(raw_payload),
                payload_hash=hashlib.sha256(raw_payload.encode()).hexdigest()[:16],
                processing_time_ms=processing_time,
                response_type="native",
                success=True
            )
            await self._state.append_event(event)
        except Exception as e:
            logger.error(f"Feature execution failed: {e}", feature_id=feature_id, error_type=type(e).__name__)
            await self.send_response(update, context, "❌ Internal error processing request. Devs notified.")
            event = UsageEvent(
                user_hash=user_hash,
                feature_id=feature_id,
                payload_length=len(raw_payload),
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
                success=False,
                error_category=type(e).__name__
            )
            await self._state.append_event(event)

    async def cmd_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        # Updated to use configured admin list
        if user_id not in Cfg.ADMIN_USER_IDS:
            await self.send_response(update, context, "🔒 Admin access required")
            return
        stats = await self._state.get_analytics(days=7)
        report = (
            f"📊 **Usage Analytics (Last {stats['period_days']} days)**\n\n"
            f"• **Total requests:** {stats['total_events']}\n"
            f"• **Unique users:** {stats['unique_users']}\n"
            f"• **Avg processing time:** {stats['avg_processing_ms']:.1f}ms\n\n"
            f"**Top features:**\n"
        )
        for fid, count in stats['top_features'].items():
            feat = registry.get(int(fid))
            name = feat[0].name if feat else "Unknown"
            report += f"• {name}: {count} uses\n"
        await self.send_response(update, context, report)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = (
            "❓ **Developer Assistant Help**\n\n"
            "**Commands:**\n"
            "• `/start` — Welcome and quick start\n"
            "• `/features` — List all 40+ tools\n"
            "• `/categories` — Browse by category\n"
            "• `/feature <id>` — Detailed tool info\n"
            "• `/use <id> <input>` — Execute a tool\n"
            "• `/help` — This message\n\n"
            "**Input tips:**\n"
            "• Use quotes for inputs containing spaces\n"
            "• For multi-line inputs, the bot will prompt for a reply\n"
            "• Maximum input size: 10KB\n\n"
            "**Categories:**\n"
            "• Debug: CI analysis, error triage, flaky tests\n"
            "• Review: Code, SQL, Docker, K8s, security\n"
            "• Documentation: Release notes, ADRs, postmortems\n"
            "• Planning: Standups, sprints, learning roadmaps"
        )
        await self.send_response(update, context, help_text)

def build_application() -> Application:
    Cfg.validate()
    state_manager = StateManager(Cfg.DATA_DIR / "analytics.json")
    rate_limiter = RateLimiter()
    interface = TelegramInterface(state_manager, rate_limiter)
    app = Application.builder().token(Cfg.TELEGRAM_TOKEN).build()
    handlers = [
        CommandHandler("start", interface.cmd_start),
        CommandHandler("features", interface.cmd_features),
        CommandHandler("categories", interface.cmd_categories),
        CommandHandler("feature", interface.cmd_feature),
        CommandHandler("use", interface.cmd_use),
        CommandHandler("analytics", interface.cmd_analytics),
        CommandHandler("help", interface.cmd_help),
    ]
    for handler in handlers:
        app.add_handler(handler)
    return app

async def main():
    app = build_application()
    stop_event = asyncio.Event()
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received", signal=sig)
        stop_event.set()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting Enterprise Developer Assistant...")
    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling(allowed_updates=["message"])
        await stop_event.wait()
    finally:
        logger.info("Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
