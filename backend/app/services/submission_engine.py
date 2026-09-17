import csv
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("app.services.submission_engine")

class SubmissionEngine:
    """Submission Engine responsible for generating and validating the final submission CSV file."""

    def __init__(self) -> None:
        pass

    def generate_submission(
        self,
        ranked_cohort: List[Dict[str, Any]],
        explanations: Dict[str, str],
        output_path: str
    ) -> None:
        """Writes the top 100 candidates to a CSV file matching the required format.

        Columns: candidate_id, rank, score, reasoning.
        """
        # Ensure we have at least 100 candidates, otherwise take all
        top_cohort = ranked_cohort[:100]
        
        # Open CSV file for writing
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Format rows: ensure score ties are sorted by candidate_id ascending.
        # Python's Timsort is stable. Our RankingEngine already performed this sort.
        # But we will double check here.
        sorted_rows = sorted(
            top_cohort,
            key=lambda x: (
                -x["final_score"],
                -x.get("scoring_breakdown", {}).get("behavior_score", 0.0),
                x["candidate_id"]
            )
        )
        
        logger.info(f"Generating submission CSV at {out_file} with {len(sorted_rows)} rows...")
        
        results_map = {}

        with open(out_file, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # Write header row
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            
            # Write data rows
            for rank_idx, record in enumerate(sorted_rows, 1):
                cid = record["candidate_id"]
                score = record["final_score"]
                reasoning = explanations.get(cid, "Candidate is highly suited for the role's requirements.")
                
                writer.writerow([cid, rank_idx, score, reasoning])

                sb = record.get("scoring_breakdown", {})
                score_breakdown = {
                    "skill_score": sb.get("skill_score", 0.0),
                    "experience_score": sb.get("experience_score", 0.0),
                    "education_score": sb.get("education_score", 0.0),
                    "project_score": sb.get("project_score", 0.0),
                    "behavior_score": sb.get("behavior_score", 0.0),
                    "availability_score": sb.get("availability_score", 0.0),
                    "engagement_bonus": sb.get("engagement_bonus", 0.0),
                    "final_score": score
                }

                sa = record.get("skill_analysis")
                if isinstance(sa, dict):
                    exact_m = sa.get("exact_matches", [])
                    syn_m = sa.get("synonym_matches", [])
                    miss_req = sa.get("missing_required_skills", [])
                    miss_pref = sa.get("missing_preferred_skills", [])
                elif sa is not None:
                    exact_m = getattr(sa, "exact_matches", [])
                    syn_m = getattr(sa, "synonym_matches", [])
                    miss_req = getattr(sa, "missing_required_skills", [])
                    miss_pref = getattr(sa, "missing_preferred_skills", [])
                else:
                    exact_m, syn_m, miss_req, miss_pref = [], [], [], []

                c_matched = sb.get("critical_skills_matched", [])
                i_matched = sb.get("important_skills_matched", [])
                n_matched = sb.get("nice_to_have_skills_matched", [])

                matched_skills = list(dict.fromkeys(exact_m + syn_m)) if (exact_m or syn_m) else record.get("matched_skills", list(dict.fromkeys(c_matched + i_matched + n_matched)))
                missing_skills = list(dict.fromkeys(miss_req + miss_pref)) if (miss_req or miss_pref) else record.get("missing_skills", sb.get("missing_critical_skills", []))

                all_matched_list = c_matched + i_matched + n_matched + matched_skills
                matched_set = {s.strip().lower() for s in all_matched_list if isinstance(s, str)}
                missing_skills = [s for s in missing_skills if isinstance(s, str) and s.strip().lower() not in matched_set]

                results_map[cid] = {
                    "candidate_id": cid,
                    "rank": rank_idx,
                    "final_score": score,
                    "is_honeypot": record.get("is_honeypot", False),
                    "reasoning": reasoning,
                    "score_breakdown": score_breakdown,
                    "critical_skills_matched": c_matched,
                    "important_skills_matched": i_matched,
                    "nice_to_have_skills_matched": n_matched,
                    "missing_critical_skills": sb.get("missing_critical_skills", []),
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "name": record.get("name", ""),
                    "years_of_experience": record.get("years_of_experience", 0.0),
                    "location": record.get("location", ""),
                    "open_to_work": record.get("open_to_work", False),
                    "notice_period_days": record.get("notice_period_days", 0),
                    "skills": record.get("skills", []),
                    "current_title": record.get("current_title", ""),
                    "current_company": record.get("current_company", "")
                }
                
        logger.info("Submission CSV generated successfully")

        # Save persistent ranking_results.json
        try:
            import json
            from backend.app.config.settings import BASE_DIR
            out_parent = Path(output_path).parent
            # If output_path is in backend/app or project root (production screening), save to backend/app/ranking_results.json
            if out_parent == Path(".") or out_parent.resolve() == BASE_DIR or out_parent.resolve() == (BASE_DIR / "backend" / "app"):
                results_file = BASE_DIR / "backend" / "app" / "ranking_results.json"
            else:
                results_file = out_parent / "ranking_results.json"

            results_file.parent.mkdir(parents=True, exist_ok=True)
            with open(results_file, "w", encoding="utf-8") as rf:
                json.dump(results_map, rf, indent=2)
            logger.info(f"Saved persistent evaluation artifact to {results_file}")
        except Exception as e:
            logger.warning(f"Failed to write ranking_results.json: {e}")


    def validate_submission_file(self, validation_script_path: str, csv_path: str) -> Tuple[bool, List[str]]:
        """Runs the official validation script on the generated CSV file."""
        script_file = Path(validation_script_path)
        csv_file = Path(csv_path)
        
        if not script_file.exists():
            logger.warning(f"Validation script not found at {script_file}. Skipping execution.")
            return False, ["Validation script not found."]
            
        if not csv_file.exists():
            return False, ["CSV submission file not found."]
            
        try:
            # Execute validation script
            # In Windows, we run with python executable
            result = subprocess.run(
                ["python", str(script_file), str(csv_file)],
                capture_output=True,
                text=True,
                check=False
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode == 0:
                logger.info(f"Submission validation passed: {stdout}")
                return True, [stdout]
            else:
                logger.error(f"Submission validation failed. Code: {result.returncode}\nStdout: {stdout}\nStderr: {stderr}")
                errors = stdout.split("\n") if stdout else [stderr]
                return False, errors
        except Exception as e:
            logger.error(f"Failed to execute validation script: {e}")
            return False, [str(e)]
