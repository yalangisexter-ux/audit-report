"""Regression tests for clickable evidence links in exported reports."""
from docx import Document

import app


def test_extract_http_urls_preserves_each_evidence_url():
    first = "https://example.com/proof?id=1"
    second = "https://drive.google.com/file/d/abc/view"
    assert app.extract_http_urls(first + "\n" + second) == [first, second]


def test_word_evidence_url_is_an_external_hyperlink():
    url = "https://example.com/proof?id=1&view=full"
    document = Document()
    paragraph = document.add_paragraph("Proof / Evidence: ")
    app.add_docx_hyperlink(paragraph, url)

    hyperlink = paragraph._p.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hyperlink")
    assert hyperlink is not None
    relationship_id = hyperlink.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    assert paragraph.part.rels[relationship_id].target_ref == url
    text_node = hyperlink.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
    assert text_node.text == url


def test_csv_evidence_urls_remain_raw_urls_for_spreadsheet_link_detection():
    url = "https://example.com/proof?id=1"
    # CSV is a plain-text format: preserving the literal URL lets spreadsheet
    # applications recognize it as a URL instead of replacing it with a label.
    assert app.extract_http_urls(url) == [url]
