from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pdfplumber


KNOWN_IDS = {"EF", "PL", "MAS", "T1", "T2", "T3", "T4", "T5", "T6"}

COLUMN_FIELDS = [
    "mg",
    "proteina",
    "lactosa",
    "sng",
    "st",
    "prov",
    "caseina",
    "mun",
    "crioscopia",
    "rcs",
    "rm",
]

HEADER_LABELS = {
    "PROTE": "proteina",
    "LACTO": "lactosa",
    "SNG": "sng",
    "ST": "st",
    "PRO.V": "prov",
    "CASE.": "caseina",
    "MUN": "mun",
    "CRIOSCOPÍA": "crioscopia",
    "RCS": "rcs",
    "RM": "rm",
}


@dataclass(slots=True)
class SampleRow:
    identificacion: str
    rodeo: str | None
    mg: float | None
    proteina: float | None
    lactosa: float | None
    sng: float | None
    st: float | None
    prov: float | None
    caseina: float | None
    mun: float | None
    crioscopia: float | None
    rcs: float | None
    rm: float | None


@dataclass(slots=True)
class Report:
    source_file: str
    source_name: str
    source_id: str | None
    nro_informe: int | None
    protocolo: int | None
    fecha_ingreso: date | None
    fecha_proceso: date | None
    propietario: str
    especie: str | None
    muestras_recibidas: int | None
    observaciones: str
    rows: list[SampleRow]

    def to_record(self) -> dict[str, Any]:
        data = asdict(self)
        data["fecha_ingreso"] = self.fecha_ingreso.isoformat() if self.fecha_ingreso else None
        data["fecha_proceso"] = self.fecha_proceso.isoformat() if self.fecha_proceso else None
        data["rows"] = [asdict(row) for row in self.rows]
        return data


def parse_pdf(pdf_path: str | Path, *, source_id: str | None = None) -> Report:
    pdf_path = Path(pdf_path)
    texto = _extract_text(pdf_path)

    nro_informe = _extract_int(r"Informe\s*N[°º]?\s*[:\s]+(\d+)", texto)
    protocolo = _extract_int(r"Protocolo:\s*(\d+)", texto) or nro_informe

    fecha_ingreso = _extract_date(r"Fecha de Ingr\.?:\s*(\d{1,2}/\d{1,2}/\d{4})", texto)
    fecha_proceso = _extract_date(r"Fecha Proceso\s*:??\s*(\d{1,2}/\d{1,2}/\d{4})", texto)

    propietario = _extract_text_field(r"Propietario\(\*\*\)\s*:\s*(.+?)\s+Fecha de Ingr", texto)
    especie = _extract_text_field(r"Especie\s*\(\*\*\)\s*:\s*([A-ZÁÉÍÓÚÑ ]+)", texto)
    muestras_recibidas = _extract_int(r"Muestras Recibidas\(\*\*\)\s*:\s*(\d+)", texto)
    observaciones = _extract_text_field(r"Observaciones:\s*\(\s*(-?)\s*\)", texto) or ""
    if observaciones == "-":
        observaciones = ""

    rows = _extract_rows(pdf_path, texto)

    return Report(
        source_file=str(pdf_path),
        source_name=pdf_path.name,
        source_id=source_id,
        nro_informe=nro_informe,
        protocolo=protocolo,
        fecha_ingreso=fecha_ingreso,
        fecha_proceso=fecha_proceso,
        propietario=propietario.strip() if propietario else "",
        especie=especie.strip() if especie else None,
        muestras_recibidas=muestras_recibidas,
        observaciones=observaciones.strip(),
        rows=rows,
    )


