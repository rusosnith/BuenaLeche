from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pdfplumber


KNOWN_IDS = {"EF", "PL", "MAS", "T1", "T2", "T3", "T4", "T5", "T6"}


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

    rows = _extract_rows(texto)

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


def _extract_rows(text: str) -> list[SampleRow]:
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
