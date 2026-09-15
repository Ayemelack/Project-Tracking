import re
import pdfplumber
from pathlib import Path
from typing import Optional
from app.core.logging import logger
from app.schemas.schemas import (
    ExtractionResult, EstimateLineItemBase, EstimateBase
)

SECTION_PATTERNS = [
    r'^(\d{1,2})\)\s+([A-Z][A-Z ()]+)',        # "1) FOUNDATION"
    r'^(\d{1,2}[A-C]?)\)\s+([A-Z][A-Z ()]+)',  # "11A) PLUMBING WORK (PIPPING)"
]

COST_OF_MATERIALS = re.compile(r'cost\s+of\s+materials?', re.IGNORECASE)
LABOUR_PATTERN = re.compile(r'^labour', re.IGNORECASE)
TOTAL_PATTERN = re.compile(r'^total', re.IGNORECASE)
GRAND_TOTAL_PATTERN = re.compile(r'grand\s+total', re.IGNORECASE)
SUMMARY_PATTERN = re.compile(r'summary', re.IGNORECASE)

HEADER_KEYWORDS = re.compile(
    r'(MOLA FAKO|SERVICES OFFERED|HEAD OFFICE|Tel:|E-Mail|Note:|follow up)',
    re.IGNORECASE
)


def _clean_currency(value: str) -> Optional[float]:
    if not value:
        return None
    original = value.strip()
    lower = original.lower()
    has_frs = 'frs' in lower or 'fcfa' in lower
    cleaned = lower.replace('frs', '').replace('fcfa', '').strip()
    cleaned = cleaned.replace(',', '').replace(' ', '')
    if not cleaned or cleaned == '-' or cleaned == '/':
        return None
    if has_frs:
        cleaned = cleaned.replace('.', '')
    else:
        # Plain number: if last group after dot is exactly 3 digits, treat dot as thousands sep
        if re.search(r'\.\d{3}$', cleaned):
            cleaned = cleaned.replace('.', '')
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_quantity(value: str) -> Optional[float]:
    if not value:
        return None
    cleaned = value.strip().replace(',', '')
    if not cleaned or cleaned == '-' or cleaned == '/':
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_section_name(name: str) -> str:
    name = name.strip()
    opens = name.count('(')
    closes = name.count(')')
    if opens > closes:
        name += ')' * (opens - closes)
    return name


def _detect_section_from_text(text: str) -> Optional[str]:
    for line in text.split('\n'):
        line = line.strip()
        for pattern in SECTION_PATTERNS:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return _normalize_section_name(match.group(2))
    return None


