"""
Report Service - Elite HTML/PDF report generation
"""
from typing import Optional
from sqlalchemy.orm import Session
from models.database import Report, Analysis
from datetime import datetime
import json


class ReportService:
    """Service for generating and managing reports"""

    def __init__(self, db: Session, storage_service=None):
        self.db = db
        self.storage = storage_service

    async def generate_report(
        self,
        analysis_id: str,
        format: str = "html",
        project_id: str = None,
    ) -> Optional[Report]:
        """Generate report from analysis"""
        analysis = (
            self.db.query(Analysis)
            .filter(Analysis.id == analysis_id)
            .first()
        )

        if not analysis:
            return None

        # Generate report content based on format
        if format == "html":
            content = self._generate_html_report(analysis)
        elif format == "pdf":
            content = self._generate_pdf_report(analysis)
        elif format == "json":
            content = self._generate_json_report(analysis)
        else:
            return None

        # Create report record
        report = Report(
            project_id=project_id or analysis.project_id,
            analysis_id=analysis_id,
            name=f"Analysis Report - {analysis.file_path}",
            description=f"Mutation testing analysis for {analysis.file_path}",
            report_type=format,
            is_public=False,
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        return report

    def _generate_html_report(self, analysis: Analysis) -> str:
        """Generate elite HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>QAMill Analysis Report</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    background: #f8f9fa;
                    color: #2c3e50;
                    line-height: 1.6;
                }}

                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 40px 20px;
                }}

                header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 0;
                    margin-bottom: 40px;
                    border-radius: 8px;
                }}

                h1 {{
                    font-size: 32px;
                    margin-bottom: 10px;
                }}

                .subtitle {{
                    opacity: 0.9;
                    font-size: 16px;
                }}

                .metrics {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 40px 0;
                }}

                .metric-card {{
                    background: white;
                    padding: 25px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    text-align: center;
                }}

                .metric-value {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #667eea;
                    margin: 10px 0;
                }}

                .metric-label {{
                    font-size: 14px;
                    color: #7f8c8d;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}

                .progress-bar {{
                    width: 100%;
                    height: 8px;
                    background: #ecf0f1;
                    border-radius: 4px;
                    overflow: hidden;
                    margin-top: 15px;
                }}

                .progress-fill {{
                    height: 100%;
                    background: linear-gradient(90deg, #667eea, #764ba2);
                    border-radius: 4px;
                }}

                .section {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    margin: 30px 0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}

                .section h2 {{
                    font-size: 24px;
                    margin-bottom: 20px;
                    color: #2c3e50;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}

                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ecf0f1;
                }}

                th {{
                    background: #f8f9fa;
                    font-weight: 600;
                    color: #2c3e50;
                }}

                tr:hover {{
                    background: #f8f9fa;
                }}

                .badge {{
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                }}

                .badge-success {{
                    background: #d4edda;
                    color: #155724;
                }}

                .badge-warning {{
                    background: #fff3cd;
                    color: #856404;
                }}

                .badge-danger {{
                    background: #f8d7da;
                    color: #721c24;
                }}

                footer {{
                    margin-top: 60px;
                    padding-top: 20px;
                    border-top: 1px solid #ecf0f1;
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>QAMill Analysis Report</h1>
                    <p class="subtitle">Mutation Testing Intelligence</p>
                </header>

                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-label">Mutation Score</div>
                        <div class="metric-value">{analysis.mutation_score:.1f}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {analysis.mutation_score}%"></div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <div class="metric-label">Coverage Score</div>
                        <div class="metric-value">{analysis.coverage_score:.1f}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {analysis.coverage_score}%"></div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <div class="metric-label">Quality Score</div>
                        <div class="metric-value">{analysis.quality_score:.1f}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {analysis.quality_score}%"></div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <div class="metric-label">Total Mutations</div>
                        <div class="metric-value">{analysis.mutation_count}</div>
                    </div>
                </div>

                <div class="section">
                    <h2>Mutation Results</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>Count</th>
                                <th>Percentage</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><span class="badge badge-success">Killed</span></td>
                                <td>{analysis.killed_count}</td>
                                <td>{(analysis.killed_count / analysis.mutation_count * 100) if analysis.mutation_count > 0 else 0:.1f}%</td>
                            </tr>
                            <tr>
                                <td><span class="badge badge-warning">Survived</span></td>
                                <td>{analysis.survived_count}</td>
                                <td>{(analysis.survived_count / analysis.mutation_count * 100) if analysis.mutation_count > 0 else 0:.1f}%</td>
                            </tr>
                            <tr>
                                <td><span class="badge badge-danger">Equivalent</span></td>
                                <td>{analysis.equivalent_count}</td>
                                <td>{(analysis.equivalent_count / analysis.mutation_count * 100) if analysis.mutation_count > 0 else 0:.1f}%</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div class="section">
                    <h2>Analysis Details</h2>
                    <table>
                        <tbody>
                            <tr>
                                <td><strong>File:</strong></td>
                                <td>{analysis.file_path}</td>
                            </tr>
                            <tr>
                                <td><strong>Language:</strong></td>
                                <td>{analysis.language}</td>
                            </tr>
                            <tr>
                                <td><strong>Status:</strong></td>
                                <td>{analysis.status}</td>
                            </tr>
                            <tr>
                                <td><strong>Duration:</strong></td>
                                <td>{analysis.duration_seconds} seconds</td>
                            </tr>
                            <tr>
                                <td><strong>LLM Provider:</strong></td>
                                <td>{analysis.llm_provider} ({analysis.llm_model})</td>
                            </tr>
                            <tr>
                                <td><strong>Analysis Date:</strong></td>
                                <td>{analysis.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <footer>
                    <p>Generated by QAMill AI QA Governance Platform</p>
                    <p>© 2026 | All rights reserved</p>
                </footer>
            </div>
        </body>
        </html>
        """
        return html

    def _generate_pdf_report(self, analysis: Analysis) -> str:
        """Generate PDF report (placeholder)"""
        return f"PDF Report for {analysis.file_path}"

    def _generate_json_report(self, analysis: Analysis) -> str:
        """Generate JSON report"""
        return json.dumps(
            {
                "id": analysis.id,
                "project_id": analysis.project_id,
                "file_path": analysis.file_path,
                "language": analysis.language,
                "mutation_count": analysis.mutation_count,
                "killed_count": analysis.killed_count,
                "survived_count": analysis.survived_count,
                "equivalent_count": analysis.equivalent_count,
                "mutation_score": analysis.mutation_score,
                "coverage_score": analysis.coverage_score,
                "quality_score": analysis.quality_score,
                "status": analysis.status,
                "duration_seconds": analysis.duration_seconds,
                "created_at": analysis.created_at.isoformat(),
            },
            indent=2,
        )

    def get_report(self, report_id: str) -> Optional[Report]:
        """Get report by ID"""
        return self.db.query(Report).filter(Report.id == report_id).first()

    def list_reports(
        self,
        project_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list:
        """List reports for a project"""
        return (
            self.db.query(Report)
            .filter(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
