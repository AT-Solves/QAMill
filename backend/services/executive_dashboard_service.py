"""
Executive Dashboard Service
High-level QA metrics, team trending, KPI tracking, and risk assessment
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class MetricType(Enum):
    """Types of metrics"""
    MUTATION_SCORE = "mutation_score"
    COVERAGE = "coverage"
    TEST_COUNT = "test_count"
    DEFECT_ESCAPE = "defect_escape"
    AUTOMATION_RATE = "automation_rate"
    QUALITY_TREND = "quality_trend"


class RiskCategory(Enum):
    """Risk categories"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class KPI:
    """Key Performance Indicator"""
    name: str
    metric_type: MetricType
    current_value: float
    target_value: float
    threshold_warning: float
    threshold_critical: float
    unit: str = "%"
    trend: str = "stable"  # up, down, stable
    trend_percentage: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TeamMetric:
    """Team-level metric"""
    team_name: str
    member_count: int
    avg_mutation_score: float
    avg_coverage: float
    test_quality_score: float
    velocity: float  # tests per day
    recent_defects: int
    automation_coverage: float


@dataclass
class RiskItem:
    """Risk assessment item"""
    id: str
    description: str
    category: RiskCategory
    impact_score: float  # 0-1
    probability_score: float  # 0-1
    mitigation_plan: Optional[str] = None
    owner: Optional[str] = None
    status: str = "open"  # open, mitigated, closed


@dataclass
class QualityTrend:
    """Quality trend over time"""
    date: datetime
    mutation_score: float
    coverage_score: float
    test_count: int
    defect_escape_rate: float
    team_velocity: float


