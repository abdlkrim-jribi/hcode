"""
Execution Analytics System for HCode.

Provides comprehensive analytics for:
- Tool execution patterns
- Performance metrics
- Error analysis
- Reasoning effectiveness
- Resource usage tracking
"""

import json
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class MetricType(Enum):
    """Types of metrics tracked"""


class TimeWindow(Enum):
    """Time windows for aggregation"""


@dataclass
class ToolExecutionEvent:
    """Single tool execution event"""

    tool_name: str
    timestamp: datetime
    duration: float  # seconds
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    file_path: Optional[str] = None
    task_context: Optional[str] = None


@dataclass
class ConversationEvent:
    """Conversation-level event"""

    conversation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = True


class TimeSeriesBuffer:
    """
    Circular buffer for time-series data with automatic cleanup.
    """

    def __init__(self, max_age: timedelta = timedelta(hours=24)):
        self._data: List[Tuple[datetime, Any]] = []
        self._max_age = max_age

    def add(self, value: Any, timestamp: Optional[datetime] = None):
        """Add value to buffer"""
        ts = timestamp or datetime.now()
        self._data.append((ts, value))
        self._cleanup()

    def _cleanup(self):
        """Remove old entries"""
        cutoff = datetime.now() - self._max_age
        self._data = [(ts, v) for ts, v in self._data if ts > cutoff]

    def __len__(self) -> int:
        return len(self._data)


