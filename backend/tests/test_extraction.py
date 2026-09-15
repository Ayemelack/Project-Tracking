import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.pdf_extraction_service import PDFExtractionService, _clean_currency, _parse_quantity


class TestCurrencyCleaning:
    def test_clean_currency_with_frs(self):
        assert _clean_currency("72.000frs") == 72000.0

    def test_clean_currency_with_comma(self):
        assert _clean_currency("1,520.000frs") == 1520000.0

    def test_clean_currency_plain_number(self):
        assert _clean_currency("4500") == 4500.0

    def test_clean_currency_empty(self):
        assert _clean_currency("") is None

    def test_clean_currency_none(self):
        assert _clean_currency(None) is None

    def test_clean_currency_with_spaces(self):
        assert _clean_currency(" 72.000frs ") == 72000.0


class TestQuantityParsing:
    def test_parse_quantity_integer(self):
        assert _parse_quantity("3500") == 3500.0

    def test_parse_quantity_decimal(self):
        assert _parse_quantity("154.86") == 154.86

    def test_parse_quantity_empty(self):
        assert _parse_quantity("") is None

    def test_parse_quantity_none(self):
        assert _parse_quantity(None) is None


class TestPDFExtraction:
    def get_test_pdf_path(self) -> str | None:
        candidates = [
            r"C:\Users\noshi\Desktop\EVERYTHING\Resource Audit System\MOLA FAKO GENERAL ESTIMATE (1).pdf",
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'MOLA FAKO GENERAL ESTIMATE (1).pdf'),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def test_extract_mola_fako(self):
        pdf_path = self.get_test_pdf_path()
        if not pdf_path:
            pytest.skip("MOLA FAKO PDF not found in expected locations")

        service = PDFExtractionService()
        result = service.extract_from_pdf(pdf_path)

        assert result is not None
        assert result.estimate is not None
        assert len(result.line_items) > 0

        print(f"\nExtraction Results:")
        print(f"  Title: {result.estimate.title}")
        print(f"  Contractor: {result.estimate.contractor}")
        print(f"  Line items: {len(result.line_items)}")
        print(f"  Warnings: {len(result.warnings)}")

        regular_items = [
            i for i in result.line_items
            if i.section_total_type not in ('section_total', 'grand_total', 'material', 'labour')
        ]
        print(f"  Regular items: {len(regular_items)}")

        total_items = [i for i in result.line_items if i.section_total_type == 'section_total']
        print(f"  Section totals: {len(total_items)}")

        grand_total = [i for i in result.line_items if i.section_total_type == 'grand_total']
        print(f"  Grand totals: {len(grand_total)}")

        for item in result.line_items[:10]:
            print(f"    [{item.section_total_type or 'item'}] {item.description}: {item.total_cost}")

        assert len(result.line_items) >= 10, "Should extract at least 10 items from the MOLA FAKO estimate"

    def test_extraction_has_sections(self):
        pdf_path = self.get_test_pdf_path()
        if not pdf_path:
            pytest.skip("MOLA FAKO PDF not found")

        service = PDFExtractionService()
        result = service.extract_from_pdf(pdf_path)

        categories = set(i.category for i in result.line_items if i.category)
        print(f"\nCategories found: {categories}")
        assert len(categories) >= 3, "Should find at least 3 different categories/sections"