class ExecutiveDashboardService:
    """Service for executive-level QA governance dashboards"""

    def __init__(self):
        self.kpis: Dict[str, KPI] = {}
        self.teams: Dict[str, TeamMetric] = {}
        self.risks: Dict[str, RiskItem] = {}
        self.trends: List[QualityTrend] = []

    def initialize_default_kpis(self) -> None:
        """Initialize default KPIs"""

        self.kpis["mutation_score"] = KPI(
            name="Overall Mutation Score",
            metric_type=MetricType.MUTATION_SCORE,
            current_value=87.0,
            target_value=90.0,
            threshold_warning=75.0,
            threshold_critical=60.0,
            unit="%",
            trend="up",
            trend_percentage=2.5
        )

        self.kpis["coverage"] = KPI(
            name="Code Coverage",
            metric_type=MetricType.COVERAGE,
            current_value=92.0,
            target_value=95.0,
            threshold_warning=80.0,
            threshold_critical=70.0,
            unit="%",
            trend="up",
            trend_percentage=1.8
        )

        self.kpis["test_count"] = KPI(
            name="Total Tests",
            metric_type=MetricType.TEST_COUNT,
            current_value=1250.0,
            target_value=1500.0,
            threshold_warning=800.0,
            threshold_critical=500.0,
            unit="tests",
            trend="up",
            trend_percentage=5.2
        )

        self.kpis["defect_escape"] = KPI(
            name="Defect Escape Rate",
            metric_type=MetricType.DEFECT_ESCAPE,
            current_value=2.3,
            target_value=1.0,
            threshold_warning=3.0,
            threshold_critical=5.0,
            unit="%",
            trend="down",
            trend_percentage=-0.8
        )

        self.kpis["automation_rate"] = KPI(
            name="Test Automation Rate",
            metric_type=MetricType.AUTOMATION_RATE,
            current_value=78.0,
            target_value=85.0,
            threshold_warning=60.0,
            threshold_critical=40.0,
            unit="%",
            trend="up",
            trend_percentage=3.2
        )

    def add_team(self, team: TeamMetric) -> None:
        """Add team metric"""
        self.teams[team.team_name] = team

    def update_kpi(
        self,
        kpi_name: str,
        current_value: float,
        trend: str = "stable",
        trend_percentage: float = 0.0
    ) -> None:
        """Update KPI value"""

        if kpi_name in self.kpis:
            self.kpis[kpi_name].current_value = current_value
            self.kpis[kpi_name].trend = trend
            self.kpis[kpi_name].trend_percentage = trend_percentage
            self.kpis[kpi_name].last_updated = datetime.now()

    def add_risk(self, risk: RiskItem) -> str:
        """Add risk item"""
        self.risks[risk.id] = risk
        return risk.id

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get executive dashboard summary"""

        # Calculate overall health
        overall_score = self._calculate_overall_health()

        # Get key metrics
        key_metrics = {
            "mutation_score": self.kpis.get("mutation_score").current_value if "mutation_score" in self.kpis else 0,
            "coverage": self.kpis.get("coverage").current_value if "coverage" in self.kpis else 0,
            "test_count": self.kpis.get("test_count").current_value if "test_count" in self.kpis else 0,
            "defect_escape_rate": self.kpis.get("defect_escape").current_value if "defect_escape" in self.kpis else 0,
            "automation_rate": self.kpis.get("automation_rate").current_value if "automation_rate" in self.kpis else 0
        }

        # Risk summary
        critical_risks = sum(1 for r in self.risks.values() if r.category == RiskCategory.CRITICAL)
        high_risks = sum(1 for r in self.risks.values() if r.category == RiskCategory.HIGH)

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": overall_score,
            "health_status": self._get_health_status(overall_score),
            "key_metrics": key_metrics,
            "trend": self._get_trend_direction(),
            "risks": {
                "critical": critical_risks,
                "high": high_risks,
                "total": len(self.risks)
            },
            "teams": {
                name: {
                    "avg_mutation_score": team.avg_mutation_score,
                    "avg_coverage": team.avg_coverage,
                    "quality_score": team.test_quality_score,
                    "velocity": team.velocity
                }
                for name, team in self.teams.items()
            }
        }

    def get_kpi_dashboard(self) -> Dict[str, Any]:
        """Get detailed KPI dashboard"""

        kpi_data = {}

        for kpi_name, kpi in self.kpis.items():
            status = self._calculate_kpi_status(kpi)

            kpi_data[kpi_name] = {
                "name": kpi.name,
                "current_value": kpi.current_value,
                "target_value": kpi.target_value,
                "unit": kpi.unit,
                "status": status,
                "trend": kpi.trend,
                "trend_percentage": kpi.trend_percentage,
                "progress_percentage": (kpi.current_value / kpi.target_value * 100) if kpi.target_value > 0 else 0,
                "last_updated": kpi.last_updated.isoformat()
            }

        return kpi_data

    def get_team_dashboard(self) -> Dict[str, Any]:
        """Get team performance dashboard"""

        team_data = {}

        for team_name, team in self.teams.items():
            team_data[team_name] = {
                "members": team.member_count,
                "mutation_score": team.avg_mutation_score,
                "coverage": team.avg_coverage,
                "quality_score": team.test_quality_score,
                "velocity": team.velocity,
                "defects": team.recent_defects,
                "automation_coverage": team.automation_coverage,
                "health_status": self._get_team_health(team)
            }

        return team_data

    def get_risk_dashboard(self) -> Dict[str, Any]:
        """Get risk assessment dashboard"""

        risks_by_category = {}

        for category in RiskCategory:
            risks_by_category[category.value] = [
                {
                    "id": r.id,
                    "description": r.description,
                    "impact": r.impact_score,
                    "probability": r.probability_score,
                    "risk_score": r.impact_score * r.probability_score,
                    "owner": r.owner,
                    "status": r.status
                }
                for r in self.risks.values()
                if r.category == category
            ]

        return {
            "total_risks": len(self.risks),
            "risks_by_category": risks_by_category,
            "top_risks": sorted(
                [
                    {
                        "id": r.id,
                        "description": r.description,
                        "risk_score": r.impact_score * r.probability_score
                    }
                    for r in self.risks.values()
                ],
                key=lambda x: x["risk_score"],
                reverse=True
            )[:5]
        }

    def get_trend_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Get quality trend analysis"""

        filtered_trends = [
            t for t in self.trends
            if datetime.now() - t.date <= timedelta(days=days)
        ]

        if not filtered_trends:
            return {"error": "No trend data available"}

        # Calculate trend metrics
        first_value = filtered_trends[0].mutation_score if filtered_trends else 0
        last_value = filtered_trends[-1].mutation_score if filtered_trends else 0
        change = last_value - first_value

        return {
            "period_days": days,
            "data_points": len(filtered_trends),
            "mutation_score_trend": {
                "start": first_value,
                "end": last_value,
                "change": change,
                "change_percentage": (change / first_value * 100) if first_value > 0 else 0,
                "data": [
                    {"date": t.date.isoformat(), "value": t.mutation_score}
                    for t in filtered_trends
                ]
            },
            "coverage_trend": {
                "data": [
                    {"date": t.date.isoformat(), "value": t.coverage_score}
                    for t in filtered_trends
                ]
            },
            "team_velocity_trend": {
                "data": [
                    {"date": t.date.isoformat(), "velocity": t.team_velocity}
                    for t in filtered_trends
                ]
            }
        }

    def generate_executive_summary(self) -> str:
        """Generate text executive summary"""

        summary = self.get_dashboard_summary()
        metrics = self.get_kpi_dashboard()

        report = f"""
QAMill Executive Summary Report
Generated: {summary['timestamp']}

OVERALL HEALTH: {summary['health_status'].upper()}
Overall Quality Score: {summary['overall_health']:.1f}%

KEY METRICS:
- Mutation Score: {summary['key_metrics']['mutation_score']:.1f}%
- Code Coverage: {summary['key_metrics']['coverage']:.1f}%
- Total Tests: {int(summary['key_metrics']['test_count'])}
- Defect Escape Rate: {summary['key_metrics']['defect_escape_rate']:.2f}%
- Automation Rate: {summary['key_metrics']['automation_rate']:.1f}%

RISK SUMMARY:
- Critical Risks: {summary['risks']['critical']}
- High Risks: {summary['risks']['high']}
- Total Open Risks: {summary['risks']['total']}

TEAM PERFORMANCE:
"""

        for team_name, team_metrics in summary['teams'].items():
            report += f"\n{team_name}:\n"
            report += f"  - Mutation Score: {team_metrics['avg_mutation_score']:.1f}%\n"
            report += f"  - Coverage: {team_metrics['avg_coverage']:.1f}%\n"
            report += f"  - Quality: {team_metrics['quality_score']:.1f}%\n"
            report += f"  - Velocity: {team_metrics['velocity']:.1f} tests/day\n"

        return report

    def _calculate_overall_health(self) -> float:
        """Calculate overall health score"""

        if not self.kpis:
            return 0.0

        total = 0.0
        weights = {
            "mutation_score": 0.35,
            "coverage": 0.30,
            "automation_rate": 0.20,
            "defect_escape": 0.15
        }

        for kpi_name, weight in weights.items():
            if kpi_name in self.kpis:
                kpi = self.kpis[kpi_name]

                if kpi_name == "defect_escape":
                    # Lower is better for defect escape
                    score = max(0, 100 - kpi.current_value)
                else:
                    score = min(100, kpi.current_value)

                total += score * weight

        return total

    def _get_health_status(self, score: float) -> str:
        """Get health status label"""

        if score >= 85:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        else:
            return "poor"

    def _calculate_kpi_status(self, kpi: KPI) -> str:
        """Calculate KPI status"""

        if kpi.current_value >= kpi.target_value:
            return "on_target"
        elif kpi.current_value >= kpi.threshold_warning:
            return "warning"
        elif kpi.current_value >= kpi.threshold_critical:
            return "critical"
        else:
            return "critical"

    def _get_trend_direction(self) -> str:
        """Get overall trend direction"""

        if not self.kpis:
            return "stable"

        trends = [kpi.trend for kpi in self.kpis.values()]
        ups = sum(1 for t in trends if t == "up")
        downs = sum(1 for t in trends if t == "down")

        if ups > downs:
            return "improving"
        elif downs > ups:
            return "declining"
        else:
            return "stable"

    def _get_team_health(self, team: TeamMetric) -> str:
        """Get team health status"""

        health_score = (
            team.avg_mutation_score * 0.4 +
            team.avg_coverage * 0.3 +
            team.test_quality_score * 0.3
        ) / 100

        if health_score >= 0.85:
            return "healthy"
        elif health_score >= 0.70:
            return "fair"
        else:
            return "needs_improvement"