class ToolAnalytics:
    """
    Analytics specifically for tool execution.
    """

    def __init__(self):
        self._events = TimeSeriesBuffer(timedelta(hours=24))
        self._by_tool: Dict[str, List[ToolExecutionEvent]] = defaultdict(list)
        self._error_counts: Dict[str, int] = defaultdict(int)

    def record(self, event: ToolExecutionEvent):
        """Record tool execution event"""
        self._events.add(event, event.timestamp)
        self._by_tool[event.tool_name].append(event)

        if not event.success and event.error_type:
            self._error_counts[event.error_type] += 1

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get statistics for a specific tool"""
        events = self._by_tool.get(tool_name, [])
        if not events:
            return {}

        durations = [e.duration for e in events]
        successes = sum(1 for e in events if e.success)

        return {
            "total_calls": len(events),
            "success_rate": successes / len(events) if events else 0,
            "avg_latency": statistics.mean(durations) if durations else 0,
            "p50_latency": statistics.median(durations) if durations else 0,
            "p95_latency": self._percentile(durations, 95) if durations else 0,
            "p99_latency": self._percentile(durations, 99) if durations else 0,
            "total_input_tokens": sum(e.input_tokens for e in events),
            "total_output_tokens": sum(e.output_tokens for e in events),
        }

    def get_all_tool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tools"""
        return {name: self.get_tool_stats(name) for name in self._by_tool}

    def get_top_errors(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most common errors"""
        return sorted(self._error_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    def get_slowest_tools(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Get tools with highest average latency"""
        stats = self.get_all_tool_stats()
        return sorted(
            [(name, s["avg_latency"]) for name, s in stats.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[-1]
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


class CostAnalytics:
    """
    Analytics for cost tracking.
    """

    def __init__(self):
        self._daily_costs: Dict[str, float] = defaultdict(float)
        self._by_provider: Dict[str, float] = defaultdict(float)
        self._by_model: Dict[str, float] = defaultdict(float)

    def record_cost(
            self, cost: float, provider: str, model: str, timestamp: Optional[datetime] = None
    ):
        """Record cost event"""
        ts = timestamp or datetime.now()
        date_key = ts.strftime("%Y-%m-%d")

        self._daily_costs[date_key] += cost
        self._by_provider[provider] += cost
        self._by_model[model] += cost

    def get_total_cost(self) -> float:
        """Get total cost across all time"""
        return sum(self._daily_costs.values())

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get cost breakdown by provider"""
        return dict(self._by_provider)

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model"""
        return dict(self._by_model)

    def get_cost_trend(self, days: int = 7) -> List[Tuple[str, float]]:
        """Get cost trend over recent days"""
        today = datetime.now()
        result = []

        for i in range(days - 1, -1, -1):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            result.append((date, self._daily_costs.get(date, 0)))

        return result


class ExecutionAnalytics:
    """
    Main analytics aggregator.

    Combines tool, reasoning, and cost analytics
    with comprehensive reporting.
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        """
        Initialize analytics system.

        Args:
            persistence_path: Optional path for persisting analytics
        """
        self.tool_analytics = ToolAnalytics()
        self.cost_analytics = CostAnalytics()

        self._conversations: Dict[str, ConversationEvent] = {}
        self._persistence_path = persistence_path
        self._start_time = datetime.now()

    def record_tool_execution(
            self,
            tool_name: str,
            duration: float,
            success: bool,
            error_type: Optional[str] = None,
            error_message: Optional[str] = None,
            input_tokens: int = 0,
            output_tokens: int = 0,
            file_path: Optional[str] = None,
            task_context: Optional[str] = None,
    ):
        """Record a tool execution"""
        event = ToolExecutionEvent(
            tool_name=tool_name,
            timestamp=datetime.now(),
            duration=duration,
            success=success,
            error_type=error_type,
            error_message=error_message,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            file_path=file_path,
            task_context=task_context,
        )
        self.tool_analytics.record(event)

    def record_cost(self, cost: float, provider: str, model: str):
        """Record cost"""
        self.cost_analytics.record_cost(cost, provider, model)

    def start_conversation(self, conversation_id: str):
        """Start tracking a conversation"""
        self._conversations[conversation_id] = ConversationEvent(
            conversation_id=conversation_id, start_time=datetime.now()
        )

    def end_conversation(
            self,
            conversation_id: str,
            success: bool = True,
            total_tokens: int = 0,
            total_cost: float = 0.0,
    ):
        """End a conversation"""
        if conversation_id in self._conversations:
            conv = self._conversations[conversation_id]
            conv.end_time = datetime.now()
            conv.success = success
            conv.total_tokens = total_tokens
            conv.total_cost = total_cost

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary"""
        uptime = (datetime.now() - self._start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_duration(uptime),
            "tool_stats": self.tool_analytics.get_all_tool_stats(),
            "top_errors": self.tool_analytics.get_top_errors(5),
            "slowest_tools": self.tool_analytics.get_slowest_tools(5),
            "total_cost": self.cost_analytics.get_total_cost(),
            "cost_by_provider": self.cost_analytics.get_cost_by_provider(),
            "cost_trend": self.cost_analytics.get_cost_trend(7),
            "active_conversations": len(
                [c for c in self._conversations.values() if c.end_time is None]
            ),
            "total_conversations": len(self._conversations),
        }

    def get_health_report(self) -> Dict[str, Any]:
        """Get system health report"""
        tool_stats = self.tool_analytics.get_all_tool_stats()

        # Calculate overall success rate
        total_calls = sum(s.get("total_calls", 0) for s in tool_stats.values())
        total_success = sum(
            s.get("total_calls", 0) * s.get("success_rate", 0) for s in tool_stats.values()
        )
        overall_success_rate = total_success / total_calls if total_calls else 1.0

        # Identify issues
        issues = []

        if overall_success_rate < 0.9:
            issues.append(
                {
                    "severity": "high",
                    "message": f"Overall success rate is {overall_success_rate:.1%}",
                    "recommendation": "Review error logs and tool configurations",
                }
            )

        slow_tools = self.tool_analytics.get_slowest_tools(3)
        for tool, latency in slow_tools:
            if latency > 5.0:
                issues.append(
                    {
                        "severity": "medium",
                        "message": f"Tool {tool} has high latency ({latency:.2f}s)",
                        "recommendation": f"Consider optimizing or caching {tool} results",
                    }
                )

        top_errors = self.tool_analytics.get_top_errors(3)
        for error_type, count in top_errors:
            if count > 10:
                issues.append(
                    {
                        "severity": "medium",
                        "message": f"Frequent error: {error_type} ({count} occurrences)",
                        "recommendation": "Investigate root cause of this error",
                    }
                )

        return {
            "status": "healthy" if not issues else "degraded",
            "overall_success_rate": overall_success_rate,
            "issues": issues,
            "recommendations": [i["recommendation"] for i in issues],
        }

    def get_performance_insights(self) -> List[Dict[str, Any]]:
        """Get actionable performance insights"""
        insights = []

        tool_stats = self.tool_analytics.get_all_tool_stats()

        # Identify optimization opportunities
        for tool_name, stats in tool_stats.items():
            if stats.get("total_calls", 0) > 20:
                p95 = stats.get("p95_latency", 0)
                avg = stats.get("avg_latency", 0)

                if p95 > avg * 3:
                    insights.append(
                        {
                            "type": "latency_variance",
                            "tool": tool_name,
                            "insight": f"{tool_name} has high latency variance (p95={p95:.2f}s vs avg={avg:.2f}s)",
                            "suggestion": "Check for intermittent issues or add caching",
                        }
                    )

                success_rate = stats.get("success_rate", 1)
                if success_rate < 0.95:
                    insights.append(
                        {
                            "type": "reliability",
                            "tool": tool_name,
                            "insight": f"{tool_name} has {success_rate:.1%} success rate",
                            "suggestion": "Review error patterns and add better error handling",
                        }
                    )

        # Cost insights
        cost_by_model = self.cost_analytics.get_cost_by_model()
        if cost_by_model:
            most_expensive = max(cost_by_model.items(), key=lambda x: x[1])
            total_cost = sum(cost_by_model.values())
            if most_expensive[1] > total_cost * 0.8:
                insights.append(
                    {
                        "type": "cost",
                        "insight": f"{most_expensive[0]} accounts for {most_expensive[1] / total_cost:.1%} of costs",
                        "suggestion": "Consider using a cheaper model for simpler tasks",
                    }
                )

        return insights

    def export_report(self, format: str = "json") -> str:
        """Export analytics report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "health": self.get_health_report(),
            "insights": self.get_performance_insights(),
        }

        if format == "json":
            return json.dumps(report, indent=2, default=str)
        elif format == "markdown":
            return self._format_markdown_report(report)
        else:
            return str(report)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        elif seconds < 86400:
            return f"{seconds / 3600:.1f}h"
        else:
            return f"{seconds / 86400:.1f}d"

    def _format_markdown_report(self, report: Dict[str, Any]) -> str:
        """Format report as markdown"""
        md = "# HCode Analytics Report\n\n"
        md += f"Generated: {report['generated_at']}\n\n"

        md += "## Summary\n\n"
        summary = report["summary"]
        md += f"- **Uptime**: {summary['uptime_formatted']}\n"
        md += f"- **Total Conversations**: {summary['total_conversations']}\n"
        md += f"- **Total Cost**: ${summary['total_cost']:.4f}\n\n"

        md += "## Health Status\n\n"
        health = report["health"]
        md += f"**Status**: {health['status'].upper()}\n"
        md += f"- Success Rate: {health['overall_success_rate']:.1%}\n\n"

        if health["issues"]:
            md += "### Issues\n\n"
            for issue in health["issues"]:
                md += f"- [{issue['severity'].upper()}] {issue['message']}\n"
            md += "\n"

        md += "## Performance Insights\n\n"
        for insight in report["insights"]:
            md += f"- **{insight['type']}**: {insight['insight']}\n"
            md += f"  - Suggestion: {insight['suggestion']}\n"

        return md

    def save(self):
        """Save analytics to persistence path"""
        if not self._persistence_path:
            return

        try:
            report = self.export_report("json")
            self._persistence_path.write_text(report)
        except Exception as e:
            logger.error(f"[analytics] failed to save analytics to {self._persistence_path}: {e}")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_analytics: Optional[ExecutionAnalytics] = None


def get_analytics(persistence_path: Optional[Path] = None) -> ExecutionAnalytics:
    """Get or create global analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = ExecutionAnalytics(persistence_path)
    return _analytics


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "MetricType",
    "TimeWindow",
    "ToolExecutionEvent",
    "ConversationEvent",
    "TimeSeriesBuffer",
    "ToolAnalytics",
    "CostAnalytics",
    "ExecutionAnalytics",
    "get_analytics",
]
