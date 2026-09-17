import logging
from typing import Dict, List, Any

from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.schemas.job_description import JobDescription

logger = logging.getLogger("app.explainability.explainability_engine")

class ExplainabilityEngine:
    """Generates factual, non-hallucinated justifications for candidate rankings in a recruiter-friendly format."""

    def generate_explanation(self, candidate: CandidateIntelligence, evaluation: Dict[str, Any], jd: JobDescription) -> str:
        """Generates a structured, factual explanation of candidate evaluation results."""
        years = candidate.years_of_experience
        title = candidate.current_title.strip() if candidate.current_title else ""
        company = candidate.current_company.strip() if candidate.current_company else ""
        name = candidate.name.strip() if hasattr(candidate, "name") and candidate.name else f"Candidate {candidate.candidate_id}"
        
        # 1. Candidate background overview
        if title and company:
            overview = f"{name} is currently a {title} at {company} with {years:.1f} years of relevant experience."
        elif title:
            overview = f"{name} brings {years:.1f} years of professional experience, working as a {title}."
        else:
            overview = f"{name} has {years:.1f} years of technical experience in this domain."

        breakdown = evaluation.get("scoring_breakdown", {})
        
        critical_matched = breakdown.get("critical_skills_matched", [])
        important_matched = breakdown.get("important_skills_matched", [])
        nice_to_have_matched = breakdown.get("nice_to_have_skills_matched", [])
        missing_critical = breakdown.get("missing_critical_skills", [])
        
        # Deduplicate matched skills
        all_matched = critical_matched + important_matched + nice_to_have_matched
        clean_matched = []
        seen = set()
        for s in all_matched:
            c_name = s.split(" (via")[0].strip()
            if c_name.lower() not in seen:
                seen.add(c_name.lower())
                clean_matched.append(c_name)

        # 2. Matched Strengths
        if clean_matched:
            strengths_str = f"Strengths: Direct evidence verified for {', '.join(clean_matched[:5])}."
        else:
            strengths_str = "Strengths: General domain background with limited direct skill overlap."

        # 3. Identified Gaps (Find any missing mandatory or preferred skills)
        missing_all = []
        if missing_critical:
            for m in missing_critical:
                c_gap = m.split(" (via")[0].strip()
                if c_gap.lower() not in missing_all:
                    missing_all.append(c_gap)

        # Also check preferred/important skills not matched
        all_jd_reqs = [r.strip() for r in (jd.requirements or [])] + [p.strip() for p in (jd.preferred_skills or []) if p.lower() != "none specified"]
        matched_lower = set(s.lower() for s in clean_matched)
        for req in all_jd_reqs:
            if req.lower() not in matched_lower and req not in missing_all:
                missing_all.append(req)

        if missing_all:
            gaps_str = f"Gaps: Lacks documented skill evidence for {', '.join(missing_all[:4])}."
        else:
            gaps_str = "Gaps: Complete skill requirement coverage confirmed."

        # 4. Behavioral & Risk Signals
        concerns = []
        if evaluation.get("is_honeypot", False):
            concerns.append("flagged for career timeline discrepancies")
        if candidate.behavioral_signals and candidate.behavioral_signals.notice_period_days > 60:
            concerns.append(f"{candidate.behavioral_signals.notice_period_days}-day notice period requirement")
        
        if concerns:
            concerns_str = f"Risks: {', '.join(concerns)}."
        else:
            concerns_str = "Risks: No timeline anomalies or availability flags."

        # 5. Recommendation Reason
        score = evaluation.get("final_score", 0.0)
        if score >= 80:
            rec_str = f"Recommendation: Strong candidate for the {jd.title} position based on core requirement coverage."
        elif score >= 60:
            rec_str = f"Recommendation: Recommended for preliminary interview to verify specific skill depth."
        else:
            rec_str = f"Recommendation: Lower priority review due to key skill gaps against job requirements."

        explanation = f"{overview} {strengths_str} {gaps_str} {concerns_str} {rec_str}"
        return explanation

    def explain_cohort(self, candidates: List[CandidateIntelligence], evaluations: List[Dict[str, Any]], jd: JobDescription) -> Dict[str, str]:
        """Generates explanations for a list of candidates.

        Returns a dictionary mapping candidate_id to its explanation string.
        """
        explanations: Dict[str, str] = {}
        eval_map = {e["candidate_id"]: e for e in evaluations}
        
        for cand in candidates:
            cid = cand.candidate_id
            eval_data = eval_map.get(cid, {})
            explanations[cid] = self.generate_explanation(cand, eval_data, jd)
            
        return explanations
