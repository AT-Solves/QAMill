"""
Analysis Service - Core QA Governance Capability
Handles mutation testing analysis workflow
"""
from datetime import datetime
from typing import List, Dict, Optional
from models.database import Analysis, Project
from sqlalchemy.orm import Session
import asyncio


class AnalysisService:
    """Service for managing analysis operations"""

    def __init__(self, db: Session, llm_service, storage_service):
        self.db = db
        self.llm = llm_service
        self.storage = storage_service

    async def start_analysis(
        self,
        project_id: str,
        file_path: str,
        language: str,
        llm_provider: str,
        llm_model: str,
    ) -> Analysis:
        """Start a new analysis"""
        analysis = Analysis(
            project_id=project_id,
            file_path=file_path,
            language=language,
            status="running",
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Start async analysis job
        asyncio.create_task(self._run_analysis(analysis))

        return analysis

    async def _run_analysis(self, analysis: Analysis) -> None:
        """Run mutation testing analysis"""
        try:
            analysis.started_at = datetime.utcnow()

            # Read source file
            source_code = self.storage.read_file(analysis.file_path)

            # Generate mutations based on language
            mutations = self._generate_mutations(
                source_code,
                analysis.language,
            )

            analysis.mutation_count = len(mutations)
            self.db.add(analysis)
            self.db.commit()

            # Run tests against mutations
            killed = 0
            survived = 0
            equivalent = 0

            for mutation in mutations:
                result = await self._test_mutation(
                    analysis.project_id,
                    mutation,
                    analysis.llm_provider,
                    analysis.llm_model,
                )

                if result["status"] == "killed":
                    killed += 1
                elif result["status"] == "survived":
                    survived += 1
                elif result["status"] == "equivalent":
                    equivalent += 1

            # Calculate metrics
            total = len(mutations)
            analysis.killed_count = killed
            analysis.survived_count = survived
            analysis.equivalent_count = equivalent
            analysis.mutation_score = (
                (killed / total * 100) if total > 0 else 0
            )
            analysis.coverage_score = 85.0  # TODO: Calculate from actual coverage
            analysis.quality_score = (
                analysis.mutation_score * 0.6 + analysis.coverage_score * 0.4
            )

            analysis.status = "completed"
            analysis.completed_at = datetime.utcnow()
            duration = (
                analysis.completed_at - analysis.started_at
            ).total_seconds()
            analysis.duration_seconds = int(duration)

            # Store mutations detail
            analysis.mutations_detail = [
                {
                    "id": m["id"],
                    "operator": m["operator"],
                    "description": m["description"],
                    "line": m["line"],
                    "status": m.get("status", "unknown"),
                }
                for m in mutations
            ]

            self.db.add(analysis)
            self.db.commit()

        except Exception as e:
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.completed_at = datetime.utcnow()
            self.db.add(analysis)
            self.db.commit()

    async def _test_mutation(
        self,
        project_id: str,
        mutation: Dict,
        llm_provider: str,
        llm_model: str,
    ) -> Dict:
        """Test a single mutation"""
        # Apply mutation to temporary file
        # Run tests
        # Return kill/survive status
        # For MVP, simulate results
        import random

        return {
            "status": random.choice(
                ["killed", "survived", "equivalent", "error"]
            ),
            "details": {},
        }

    def _generate_mutations(
        self, source_code: str, language: str
    ) -> List[Dict]:
        """Generate mutations based on language"""
        mutations = []

        if language == "python":
            # Use existing Python mutation engine
            from mutation_engine import MutationEngine

            engine = MutationEngine()
            mutants = engine.generate_mutants_from_source(source_code)
            mutations = [
                {
                    "id": m.id,
                    "operator": m.operator,
                    "description": m.description,
                    "line": m.line_no,
                    "original": m.original_src,
                    "mutated": m.mutant_src,
                }
                for m in mutants
            ]

        elif language == "javascript":
            # Use JavaScript mutation engine
            from javascript_mutation_engine_extended import (
                JavaScriptMutationEngineExtended,
            )

            engine = JavaScriptMutationEngineExtended(".")
            # Pass source code directly instead of file path
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".js", delete=False
            ) as f:
                f.write(source_code)
                f.flush()
                mutants = engine.generate_mutants(f.name)

            mutations = [
                {
                    "id": m.id,
                    "operator": m.operator,
                    "description": m.description,
                    "line": m.line_no,
                    "original": m.original_src,
                    "mutated": m.mutant_src,
                }
                for m in mutants
            ]

        return mutations

    def get_analysis(self, analysis_id: str) -> Optional[Analysis]:
        """Get analysis by ID"""
        return self.db.query(Analysis).filter(
            Analysis.id == analysis_id
        ).first()

    def list_analyses(
        self, project_id: str, limit: int = 50, offset: int = 0
    ) -> List[Analysis]:
        """List analyses for a project"""
        return (
            self.db.query(Analysis)
            .filter(Analysis.project_id == project_id)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_project_stats(self, project_id: str) -> Dict:
        """Get aggregate stats for a project"""
        analyses = self.db.query(Analysis).filter(
            Analysis.project_id == project_id,
            Analysis.status == "completed",
        ).all()

        if not analyses:
            return {
                "total_analyses": 0,
                "avg_mutation_score": 0.0,
                "avg_coverage_score": 0.0,
                "avg_quality_score": 0.0,
                "trend": [],
            }

        scores = [a.mutation_score for a in analyses]
        coverage = [a.coverage_score for a in analyses]
        quality = [a.quality_score for a in analyses]

        return {
            "total_analyses": len(analyses),
            "avg_mutation_score": sum(scores) / len(scores),
            "avg_coverage_score": sum(coverage) / len(coverage),
            "avg_quality_score": sum(quality) / len(quality),
            "trend": [
                {
                    "date": a.created_at.isoformat(),
                    "mutation_score": a.mutation_score,
                    "file": a.file_path,
                }
                for a in analyses[-10:]  # Last 10
            ],
        }
