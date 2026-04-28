import logging
from agents.ingestion_agent import IngestionAgent
from agents.extraction_agent import ExtractionAgent
from agents.analysis_agent import AnalysisAgent
from agents.validation_agent import ValidationAgent
from agents.insight_agent import InsightAgent
from config.prompts import SPECIALIST_PROMPTS

logger = logging.getLogger(__name__)

MAX_VALIDATION_RETRIES = 2


class AgentOrchestrator:
    """
    Drives the full agent pipeline:

        Ingestion → Extraction → Analysis → Validation
                                     ↑           |
                                     └── retry ──┘ (up to MAX_VALIDATION_RETRIES)
                                                 |
                                              Insight

    The orchestrator owns all routing decisions.  Individual agents are
    stateless with respect to the pipeline; they receive inputs and return
    structured outputs.
    """

    def __init__(self):
        self.ingestion_agent  = IngestionAgent()
        self.extraction_agent = ExtractionAgent()
        self.analysis_agent   = AnalysisAgent()
        self.validation_agent = ValidationAgent()
        self.insight_agent    = InsightAgent()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        patient_meta: dict,
        pdf_file=None,
        use_sample: bool = False,
    ) -> dict:
        """
        Execute the full pipeline.

        Args:
            patient_meta: {"patient_name": str, "age": str, "gender": str}
            pdf_file:     Streamlit UploadedFile or None.
            use_sample:   Use built-in sample report when True.

        Returns:
            {
                "success":           bool,
                "insight":           str,   # final patient-facing report
                "validation_result": dict,  # {status, issues}
                "retries":           int,   # number of validation retries used
                "error":             str,   # set only on failure
            }
        """
        # ── Step 1: Ingestion ──────────────────────────────────────────
        logger.info("Orchestrator: starting ingestion")
        ingestion_result = self.ingestion_agent.ingest(pdf_file, use_sample)
        if not ingestion_result["success"]:
            return self._failure(ingestion_result["error"])

        raw_text = ingestion_result["text"]

        # ── Step 2: Extraction ─────────────────────────────────────────
        logger.info("Orchestrator: extracting structured data")
        extracted_data = self.extraction_agent.extract(raw_text, patient_meta)

        # ── Step 3 + 4: Analysis → Validation loop ────────────────────
        system_prompt = SPECIALIST_PROMPTS["comprehensive_analyst"]
        analysis_text = ""
        validation_result = {"status": "NEEDS_REVIEW", "issues": []}
        retries = 0

        while retries <= MAX_VALIDATION_RETRIES:
            logger.info(f"Orchestrator: analysis attempt {retries + 1}")

            # Build prompt — on retries, inject validation feedback
            prompt = self._build_prompt(system_prompt, validation_result, retries)

            analysis_result = self.analysis_agent.analyze_report(
                data=extracted_data,
                system_prompt=prompt,
            )

            if not analysis_result.get("success"):
                return self._failure(analysis_result.get("error", "Analysis failed."))

            analysis_text = analysis_result["content"]

            # Validate the output
            logger.info("Orchestrator: validating analysis")
            validation_result = self.validation_agent.validate(extracted_data, analysis_text)

            if validation_result["status"] == "PASS":
                logger.info("Orchestrator: validation PASSED")
                break

            retries += 1
            logger.warning(
                f"Orchestrator: validation NEEDS_REVIEW (retry {retries}), "
                f"issues: {validation_result['issues']}"
            )

        # ── Step 5: Insight generation ────────────────────────────────
        logger.info("Orchestrator: generating final insight")
        insight = self.insight_agent.generate_insight(
            analysis_text, validation_result, extracted_data
        )

        return {
            "success": True,
            "insight": insight,
            "validation_result": validation_result,
            "retries": retries,
            "error": None,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self, base_prompt: str, validation_result: dict, retry_num: int
    ) -> str:
        """
        On retries, append validation feedback to the system prompt so the
        Analysis Agent can address the flagged issues.
        """
        if retry_num == 0 or not validation_result["issues"]:
            return base_prompt

        feedback = "\n\n## Validation Feedback (Previous Attempt)\n"
        feedback += "Your previous analysis was flagged for the following issues. "
        feedback += "Please address each one explicitly in your revised analysis:\n"
        for issue in validation_result["issues"]:
            feedback += f"- {issue}\n"

        return base_prompt + feedback

    @staticmethod
    def _failure(error: str) -> dict:
        return {
            "success": False,
            "insight": "",
            "validation_result": {"status": "NEEDS_REVIEW", "issues": []},
            "retries": 0,
            "error": error,
        }
