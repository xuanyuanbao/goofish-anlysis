from __future__ import annotations

import unicodedata
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


HEADER_STYLE_ID = 2
BODY_STYLE_ID = 1


def export_excel_workbook(path: Path, sheets: dict[str, list[dict[str, object]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook_xml(list(sheets)))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, (sheet_name, rows) in enumerate(sheets.items(), start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _worksheet_xml(rows),
            )


def _content_types(sheet_count: int) -> str:
    worksheet_overrides = "".join(
        (
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{worksheet_overrides}"
        "</Types>"
    )


def _root_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets_xml = "".join(
        (
            f'<sheet name="{escape(_safe_sheet_name(name))}" sheetId="{index}" '
            f'r:id="rId{index}"/>'
        )
        for index, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets_xml}</sheets>"
        "</workbook>"
    )


def _workbook_rels(sheet_count: int) -> str:
    relationships = "".join(
        (
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
        for index in range(1, sheet_count + 1)
    )
    relationships += (
        f'<Relationship Id="rId{sheet_count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}"
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        "</fonts>"
        '<fills count="2">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFDDEBF7"/><bgColor indexed="64"/></patternFill></fill>'
        "</fills>"
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="3">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
        '<xf numFmtId="0" fontId="1" fillId="1" borderId="0" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment wrapText="1" horizontal="center" vertical="center"/></xf>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


def _worksheet_xml(rows: list[dict[str, object]]) -> str:
    if rows:
        headers = list(rows[0].keys())
        body_rows = [[row.get(header, "") for header in headers] for row in rows]
    else:
        headers = ["message"]
        body_rows = [["no data"]]

    all_rows = [headers, *body_rows]
    widths = _column_widths(headers, body_rows)
    row_xml = []
    for row_index, values in enumerate(all_rows, start=1):
        cells = []
        style_id = HEADER_STYLE_ID if row_index == 1 else BODY_STYLE_ID
        for column_index, value in enumerate(values, start=1):
            coordinate = f"{_column_name(column_index)}{row_index}"
            cells.append(_cell_xml(coordinate, value, style_id))
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    last_column = _column_name(len(headers))
    dimension = f"A1:{last_column}{len(all_rows)}"
    cols_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" bestFit="1" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        f'<cols>{cols_xml}</cols>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        f'<autoFilter ref="{dimension}"/>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        "</worksheet>"
    )


def _cell_xml(coordinate: str, value: object, style_id: int) -> str:
    style = f' s="{style_id}"' if style_id else ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{coordinate}"{style}><v>{value}</v></c>'
    text = "" if value is None else escape(str(value))
    preserve = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() else ""
    return f'<c r="{coordinate}" t="inlineStr"{style}><is><t{preserve}>{text}</t></is></c>'


def _column_widths(headers: list[str], body_rows: list[list[object]]) -> list[float]:
    widths: list[float] = []
    for column_index, header in enumerate(headers):
        column_values = [header, *(row[column_index] for row in body_rows)]
        measured = max(_display_width(value) for value in column_values)
        cap = _width_cap(header)
        widths.append(round(min(max(measured + 2, 10), cap), 2))
    return widths


def _display_width(value: object) -> int:
    text = "" if value is None else str(value)
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return max(width, 1)


def _width_cap(header: str) -> int:
    lowered = header.lower()
    if "url" in lowered or "??" in header:
        return 60
    if "desc" in lowered or "title" in lowered or "??" in header or "??" in header:
        return 56
    if "message" in lowered or "??" in header:
        return 64
    return 28


def _column_name(index: int) -> str:
    letters = []
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _safe_sheet_name(name: str) -> str:
    return name[:31].replace("/", "_").replace("\\", "_")