def parse_txt(txt_path: str | Path, *, source_id: str | None = None) -> Report:
    txt_path = Path(txt_path)
    text = txt_path.read_text(encoding="utf-8", errors="replace")

    nro_informe = _extract_int(r"Informe\s*N[°º]?\s*:\s*(\d+)", text)
    if nro_informe is None:
        nro_informe = _extract_int(r"Informe\s*N\S*\s*:\s*(\d+)", text)
    if nro_informe is None:
        match = re.search(r"(\d{6,})", txt_path.stem)
        nro_informe = int(match.group(1)) if match else None
    protocolo = nro_informe
    fecha_ingreso = _extract_date(r"Fecha de Ingr\.:\s*(\d{1,2}/\d{1,2}/\d{4})", text)
    fecha_proceso = _extract_date(r"Fecha Proceso\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", text)
    propietario = _extract_text_field(r"Propietario\(\*\*\)\s*:\s*(.+?)\s+Fecha de Ingr", text) or ""
    especie = _extract_text_field(r"Especie\s*\(\*\*\)\s*:\s*([A-ZÁÉÍÓÚÑ ]+)", text)
    muestras_recibidas = _extract_int(r"Muestras Recibidas\(\*\*\)\s*:\s*(\d+)", text)

    vacios = _extract_vacios(text)
    rows = _extract_rows_from_txt(text, vacios)

    return Report(
        source_file=str(txt_path),
        source_name=txt_path.name,
        source_id=source_id,
        nro_informe=nro_informe,
        protocolo=protocolo,
        fecha_ingreso=fecha_ingreso,
        fecha_proceso=fecha_proceso,
        propietario=propietario.strip(),
        especie=especie.strip() if especie else None,
        muestras_recibidas=muestras_recibidas,
        observaciones="",
        rows=rows,
    )


def parse_report(report_path: str | Path, *, source_id: str | None = None) -> Report:
    report_path = Path(report_path)
    suffix = report_path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(report_path, source_id=source_id)
    if suffix == ".txt":
        return parse_txt(report_path, source_id=source_id)
    raise ValueError(f"Formato no soportado: {report_path}")


