"""
Compliance Reporting Service
Generates compliance reports, traceability matrices, and regulatory documentation

Capabilities:
- Requirement tracking
- Test-to-requirement mapping
- Traceability matrices
- Compliance scoring
- Audit trail management
- Regulatory reporting (HIPAA, SOC2, ISO, FDA)
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class ComplianceStandard(Enum):
    """Supported compliance standards"""
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    FDA = "fda"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    NIST = "nist"
    CUSTOM = "custom"


class RequirementStatus(Enum):
    """Status of requirement coverage"""
    FULLY_COVERED = "fully_covered"
    PARTIALLY_COVERED = "partially_covered"
    NOT_COVERED = "not_covered"
    UNDER_REVIEW = "under_review"


@dataclass
class Requirement:
    """Represents a compliance requirement"""
    id: str
    title: str
    description: str
    standard: ComplianceStandard
    section: str  # e.g., "AC-2.1"
    priority: str  # critical, high, medium, low
    test_ids: List[str] = field(default_factory=list)
    coverage_percentage: float = 0.0
    status: RequirementStatus = RequirementStatus.NOT_COVERED
    notes: str = ""


@dataclass
class ComplianceMapping:
    """Maps tests to requirements"""
    test_id: str
    requirement_ids: List[str]
    coverage_level: float  # 0-1
    test_effectiveness: float  # 0-1
    last_verified: datetime = field(default_factory=datetime.now)


@dataclass
class ComplianceReport:
    """Generated compliance report"""
    id: str
    standard: ComplianceStandard
    generated_at: datetime
    requirements: List[Requirement]
    traceability_matrix: List[ComplianceMapping]
    overall_compliance_score: float
    covered_requirements: int
    total_requirements: int
    gaps: List[str]
    recommendations: List[str]
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)


class ComplianceService:
    """Service for compliance reporting and traceability"""

    def __init__(self):
        self.requirements: Dict[str, Requirement] = {}
        self.mappings: List[ComplianceMapping] = []
        self.audit_log: List[Dict[str, Any]] = []

    async def create_requirements(
        self,
        standard: ComplianceStandard,
        requirements_data: List[Dict[str, Any]]
    ) -> List[Requirement]:
        """Create requirements for a compliance standard"""

        requirements = []

        for req_data in requirements_data:
            requirement = Requirement(
                id=f"req_{len(self.requirements):04d}",
                title=req_data.get('title', ''),
                description=req_data.get('description', ''),
                standard=standard,
                section=req_data.get('section', ''),
                priority=req_data.get('priority', 'medium'),
                test_ids=[]
            )

            self.requirements[requirement.id] = requirement
            requirements.append(requirement)

            # Log action
            self._log_action(
                "requirement_created",
                {'requirement_id': requirement.id, 'standard': standard.value}
            )

        return requirements

    async def map_tests_to_requirements(
        self,
        test_ids: List[str],
        requirement_ids: List[str],
        test_effectiveness: float = 0.8
    ) -> List[ComplianceMapping]:
        """Map tests to requirements for traceability"""

        mappings = []

        for test_id in test_ids:
            for req_id in requirement_ids:
                if req_id in self.requirements:
                    mapping = ComplianceMapping(
                        test_id=test_id,
                        requirement_ids=[req_id],
                        coverage_level=test_effectiveness,
                        test_effectiveness=test_effectiveness
                    )

                    self.mappings.append(mapping)
                    mappings.append(mapping)

                    # Update requirement
                    req = self.requirements[req_id]
                    if test_id not in req.test_ids:
                        req.test_ids.append(test_id)

                    # Log action
                    self._log_action(
                        "test_mapped",
                        {
                            'test_id': test_id,
                            'requirement_id': req_id,
                            'effectiveness': test_effectiveness
                        }
                    )

        return mappings

    async def generate_traceability_matrix(
        self,
        standard: ComplianceStandard
    ) -> Dict[str, Any]:
        """Generate traceability matrix for standard"""

        requirements = [r for r in self.requirements.values() if r.standard == standard]

        matrix_data = []

        for req in requirements:
            row = {
                'requirement_id': req.id,
                'section': req.section,
                'title': req.title,
                'priority': req.priority,
                'tests': req.test_ids,
                'test_count': len(req.test_ids),
                'coverage': len(req.test_ids) > 0,
                'status': self._calculate_requirement_status(req)
            }
            matrix_data.append(row)

        return {
            'standard': standard.value,
            'generated_at': datetime.now().isoformat(),
            'total_requirements': len(requirements),
            'covered_requirements': sum(1 for r in requirements if len(r.test_ids) > 0),
            'coverage_percentage': (
                sum(1 for r in requirements if len(r.test_ids) > 0) / len(requirements) * 100
                if requirements else 0
            ),
            'matrix': matrix_data
        }

    async def calculate_compliance_score(
        self,
        standard: ComplianceStandard,
        test_results: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate compliance score for standard"""

        requirements = [r for r in self.requirements.values() if r.standard == standard]

        if not requirements:
            return 0.0, {}

        # Calculate coverage
        covered_count = sum(1 for r in requirements if len(r.test_ids) > 0)
        coverage_score = (covered_count / len(requirements)) * 100

        # Calculate test effectiveness
        total_effectiveness = 0.0
        effectiveness_count = 0

        for mapping in self.mappings:
            if any(rid in [r.id for r in requirements] for rid in mapping.requirement_ids):
                total_effectiveness += mapping.test_effectiveness
                effectiveness_count += 1

        avg_effectiveness = (total_effectiveness / effectiveness_count * 100) if effectiveness_count > 0 else 0

        # Weighted score
        compliance_score = (coverage_score * 0.6 + avg_effectiveness * 0.4) / 100

        # Identify gaps
        gaps = [
            f"Requirement {r.id} ({r.title}) is not covered by tests"
            for r in requirements
            if len(r.test_ids) == 0
        ]

        # Generate recommendations
        recommendations = self._generate_compliance_recommendations(
            requirements,
            coverage_score,
            avg_effectiveness
        )

        result = {
            'compliance_score': compliance_score,
            'coverage_percentage': coverage_score,
            'test_effectiveness': avg_effectiveness,
            'covered_requirements': covered_count,
            'total_requirements': len(requirements),
            'gaps': gaps,
            'recommendations': recommendations
        }

        return compliance_score, result

    async def generate_compliance_report(
        self,
        standard: ComplianceStandard,
        test_results: Dict[str, Any] = None,
        include_audit_trail: bool = True
    ) -> ComplianceReport:
        """Generate comprehensive compliance report"""

        # Get requirements for standard
        requirements = [r for r in self.requirements.values() if r.standard == standard]

        # Calculate traceability matrix
        matrix = await self.generate_traceability_matrix(standard)

        # Calculate compliance score
        score, details = await self.calculate_compliance_score(standard, test_results or {})

        # Create mappings for report
        report_mappings = [
            m for m in self.mappings
            if any(rid in [r.id for r in requirements] for rid in m.requirement_ids)
        ]

        # Create report
        report = ComplianceReport(
            id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            standard=standard,
            generated_at=datetime.now(),
            requirements=requirements,
            traceability_matrix=report_mappings,
            overall_compliance_score=score,
            covered_requirements=details.get('covered_requirements', 0),
            total_requirements=details.get('total_requirements', 0),
            gaps=details.get('gaps', []),
            recommendations=details.get('recommendations', []),
            audit_trail=self.audit_log if include_audit_trail else []
        )

        # Log report generation
        self._log_action(
            "report_generated",
            {'report_id': report.id, 'standard': standard.value, 'score': score}
        )

        return report

    async def export_compliance_report(
        self,
        report: ComplianceReport,
        format: str = "json"
    ) -> str:
        """Export compliance report in various formats"""

        if format == "json":
            return self._export_json(report)
        elif format == "html":
            return self._export_html(report)
        elif format == "markdown":
            return self._export_markdown(report)
        elif format == "csv":
            return self._export_csv(report)
        else:
            return str(report)

    def _export_json(self, report: ComplianceReport) -> str:
        """Export as JSON"""

        data = {
            'id': report.id,
            'standard': report.standard.value,
            'generated_at': report.generated_at.isoformat(),
            'compliance_score': report.overall_compliance_score,
            'coverage': {
                'covered': report.covered_requirements,
                'total': report.total_requirements,
                'percentage': (report.covered_requirements / report.total_requirements * 100) if report.total_requirements > 0 else 0
            },
            'requirements': [
                {
                    'id': r.id,
                    'section': r.section,
                    'title': r.title,
                    'priority': r.priority,
                    'tests': r.test_ids,
                    'status': r.status.value
                }
                for r in report.requirements
            ],
            'gaps': report.gaps,
            'recommendations': report.recommendations
        }

        return json.dumps(data, indent=2)

    def _export_html(self, report: ComplianceReport) -> str:
        """Export as HTML"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report - {report.standard.value.upper()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .score {{ font-size: 24px; color: #{"green" if report.overall_compliance_score >= 0.8 else "orange" if report.overall_compliance_score >= 0.6 else "red"}; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .critical {{ background-color: #ffcccc; }}
        .high {{ background-color: #ffe6cc; }}
    </style>
</head>
<body>
    <h1>Compliance Report</h1>
    <p>Standard: {report.standard.value.upper()}</p>
    <p>Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="score">
        Compliance Score: {report.overall_compliance_score:.1%}
    </div>

    <p>Coverage: {report.covered_requirements} of {report.total_requirements} requirements covered</p>

    <h2>Requirements</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Section</th>
            <th>Title</th>
            <th>Priority</th>
            <th>Tests</th>
            <th>Status</th>
        </tr>
"""

        for req in report.requirements:
            priority_class = f"class='{req.priority}'" if req.priority in ['critical', 'high'] else ""
            status = "✓" if len(req.test_ids) > 0 else "✗"
            html += f"""
        <tr {priority_class}>
            <td>{req.id}</td>
            <td>{req.section}</td>
            <td>{req.title}</td>
            <td>{req.priority}</td>
            <td>{len(req.test_ids)}</td>
            <td>{status}</td>
        </tr>
"""

        html += """
    </table>

    <h2>Gaps</h2>
    <ul>
"""

        for gap in report.gaps:
            html += f"        <li>{gap}</li>\n"

        html += """
    </ul>

    <h2>Recommendations</h2>
    <ul>
"""

        for rec in report.recommendations:
            html += f"        <li>{rec}</li>\n"

        html += """
    </ul>
</body>
</html>
"""

        return html

    def _export_markdown(self, report: ComplianceReport) -> str:
        """Export as Markdown"""

        md = f"# Compliance Report - {report.standard.value.upper()}\n\n"
        md += f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += f"**Compliance Score:** {report.overall_compliance_score:.1%}\n\n"
        md += f"**Coverage:** {report.covered_requirements}/{report.total_requirements} requirements covered\n\n"

        md += "## Requirements Traceability Matrix\n\n"
        md += "| ID | Section | Title | Priority | Tests | Status |\n"
        md += "|--|--|--|--|--|--|\n"

        for req in report.requirements:
            status = "✓" if len(req.test_ids) > 0 else "✗"
            md += f"| {req.id} | {req.section} | {req.title} | {req.priority} | {len(req.test_ids)} | {status} |\n"

        if report.gaps:
            md += "\n## Coverage Gaps\n\n"
            for gap in report.gaps:
                md += f"- {gap}\n"

        if report.recommendations:
            md += "\n## Recommendations\n\n"
            for rec in report.recommendations:
                md += f"- {rec}\n"

        return md

    def _export_csv(self, report: ComplianceReport) -> str:
        """Export as CSV"""

        csv = "ID,Section,Title,Priority,Tests,Status\n"

        for req in report.requirements:
            status = "Covered" if len(req.test_ids) > 0 else "Not Covered"
            csv += f'"{req.id}","{req.section}","{req.title}","{req.priority}","{len(req.test_ids)}","{status}"\n'

        return csv

    def _calculate_requirement_status(self, requirement: Requirement) -> str:
        """Calculate status of a requirement"""

        if len(requirement.test_ids) == 0:
            return RequirementStatus.NOT_COVERED.value
        elif len(requirement.test_ids) == 1:
            return RequirementStatus.PARTIALLY_COVERED.value
        else:
            return RequirementStatus.FULLY_COVERED.value

    def _generate_compliance_recommendations(
        self,
        requirements: List[Requirement],
        coverage_score: float,
        effectiveness_score: float
    ) -> List[str]:
        """Generate recommendations based on compliance analysis"""

        recommendations = []

        # Coverage recommendations
        if coverage_score < 100:
            uncovered_count = sum(1 for r in requirements if len(r.test_ids) == 0)
            recommendations.append(
                f"Add tests for {uncovered_count} uncovered requirement(s) to achieve 100% coverage"
            )

        # Effectiveness recommendations
        if effectiveness_score < 80:
            recommendations.append(
                "Improve test effectiveness; consider adding more edge case and error handling tests"
            )

        # Priority-based recommendations
        critical_uncovered = sum(1 for r in requirements if r.priority == 'critical' and len(r.test_ids) == 0)
        if critical_uncovered > 0:
            recommendations.append(
                f"URGENT: {critical_uncovered} critical requirement(s) are not covered by tests"
            )

        if len(recommendations) == 0:
            recommendations.append("Maintain current compliance posture with regular testing")

        return recommendations

    def _log_action(self, action: str, details: Dict[str, Any]) -> None:
        """Log action to audit trail"""

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }

        self.audit_log.append(log_entry)

    async def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail of all compliance actions"""

        return self.audit_log[-limit:]
