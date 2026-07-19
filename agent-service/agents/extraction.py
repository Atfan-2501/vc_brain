"""Extraction Agent — deck PDF (multimodal) or scraped page -> structured claims.
H1-H6. Render PDF pages to images, send to the multimodal model, get claims back."""
from schemas import EXTRACTION_SCHEMA
from ._common import call_structured


def extract_claims(deck_images: list[str] | None = None, page_text: str = "") -> dict:
    """Returns {claims: [...], missing_data: [...]}. Each claim has source_ref with slide_number."""
    prompt = ("Extract every atomic factual claim from this pitch deck / page. "
              "For each, record the slide number (or URL) it came from. "
              "List anything a VC would expect but that is absent in missing_data "
              "(e.g. cap table, financials, revenue).")
    return call_structured(
        "extraction", EXTRACTION_SCHEMA, prompt,
        extra_system="Do not invent numbers not present in the source.",
        multimodal_images=deck_images,
    )


# --- helper: render a PDF to base64 data-URLs for the multimodal call ---
def pdf_to_images(deck_bytes: bytes) -> list[str]:
    """TODO: render pages with pypdf/pdf2image -> base64 'data:image/png;base64,...' URLs.
    For a text-only fallback, extract text with pypdf and pass via page_text instead."""
    raise NotImplementedError("wire in H1-H6")
