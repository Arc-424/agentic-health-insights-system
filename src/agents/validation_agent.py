import re


# Reference ranges for common markers (unit-agnostic, value-based heuristics).
# Extend this table as needed.
REFERENCE_RANGES = {
    "hemoglobin": (7.0, 20.0),
    "hgb":        (7.0, 20.0),
    "glucose":    (50.0, 500.0),
    "cholesterol":(50.0, 400.0),
    "triglycerides": (20.0, 1000.0),
    "hdl":        (10.0, 150.0),
    "ldl":        (10.0, 300.0),
    "creatinine": (0.1, 20.0),
    "alt":        (1.0, 500.0),
    "ast":        (1.0, 500.0),
    "tsh":        (0.01, 50.0),
    "hba1c":      (3.0, 20.0),
    "a1c":        (3.0, 20.0),
}

# Markers that MUST be mentioned in the analysis if detected in the report
CRITICAL_MARKERS = {"hemoglobin", "hgb", "glucose", "cholesterol", "creatinine"}


class ValidationAgent:
    """
    Audits the Analysis Agent's output for:
      - Missing critical markers (present in report but absent from analysis)
      - Implausible numeric values (outside broad reference ranges)
      - Internal inconsistencies (contradictory statements)

    Returns a structured validation result consumed by the orchestrator.
    """

    def validate(self, extracted_data: dict, analysis_text: str) -> dict:
        """
        Args:
            extracted_data: Output of ExtractionAgent.extract()
            analysis_text:  Narrative string from AnalysisAgent.analyze_report()

        Returns:
            {
                "status": "PASS" | "NEEDS_REVIEW",
                "issues": [str, ...]   # empty list when PASS
            }
        """
        issues: list[str] = []

        issues.extend(self._check_missing_markers(extracted_data, analysis_text))
        issues.extend(self._check_implausible_values(extracted_data["report"]))
        issues.extend(self._check_inconsistencies(analysis_text))

        status = "PASS" if not issues else "NEEDS_REVIEW"
        return {"status": status, "issues": issues}

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _check_missing_markers(self, extracted_data: dict, analysis_text: str) -> list[str]:
        """Flag critical markers found in the report but not addressed in the analysis."""
        detected = set(extracted_data.get("detected_markers", []))
        critical_present = detected & CRITICAL_MARKERS
        analysis_lower = analysis_text.lower()

        missing = [
            f"Critical marker '{m}' detected in report but not addressed in analysis."
            for m in critical_present
            if m not in analysis_lower
        ]
        return missing

    def _check_implausible_values(self, report_text: str) -> list[str]:
        """
        Scan the raw report text for numeric values next to known markers
        and flag anything outside the broad plausibility range.
        """
        issues: list[str] = []
        lower = report_text.lower()

        for marker, (lo, hi) in REFERENCE_RANGES.items():
            # Look for patterns like "hemoglobin 3.2" or "glucose: 850"
            pattern = rf"{re.escape(marker)}\s*[:\-]?\s*(\d+\.?\d*)"
            for match in re.finditer(pattern, lower):
                try:
                    value = float(match.group(1))
                    if not (lo <= value <= hi):
                        issues.append(
                            f"Implausible value for '{marker}': {value} "
                            f"(expected {lo}–{hi})."
                        )
                except ValueError:
                    pass

        return issues

    def _check_inconsistencies(self, analysis_text: str) -> list[str]:
        """
        Detect simple contradictory phrases in the analysis narrative.
        This is a lightweight heuristic; a more robust approach would use
        an LLM-based consistency checker.
        """
        contradiction_pairs = [
            ("normal", "abnormal"),
            ("elevated", "within normal"),
            ("low", "high"),
            ("no risk", "high risk"),
        ]

        lower = analysis_text.lower()
        issues: list[str] = []

        for term_a, term_b in contradiction_pairs:
            if term_a in lower and term_b in lower:
                issues.append(
                    f"Possible inconsistency: analysis contains both '{term_a}' "
                    f"and '{term_b}'."
                )

        return issues
