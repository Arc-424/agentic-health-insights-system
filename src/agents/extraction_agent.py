import re


class ExtractionAgent:
    """
    Converts raw report text into a structured medical data dictionary.
    Separates patient metadata from lab markers so downstream agents
    work with typed data rather than raw strings.
    """

    # Common lab markers to look for (extend as needed)
    LAB_MARKERS = [
        "hemoglobin", "hgb", "hematocrit", "hct",
        "wbc", "rbc", "platelets", "plt",
        "glucose", "cholesterol", "triglycerides", "hdl", "ldl",
        "creatinine", "urea", "bun",
        "alt", "ast", "alp", "bilirubin",
        "tsh", "t3", "t4",
        "sodium", "potassium", "chloride", "bicarbonate",
        "calcium", "magnesium", "phosphorus",
        "amylase", "lipase",
        "ferritin", "iron", "tibc",
        "vitamin d", "vitamin b12", "folate",
        "hba1c", "a1c",
        "esr", "crp",
    ]

    def extract(self, raw_text: str, patient_meta: dict) -> dict:
        """
        Parse raw report text and merge with patient metadata.

        Args:
            raw_text:     Plain text extracted from the PDF.
            patient_meta: Dict with keys: patient_name, age, gender.

        Returns:
            ExtractedReportData dict consumed by AnalysisAgent.
        """
        detected_markers = self._detect_markers(raw_text)
        sections = self._split_sections(raw_text)

        return {
            "patient_name": patient_meta.get("patient_name", ""),
            "age": patient_meta.get("age", ""),
            "gender": patient_meta.get("gender", ""),
            "report": raw_text,
            "detected_markers": detected_markers,
            "sections": sections,
            "marker_count": len(detected_markers),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_markers(self, text: str) -> list[str]:
        """Return list of lab marker names found in the text."""
        lower = text.lower()
        return [m for m in self.LAB_MARKERS if m in lower]

    def _split_sections(self, text: str) -> dict:
        """
        Attempt a lightweight section split based on common report headings.
        Falls back to a single 'full_report' key if no headings are found.
        """
        heading_pattern = re.compile(
            r"(complete blood count|cbc|lipid profile|liver function|"
            r"renal function|thyroid|metabolic panel|urinalysis)",
            re.IGNORECASE,
        )

        parts = heading_pattern.split(text)
        if len(parts) <= 1:
            return {"full_report": text.strip()}

        sections: dict = {}
        # parts alternates: [pre, heading, content, heading, content, ...]
        for i in range(1, len(parts) - 1, 2):
            heading = parts[i].strip().lower().replace(" ", "_")
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            sections[heading] = content

        return sections
