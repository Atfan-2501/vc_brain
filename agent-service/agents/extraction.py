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


def extract_claims_from_text(text: str) -> dict:
    """Extract claims from web content (Tier-2 enrichment). The text is a concatenation of
    Tavily results with their URLs inline; the model sets source_ref.type='web' and the URL
    the claim came from. Returns {claims:[...], missing_data:[...]}."""
    prompt = ("Extract atomic, factual claims about the founder, company, traction, or market "
              "from the web content below. For EACH claim, set source_ref.type='web' and "
              "source_ref.url to the exact URL (shown as 'SOURCE: <url>') it came from. Ignore "
              "marketing fluff; keep only checkable assertions.\n\n" + text)
    return call_structured("extraction", EXTRACTION_SCHEMA, prompt,
                           extra_system="Only assert what the text supports. Do not infer numbers.")


# --- helper: render a PDF to base64 data-URLs for the multimodal call ---
def pdf_to_images(deck_bytes: bytes, max_pages: int = 20, dpi: int = 120) -> list[str]:
    """Render deck pages to base64 PNG data-URLs for the multimodal model. Uses PyMuPDF (self-
    contained, no system poppler needed). Caps pages, rejects encrypted PDFs."""
    import base64
    import fitz  # pymupdf
    doc = fitz.open(stream=deck_bytes, filetype="pdf")
    if getattr(doc, "needs_pass", False):
        raise RuntimeError("deck is password-protected — cannot read")
    urls = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(dpi=dpi)
        b64 = base64.b64encode(pix.tobytes("png")).decode()
        urls.append(f"data:image/png;base64,{b64}")
    if not urls:
        raise RuntimeError("no pages rendered from deck")
    return urls
