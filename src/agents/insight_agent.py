class InsightAgent:
    """
    Produces the final patient-facing health report by combining:
      - The narrative analysis from AnalysisAgent
      - Any validation warnings from ValidationAgent

    This agent does NOT call an LLM; it formats the existing analysis
    and appends validation warnings if present.
    """

    def generate_insight(
        self,
        analysis_text: str,
        validation_result: dict,
        extracted_data: dict,
    ) -> str:
        """
        Args:
            analysis_text:      Narrative from AnalysisAgent.
            validation_result:  {status, issues} from ValidationAgent.
            extracted_data:     Structured data from ExtractionAgent (for metadata).

        Returns:
            Final insight report string.
        """
        patient_name = extracted_data.get("patient_name", "Patient")
        age = extracted_data.get("age", "N/A")
        gender = extracted_data.get("gender", "N/A")

        # Build header
        header = f"# Health Insights Report\n\n"
        header += f"**Patient:** {patient_name}  \n"
        header += f"**Age:** {age} | **Gender:** {gender}\n\n"
        header += "---\n\n"

        # Main analysis
        body = analysis_text

        # Append validation warnings if any
        footer = ""
        if validation_result["status"] == "NEEDS_REVIEW" and validation_result["issues"]:
            footer += "\n\n---\n\n"
            footer += "### ⚠️ Validation Warnings\n\n"
            footer += (
                "The following issues were detected during automated validation. "
                "Please review these points with your healthcare provider:\n\n"
            )
            for issue in validation_result["issues"]:
                footer += f"- {issue}\n"

        return header + body + footer