class PDFExtractionService:
    def extract_from_pdf(self, file_path: str) -> ExtractionResult:
        logger.info(f"Starting PDF extraction: {file_path}")
        pdf = pdfplumber.open(file_path)

        all_line_items: list[EstimateLineItemBase] = []
        warnings: list[str] = []
        extraction_notes: list[str] = []
        current_section: Optional[str] = None
        document_info: dict = {}

        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""

            if page_num == 1:
                self._extract_header_info(text, document_info, extraction_notes)

            # Summary page: only extract grand total, skip section totals
            if SUMMARY_PATTERN.search(text) and page_num > 1:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        row_text = ' '.join(str(c or '') for c in row).lower()
                        if GRAND_TOTAL_PATTERN.search(row_text):
                            for cell in reversed(row):
                                val = _clean_currency(str(cell or ''))
                                if val is not None:
                                    all_line_items.append(EstimateLineItemBase(
                                        description="GRAND TOTAL",
                                        total_cost=val,
                                        source_page=page_num,
                                        section_total_type="grand_total",
                                    ))
                                    extraction_notes.append(f"Grand total found: {val}")
                                    break
                continue

            # Find section headers with their y-positions
            headers_with_pos: list[tuple[float, str]] = []
            try:
                chars = page.chars
                lines_map: dict[float, str] = {}
                for c in chars:
                    y = round(c['top'], 1)
                    if y not in lines_map:
                        lines_map[y] = ''
                    lines_map[y] += c.get('text', '')
                for y_pos, line_text in sorted(lines_map.items()):
                    for pattern in SECTION_PATTERNS:
                        match = re.match(pattern, line_text.strip(), re.IGNORECASE)
                        if match:
                            headers_with_pos.append((y_pos, _normalize_section_name(match.group(2))))
            except Exception:
                pass

            tables = page.extract_tables()
            table_bboxes = page.find_tables()

            for i, table in enumerate(tables):
                # Find the nearest section header above this table
                if i < len(table_bboxes) and headers_with_pos:
                    table_top = table_bboxes[i].bbox[1]
                    best_section = None
                    for h_pos, h_name in headers_with_pos:
                        if h_pos < table_top:
                            best_section = h_name
                        else:
                            break
                    if best_section:
                        current_section = best_section
                elif not headers_with_pos:
                    # Fallback: detect section from full page text
                    page_section = _detect_section_from_text(text)
                    if page_section:
                        current_section = page_section

                items = self._parse_table(
                    table, current_section, page_num, warnings, extraction_notes
                )
                all_line_items.extend(items)

        pdf.close()

        # Keep only detail-page section totals (not summary-page ones)
        # Detail pages have source_page < 10, summary is page 10+
        seen_categories: set[str] = set()
        deduplicated: list[EstimateLineItemBase] = []
        grand_total_item: Optional[EstimateLineItemBase] = None

        for item in all_line_items:
            if item.section_total_type == 'grand_total':
                grand_total_item = item
                continue
            if item.section_total_type == 'section_total':
                key = item.category or item.description
                if key in seen_categories:
                    continue
                seen_categories.add(key)
            deduplicated.append(item)

        if grand_total_item:
            deduplicated.append(grand_total_item)
        all_line_items = deduplicated

        total = sum(
            item.total_cost for item in all_line_items
            if item.total_cost and item.section_total_type not in ('section_total', 'grand_total', 'material', 'labour')
        )

        estimate = EstimateBase(
            title=document_info.get("title", "Untitled Estimate"),
            project_name=document_info.get("project_name"),
            reference_number=document_info.get("reference_number"),
            contractor=document_info.get("contractor"),
            client=document_info.get("client"),
            currency="FCFA",
        )

        logger.info(f"Extraction complete: {len(all_line_items)} items found")
        return ExtractionResult(
            estimate=estimate,
            line_items=all_line_items,
            warnings=warnings,
            extraction_notes=extraction_notes,
        )

    def _extract_header_info(self, text: str, info: dict, notes: list):
        lines = text.split('\n')
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            if HEADER_KEYWORDS.search(line_stripped) and 'MOLA FAKO' in line_stripped.upper():
                if 'title' not in info:
                    info['title'] = line_stripped
                    info['contractor'] = line_stripped
                    info['project_name'] = line_stripped
                    notes.append(f"Contractor extracted from header: {line_stripped}")

    def _parse_table(
        self,
        table: list[list],
        section: Optional[str],
        page_num: int,
        warnings: list,
        notes: list,
    ) -> list[EstimateLineItemBase]:
        items: list[EstimateLineItemBase] = []
        if not table or len(table) < 2:
            return items

        header_row = table[0]
        header_text = ' '.join(str(c or '') for c in header_row).lower()

        is_summary_table = (
            'summary' in header_text
            or (len(header_row) <= 3 and not any(
                kw in header_text for kw in ['no', 'description', 'qty']
            ))
        )

        if is_summary_table:
            return self._parse_summary_table(table, page_num, notes)

        has_standard_header = (
            any('no' in str(c or '').lower() for c in header_row)
            and any('desc' in str(c or '').lower() for c in header_row)
        )

        for row in table[1:]:
            if not row or all(c is None or str(c).strip() == '' for c in row):
                continue

            row_text = ' '.join(str(c or '') for c in row).lower()

            if COST_OF_MATERIALS.search(row_text):
                total_val = self._extract_total_from_row(row)
                if total_val is not None:
                    items.append(EstimateLineItemBase(
                        description="Cost of Materials",
                        total_cost=total_val,
                        category=section,
                        source_page=page_num,
                        section_total_type="material",
                    ))
                continue

            if LABOUR_PATTERN.match(row_text.strip()):
                total_val = self._extract_total_from_row(row)
                if total_val is not None:
                    items.append(EstimateLineItemBase(
                        description="Labour",
                        total_cost=total_val,
                        category=section,
                        source_page=page_num,
                        section_total_type="labour",
                    ))
                continue

            if TOTAL_PATTERN.match(row_text.strip()) and not GRAND_TOTAL_PATTERN.search(row_text):
                total_val = self._extract_total_from_row(row)
                if total_val is not None:
                    items.append(EstimateLineItemBase(
                        description=f"TOTAL - {section}" if section else "Section Total",
                        total_cost=total_val,
                        category=section,
                        source_page=page_num,
                        section_total_type="section_total",
                    ))
                continue

            if GRAND_TOTAL_PATTERN.search(row_text):
                total_val = self._extract_total_from_row(row)
                if total_val is not None:
                    items.append(EstimateLineItemBase(
                        description="GRAND TOTAL",
                        total_cost=total_val,
                        category=section,
                        source_page=page_num,
                        section_total_type="grand_total",
                    ))
                continue

            item = self._parse_line_item_row(row, section, page_num, warnings)
            if item:
                items.append(item)

        return items

    def _parse_summary_table(
        self, table: list[list], page_num: int, notes: list
    ) -> list[EstimateLineItemBase]:
        items = []
        for row in table:
            if not row or all(c is None or str(c).strip() == '' for c in row):
                continue

            row_text = ' '.join(str(c or '') for c in row).strip()
            if not row_text:
                continue

            if GRAND_TOTAL_PATTERN.search(row_text):
                total_val = self._extract_total_from_row(row)
                if total_val is not None:
                    items.append(EstimateLineItemBase(
                        description="GRAND TOTAL",
                        total_cost=total_val,
                        source_page=page_num,
                        section_total_type="grand_total",
                    ))
                    notes.append(f"Grand total found: {total_val}")
                continue

            match = None
            for pattern in SECTION_PATTERNS:
                match = re.search(pattern, row_text, re.IGNORECASE)
                if match:
                    break

            if match:
                section_name = match.group(2).strip()
                total_val = self._extract_total_from_row(row)
                if total_val is not None:
                    items.append(EstimateLineItemBase(
                        description=f"Section: {section_name}",
                        category=section_name,
                        total_cost=total_val,
                        source_page=page_num,
                        section_total_type="section_total",
                    ))

        return items

    def _parse_line_item_row(
        self,
        row: list,
        section: Optional[str],
        page_num: int,
        warnings: list,
    ) -> Optional[EstimateLineItemBase]:
        cells = [str(c or '').strip() for c in row]

        if len(cells) < 3:
            return None

        item_number = cells[0] if cells[0] else None
        description = cells[1] if len(cells) > 1 else ""

        if not description or HEADER_KEYWORDS.search(description):
            return None

        quantity = None
        unit_cost = None
        total_cost = None
        unit = None

        numeric_cells = cells[2:]

        if len(numeric_cells) >= 3:
            quantity = _parse_quantity(numeric_cells[0])
            unit_cost = _clean_currency(numeric_cells[1])
            total_cost = _clean_currency(numeric_cells[2])

            qty_text = numeric_cells[0].strip().lower()
            if not any(c.isdigit() for c in qty_text) and qty_text:
                unit = qty_text
                quantity = None

        elif len(numeric_cells) == 2:
            unit_cost = _clean_currency(numeric_cells[0])
            total_cost = _clean_currency(numeric_cells[1])

        if description and (total_cost is not None or unit_cost is not None):
            return EstimateLineItemBase(
                item_number=item_number,
                category=section,
                description=description,
                quantity=quantity,
                unit=unit,
                unit_cost=unit_cost,
                total_cost=total_cost,
                source_page=page_num,
            )

        return None

    def _extract_total_from_row(self, row: list) -> Optional[float]:
        cells = [str(c or '').strip() for c in row]
        for cell in reversed(cells):
            val = _clean_currency(cell)
            if val is not None:
                return val
        return None


pdf_extraction_service = PDFExtractionService()
