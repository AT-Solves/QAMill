"""
Test Gap Analysis Service
Identifies test gaps and untested code paths

Capabilities:
- Identify code areas with insufficient testing
- Map mutations to specific code sections
- Risk scoring for untested code
- Generate recommendations
- Highlight high-risk areas
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class RiskLevel(Enum):
    """Risk levels for untested code"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


@dataclass
class CodeGap:
    """Represents a test gap in code"""
    id: str
    file_path: str
    line_numbers: List[int]
    function_name: str
    code_snippet: str
    gap_type: str  # untested, under_tested, no_edge_cases, no_error_handling
    risk_level: RiskLevel
    mutations_escaped: List[str]
    count_mutations_escaped: int
    recommendation: str
    impact_score: float  # 0-1, where 1 is most critical


@dataclass
class WeaknessSummary:
    """Summary of test weaknesses"""
    total_gaps: int
    critical_gaps: int
    high_risk_gaps: int
    medium_risk_gaps: int
    total_escaped_mutations: int
    avg_risk_level: float
    estimated_score_improvement: float


class TestGapAnalyzer:
    """Analyzes and identifies test gaps"""

    def __init__(self):
        self.gaps: List[CodeGap] = []

    def analyze_code_gaps(
        self,
        source_code: str,
        survived_mutations: List[Dict[str, Any]],
        test_coverage: Dict[str, Any],
        function_data: Dict[str, Any] = None
    ) -> Tuple[List[CodeGap], WeaknessSummary]:
        """
        Analyze code for test gaps

        Args:
            source_code: Source code being tested
            survived_mutations: Mutations that escaped tests
            test_coverage: Code coverage metrics
            function_data: Function-level metadata

        Returns:
            Tuple of (gaps list, weakness summary)
        """

        self.gaps = []
        lines = source_code.split('\n')

        # Identify untested lines
        uncovered_lines = self._identify_uncovered_lines(test_coverage)

        # Map mutations to code sections
        mutation_map = self._map_mutations_to_code(survived_mutations, lines)

        # Analyze each uncovered section
        for line_num in uncovered_lines:
            gap = self._analyze_line_gap(
                line_num,
                lines,
                mutation_map,
                survived_mutations
            )
            if gap:
                self.gaps.append(gap)

        # Identify under-tested areas (covered but low mutation score)
        undertested = self._identify_undertested_areas(
            survived_mutations,
            test_coverage,
            lines
        )
        self.gaps.extend(undertested)

        # Identify missing error handling
        error_gaps = self._identify_missing_error_handling(source_code, lines)
        self.gaps.extend(error_gaps)

        # Identify boundary value gaps
        boundary_gaps = self._identify_boundary_value_gaps(
            survived_mutations,
            lines
        )
        self.gaps.extend(boundary_gaps)

        # Create summary
        summary = self._create_weakness_summary()

        return self.gaps, summary

    def _identify_uncovered_lines(self, test_coverage: Dict) -> List[int]:
        """Identify lines not covered by tests"""
        uncovered = []

        coverage_data = test_coverage.get('line_coverage', {})

        for line_num, is_covered in coverage_data.items():
            if not is_covered:
                uncovered.append(int(line_num))

        return uncovered

    def _map_mutations_to_code(self, mutations: List[Dict], lines: List[str]) -> Dict[int, List[str]]:
        """Map mutations to code lines"""
        mapping = {}

        for mutation in mutations:
            line_num = mutation.get('line_number', 0)
            if line_num > 0:
                if line_num not in mapping:
                    mapping[line_num] = []
                mapping[line_num].append(mutation.get('description', ''))

        return mapping

    def _analyze_line_gap(
        self,
        line_num: int,
        lines: List[str],
        mutation_map: Dict[int, List[str]],
        mutations: List[Dict]
    ) -> CodeGap:
        """Analyze a single line for gaps"""

        if line_num > len(lines):
            return None

        code_line = lines[line_num - 1].strip()

        # Get mutations on this line
        mutations_on_line = mutation_map.get(line_num, [])

        # Determine gap type
        gap_type = self._determine_gap_type(code_line)

        # Calculate risk level
        risk_level = self._calculate_risk_level(code_line, len(mutations_on_line))

        # Generate recommendation
        recommendation = self._generate_gap_recommendation(gap_type, code_line)

        gap = CodeGap(
            id=f"gap_{line_num:04d}",
            file_path="main.py",  # Could be enhanced
            line_numbers=[line_num],
            function_name=self._find_function_name(lines, line_num),
            code_snippet=code_line,
            gap_type=gap_type,
            risk_level=risk_level,
            mutations_escaped=mutations_on_line,
            count_mutations_escaped=len(mutations_on_line),
            recommendation=recommendation,
            impact_score=self._calculate_impact_score(risk_level, len(mutations_on_line))
        )

        return gap

    def _identify_undertested_areas(
        self,
        mutations: List[Dict],
        coverage: Dict,
        lines: List[str]
    ) -> List[CodeGap]:
        """Identify areas that are covered but have many escaped mutations"""

        gaps = []
        mutation_by_line = {}

        # Group mutations by line
        for mutation in mutations:
            line = mutation.get('line_number', 0)
            if line > 0:
                if line not in mutation_by_line:
                    mutation_by_line[line] = []
                mutation_by_line[line].append(mutation)

        # Find lines with high mutation escape rate
        for line_num, muts in mutation_by_line.items():
            if len(muts) >= 3:  # Multiple mutations escaped on one line
                gap = CodeGap(
                    id=f"under_{line_num:04d}",
                    file_path="main.py",
                    line_numbers=[line_num],
                    function_name=self._find_function_name(lines, line_num),
                    code_snippet=lines[line_num - 1].strip() if line_num <= len(lines) else "",
                    gap_type="under_tested",
                    risk_level=RiskLevel.HIGH,
                    mutations_escaped=[m.get('description', '') for m in muts],
                    count_mutations_escaped=len(muts),
                    recommendation=f"Add comprehensive tests for this line; {len(muts)} mutations escaped",
                    impact_score=0.7
                )
                gaps.append(gap)

        return gaps

    def _identify_missing_error_handling(self, source_code: str, lines: List[str]) -> List[CodeGap]:
        """Identify missing error handling"""

        gaps = []

        # Find lines without try-except or error checks
        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Check for operations that might fail
            if any(op in line for op in ['/', 'open(', 'int(', '[', '.split(', '/']):
                if not self._has_error_handling(lines, line_num):
                    gap = CodeGap(
                        id=f"error_{line_num:04d}",
                        file_path="main.py",
                        line_numbers=[line_num],
                        function_name=self._find_function_name(lines, line_num),
                        code_snippet=line,
                        gap_type="no_error_handling",
                        risk_level=RiskLevel.MEDIUM,
                        mutations_escaped=[],
                        count_mutations_escaped=0,
                        recommendation="Add error handling tests (try-except, null checks, bounds checking)",
                        impact_score=0.6
                    )
                    gaps.append(gap)

        return gaps

    def _identify_boundary_value_gaps(
        self,
        mutations: List[Dict],
        lines: List[str]
    ) -> List[CodeGap]:
        """Identify missing boundary value tests"""

        gaps = []

        # Find relational operators
        for line_num, line in enumerate(lines, 1):
            if any(op in line for op in ['<', '>', '<=', '>=', '==']):
                gap = CodeGap(
                    id=f"boundary_{line_num:04d}",
                    file_path="main.py",
                    line_numbers=[line_num],
                    function_name=self._find_function_name(lines, line_num),
                    code_snippet=line.strip(),
                    gap_type="boundary_values",
                    risk_level=RiskLevel.MEDIUM,
                    mutations_escaped=[],
                    count_mutations_escaped=0,
                    recommendation="Add boundary value tests (test values at, above, and below boundaries)",
                    impact_score=0.5
                )
                gaps.append(gap)

        return gaps

    def _determine_gap_type(self, code_line: str) -> str:
        """Determine type of gap"""

        if len(code_line) == 0:
            return "empty_line"
        elif any(kw in code_line for kw in ['if', 'elif', 'else']):
            return "conditional_logic"
        elif any(kw in code_line for kw in ['for', 'while']):
            return "loop_logic"
        elif '/' in code_line:
            return "division_operation"
        elif any(op in code_line for op in ['<', '>', '<=', '>=']):
            return "comparison_logic"
        else:
            return "general"

    def _calculate_risk_level(self, code_line: str, mutation_count: int) -> RiskLevel:
        """Calculate risk level based on code and mutations"""

        # High-risk patterns
        if any(kw in code_line for kw in ['if', 'else', 'elif']):
            if mutation_count >= 2:
                return RiskLevel.CRITICAL
            return RiskLevel.HIGH

        # Division operations
        if '/' in code_line:
            return RiskLevel.HIGH

        if mutation_count >= 3:
            return RiskLevel.HIGH
        elif mutation_count == 2:
            return RiskLevel.MEDIUM
        elif mutation_count == 1:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL

    def _generate_gap_recommendation(self, gap_type: str, code_line: str) -> str:
        """Generate recommendation for gap"""

        recommendations = {
            "untested": "Add tests for this untested code path",
            "under_tested": "Add more comprehensive tests; multiple mutations escaped",
            "conditional_logic": "Add tests for both true and false branches",
            "loop_logic": "Add tests for loop conditions, boundaries, and edge cases",
            "division_operation": "Add tests for division by zero and boundary values",
            "comparison_logic": "Add boundary value tests (test at and across boundaries)",
            "no_error_handling": "Add error handling tests (null checks, exceptions)",
            "boundary_values": "Add boundary value analysis tests",
            "general": "Add more comprehensive test coverage"
        }

        return recommendations.get(gap_type, "Add more test coverage")

    def _calculate_impact_score(self, risk_level: RiskLevel, mutation_count: int) -> float:
        """Calculate impact score (0-1)"""

        risk_scores = {
            RiskLevel.CRITICAL: 1.0,
            RiskLevel.HIGH: 0.8,
            RiskLevel.MEDIUM: 0.6,
            RiskLevel.LOW: 0.4,
            RiskLevel.MINIMAL: 0.2
        }

        base_score = risk_scores.get(risk_level, 0.5)

        # Increase score based on mutation count
        mutation_bonus = min(mutation_count * 0.1, 0.2)

        return min(base_score + mutation_bonus, 1.0)

    def _find_function_name(self, lines: List[str], target_line: int) -> str:
        """Find function name for a line"""

        for line_num in range(target_line - 1, -1, -1):
            line = lines[line_num].strip()
            if line.startswith('def ') or line.startswith('function '):
                # Extract function name
                if 'def ' in line:
                    return line.split('def ')[1].split('(')[0]
                elif 'function' in line:
                    return line.split('function ')[1].split('(')[0]

        return "unknown_function"

    def _has_error_handling(self, lines: List[str], target_line: int) -> bool:
        """Check if a line has error handling"""

        # Look for try-except in surrounding lines
        for line_num in range(max(0, target_line - 5), min(len(lines), target_line + 5)):
            line = lines[line_num].strip()
            if 'try:' in line or 'except' in line or 'try {' in line or 'catch' in line:
                return True

        return False

    def _create_weakness_summary(self) -> WeaknessSummary:
        """Create summary of test weaknesses"""

        total_gaps = len(self.gaps)
        critical_gaps = sum(1 for g in self.gaps if g.risk_level == RiskLevel.CRITICAL)
        high_risk_gaps = sum(1 for g in self.gaps if g.risk_level == RiskLevel.HIGH)
        medium_risk_gaps = sum(1 for g in self.gaps if g.risk_level == RiskLevel.MEDIUM)
        total_escaped = sum(g.count_mutations_escaped for g in self.gaps)

        # Calculate average risk level
        risk_values = {
            RiskLevel.CRITICAL: 5,
            RiskLevel.HIGH: 4,
            RiskLevel.MEDIUM: 3,
            RiskLevel.LOW: 2,
            RiskLevel.MINIMAL: 1
        }

        avg_risk = (sum(risk_values[g.risk_level] for g in self.gaps) / len(self.gaps) * 20) if self.gaps else 0

        # Estimate score improvement
        estimated_improvement = (total_escaped / (total_escaped + 50)) * 0.2  # Max 20% improvement

        return WeaknessSummary(
            total_gaps=total_gaps,
            critical_gaps=critical_gaps,
            high_risk_gaps=high_risk_gaps,
            medium_risk_gaps=medium_risk_gaps,
            total_escaped_mutations=total_escaped,
            avg_risk_level=min(avg_risk, 100),
            estimated_score_improvement=min(estimated_improvement, 0.2)
        )

    def export_gaps_report(self, format: str = "json") -> str:
        """Export gaps analysis report"""

        if format == "json":
            data = [
                {
                    "id": g.id,
                    "line": g.line_numbers[0] if g.line_numbers else 0,
                    "function": g.function_name,
                    "gap_type": g.gap_type,
                    "risk_level": g.risk_level.value,
                    "mutations_escaped": g.count_mutations_escaped,
                    "recommendation": g.recommendation,
                    "impact": g.impact_score
                }
                for g in sorted(self.gaps, key=lambda x: x.impact_score, reverse=True)
            ]
            return json.dumps(data, indent=2)

        elif format == "markdown":
            report = "# Test Gap Analysis Report\n\n"
            report += f"**Total Gaps:** {len(self.gaps)}\n\n"

            # Group by risk level
            for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
                gaps_at_level = [g for g in self.gaps if g.risk_level == risk_level]

                if gaps_at_level:
                    report += f"## {risk_level.value.upper()} Risk ({len(gaps_at_level)})\n\n"

                    for gap in gaps_at_level[:5]:  # Top 5
                        report += f"- **Line {gap.line_numbers[0]}** in `{gap.function_name}`\n"
                        report += f"  - Type: {gap.gap_type}\n"
                        report += f"  - Mutations Escaped: {gap.count_mutations_escaped}\n"
                        report += f"  - Recommendation: {gap.recommendation}\n\n"

            return report

        return str(self.gaps)
