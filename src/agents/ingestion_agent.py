from utils.pdf_extractor import extract_text_from_pdf
from config.sample_data import SAMPLE_REPORT


class IngestionAgent:
    """
    Entry point of the pipeline.
    Accepts either an uploaded PDF file object or a flag to use the
    built-in sample report, and returns validated plain text.
    """

    def ingest(self, pdf_file=None, use_sample: bool = False) -> dict:
        """
        Args:
            pdf_file:   A file-like object (Streamlit UploadedFile).
            use_sample: If True, return the built-in sample report text.

        Returns:
            {
                "success": bool,
                "text":    str,   # raw report text on success
                "error":   str,   # error message on failure
            }
        """
        if use_sample:
            return {"success": True, "text": SAMPLE_REPORT, "error": None}

        if pdf_file is None:
            return {"success": False, "text": "", "error": "No PDF file provided."}

        result = extract_text_from_pdf(pdf_file)

        # extract_text_from_pdf returns a string — either the text or an error message
        if result.startswith("Error") or result.startswith("PDF") or result.startswith("Could not"):
            return {"success": False, "text": "", "error": result}

        return {"success": True, "text": result, "error": None}