def _extract_text(pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_text_field(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _extract_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return int(match.group(1)) if match else None


def _extract_date(pattern: str, text: str) -> date | None:
    value = _extract_text_field(pattern, text)
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _is_identification(value: str) -> bool:
    return bool(value and (value in KNOWN_IDS or re.fullmatch(r"T\d+", value)))


def _extract_rows(pdf_path: Path, text: str) -> list[SampleRow]:
    rows = _extract_rows_by_layout(pdf_path)
    if rows:
        return rows
    return _extract_rows_from_text(text)


def _extract_rows_by_layout(pdf_path: Path) -> list[SampleRow]:
    rows: list[SampleRow] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            line_groups = _group_words_by_line(page.extract_words(use_text_flow=True))
            anchors, header_top = _extract_column_anchors(line_groups)
            if not anchors:
                continue

            for line in line_groups:
                if line[0]["top"] <= header_top:
                    continue

                ident = line[0]["text"].upper()
                if not _is_identification(ident):
                    continue

                values: dict[str, float | None] = {field: None for field in COLUMN_FIELDS}
                for word in line[1:]:
                    token = word["text"]
                    if not re.fullmatch(r"[\d.,]+", token):
                        continue

                    value = _to_float(token)
                    if value is None:
                        continue

                    center = (word["x0"] + word["x1"]) / 2
                    field = min(anchors, key=lambda name: abs(anchors[name] - center))
                    values[field] = value

                rows.append(
                    SampleRow(
                        identificacion=ident,
                        rodeo=ident if ident.startswith("T") else None,
                        mg=values["mg"],
                        proteina=values["proteina"],
                        lactosa=values["lactosa"],
                        sng=values["sng"],
                        st=values["st"],
                        prov=values["prov"],
                        caseina=values["caseina"],
                        mun=values["mun"],
                        crioscopia=values["crioscopia"],
                        rcs=values["rcs"],
                        rm=values["rm"],
                    )
                )

    return rows


def _group_words_by_line(words: list[dict[str, Any]], tolerance: float = 2.0) -> list[list[dict[str, Any]]]:
    grouped: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if not grouped or abs(grouped[-1][0]["top"] - word["top"]) > tolerance:
            grouped.append([word])
        else:
            grouped[-1].append(word)
    return grouped


def _extract_column_anchors(line_groups: list[list[dict[str, Any]]]) -> tuple[dict[str, float], float]:
    for line in line_groups:
        labels = [word["text"] for word in line]
        normalized = {label.upper() for label in labels}
        if not {"RCS", "RM", "ST"}.issubset(normalized):
            continue

        anchors: dict[str, float] = {}
        mg_parts = [word for word in line if word["text"] in {"M", "G"}]
        if len(mg_parts) >= 2:
            anchors["mg"] = sum((word["x0"] + word["x1"]) / 2 for word in mg_parts[:2]) / 2

        for word in line:
            field = HEADER_LABELS.get(word["text"].upper())
            if field:
                anchors[field] = (word["x0"] + word["x1"]) / 2

        if set(COLUMN_FIELDS).issubset(anchors):
            return anchors, line[0]["top"]

    return {}, 0.0


def _extract_rows_from_text(text: str) -> list[SampleRow]:
    rows: list[SampleRow] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        parts = line.split(" ")
        ident = parts[0].upper()
        if not _is_identification(ident):
            continue

        numeric_values = [_to_float(part) for part in parts[1:] if re.fullmatch(r"[\d.,]+", part)]
        while len(numeric_values) < 11:
            numeric_values.append(None)

        rows.append(
            SampleRow(
                identificacion=ident,
                rodeo=ident if ident.startswith("T") else None,
                mg=numeric_values[0],
                proteina=numeric_values[1],
                lactosa=numeric_values[2],
                sng=numeric_values[3],
                st=numeric_values[4],
                prov=numeric_values[5],
                caseina=numeric_values[6],
                mun=numeric_values[7],
                crioscopia=numeric_values[8],
                rcs=numeric_values[9],
                rm=numeric_values[10],
            )
        )

    return rows


def _extract_vacios(text: str) -> set[str]:
    match = re.search(r"Vac[íi]os\s*:\s*(.*?)\n\s*\n", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return set()

    values = re.findall(r"\d+", match.group(1))
    return {str(int(value)) for value in values}


def _extract_rows_from_txt(text: str, vacios: set[str]) -> list[SampleRow]:
    rows: list[SampleRow] = []
    in_table = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        compact = " ".join(line.split())

        if not in_table:
            if compact.upper().startswith("IDENTIF"):
                in_table = True
            continue

        if not compact:
            continue
        if compact.upper().startswith("LECHE COAGULADA"):
            break

        match = re.match(r"^(\d{1,4})\s+(.*)$", compact)
        if not match:
            continue

        ident = str(int(match.group(1)))
        remainder = match.group(2)
        tokens = re.findall(r"\d+(?:[\.,]\d+)?", remainder)
        numeric_values = [_to_float(token) for token in tokens]

        mg = proteina = lactosa = st = rcs = rm = crioscopia = mun = None
        if ident in vacios:
            rcs = 0.0
        elif len(numeric_values) == 1:
            rcs = numeric_values[0]
        elif len(numeric_values) >= 5:
            mg = numeric_values[0]
            proteina = numeric_values[1]
            lactosa = numeric_values[2]
            st = numeric_values[3]
            rcs = numeric_values[4]
            if len(numeric_values) > 5:
                rm = numeric_values[5]
            if len(numeric_values) > 6:
                crioscopia = numeric_values[6]
            if len(numeric_values) > 7:
                mun = numeric_values[7]
        else:
            continue

        rows.append(
            SampleRow(
                identificacion=ident,
                rodeo=None,
                mg=mg,
                proteina=proteina,
                lactosa=lactosa,
                sng=None,
                st=st,
                prov=None,
                caseina=None,
                mun=mun,
                crioscopia=crioscopia,
                rcs=rcs,
                rm=rm,
            )
        )

    return rows
