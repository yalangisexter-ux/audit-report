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
    assert text_node.text == "Proof link"
    assert hyperlink.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color").get(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
    ) == "0563C1"
    assert hyperlink.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}u") is not None


def test_pdf_link_uses_a_short_clickable_label_and_keeps_google_target():
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph

    url = "https://docs.google.com/document/d/example/edit?usp=sharing&tab=t.0"
    paragraph = Paragraph(app.report_pdf_hyperlink(url, "Proof link 1"), getSampleStyleSheet()["BodyText"])
    assert paragraph.getPlainText() == "Proof link 1"
    assert paragraph.frags[0].link[0][1] == url
    assert paragraph.frags[0].textColor.hexval() == "0x0563c1"
    assert paragraph.frags[0].us_lines


def test_csv_evidence_urls_are_clickable_spreadsheet_hyperlink_formulas():
    url = "https://docs.google.com/spreadsheets/d/example/edit?usp=sharing"
    formula = app.csv_hyperlink_formula(url, "Proof link 1")
    assert formula == f'=HYPERLINK("{url}","Proof link 1")'
