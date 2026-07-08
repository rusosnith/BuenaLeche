"""
labvima_parser.py
-----------------
Extrae los datos de un informe PDF de LABVIMA y los devuelve
como una lista de diccionarios, uno por identificación (EF, PL, T1-T6, MAS, etc.).
"""

import re
import pdfplumber
from datetime import datetime


# Identificadores conocidos. El script detecta cualquiera que aparezca en la tabla.
IDS_CONOCIDOS = {"EF", "PL", "T1", "T2", "T3", "T4", "T5", "T6", "MAS"}


def extraer_informe(pdf_path: str) -> dict:
    """
    Parsea un PDF de LABVIMA y retorna:
    {
        "nro_informe": int,
        "fecha_proceso": date,
        "fecha_ingreso": date,
        "propietario": str,
        "filas": [ { campo: valor, ... }, ... ]
    }
    """
    with pdfplumber.open(pdf_path) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    nro_informe = _extraer_campo(r"Informe\s*N[°º]\s*[:\s]+(\d+)", texto_completo)
    fecha_proceso = _extraer_fecha(r"Fecha\s+Pr?\s*oceso\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", texto_completo)
    fecha_ingreso = _extraer_fecha(r"Fecha de Ingr\.\s*[:\s]+(\d{1,2}/\d{1,2}/\d{4})", texto_completo)
    propietario = _extraer_campo(r"Propietario\(\*\*\)\s*:\s*(.+?)(?:\s{2,}|$)", texto_completo)

    filas = _extraer_tabla(texto_completo, pdf_path)

    return {
        "nro_informe": int(nro_informe) if nro_informe else None,
        "fecha_proceso": fecha_proceso,
        "fecha_ingreso": fecha_ingreso,
        "propietario": propietario.strip() if propietario else "",
        "filas": filas,
    }


def _extraer_campo(patron, texto):
    m = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def _extraer_fecha(patron, texto):
    val = _extraer_campo(patron, texto)
    if not val:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _numero(s):
    """Convierte un string a float, o None si no es numérico."""
    if s is None:
        return None
    s = s.strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _extraer_tabla(texto: str, pdf_path: str) -> list:
    """
    Estrategia 1: intentar con pdfplumber (extracción de tabla).
    Estrategia 2: fallback por regex sobre el texto plano.
    """
    filas = _extraer_tabla_pdfplumber(pdf_path)
    if filas:
        return filas
    return _extraer_tabla_regex(texto)


def _extraer_tabla_pdfplumber(pdf_path: str) -> list:
    """
    Intenta extraer la tabla de datos usando pdfplumber con detección automática.
    """
    filas = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        # Primera celda: identificador (EF, PL, T1, T2, etc.)
                        ident = (row[0] or "").strip().upper()
                        # Aceptamos cualquier identificador que empiece con letra conocida
                        if not _es_identificador(ident):
                            continue
                        fila = _mapear_columnas_tabla(ident, row)
                        if fila:
                            filas.append(fila)
    except Exception:
        pass
    return filas


def _extraer_tabla_regex(texto: str) -> list:
    """
    Fallback: parseo línea por línea usando el identificador como ancla.
    Formato LABVIMA: EF  4.95  3.96  4.62  14.90  497  179
    Columnas esperadas: ID  MG  G  Prote  Lacto  [SNG]  ST  [ProV]  [Case]  [MUN]  [Crios]  RCS  RM
    """
    filas = []
    # Patrón: identificador seguido de 2+ números decimales
    patron = re.compile(
        r"^(EF|PL|MAS|T\d+|MAS)\s+"       # identificador
        r"([\d.]+)\s+"                       # M.G.
        r"([\d.]+)\s+"                       # Proteína
        r"([\d.]+)\s+"                       # Lactosa
        r"([\d.]+)"                          # S.T. (mínimo hasta acá)
        r"(?:\s+([\d.]+))?"                  # RCS (opcional en misma línea)
        r"(?:\s+([\d.]+))?",                 # RM (opcional)
        re.MULTILINE | re.IGNORECASE,
    )
    for m in patron.finditer(texto):
        ident = m.group(1).strip().upper()
        fila = {
            "identificacion": ident,
            "rodeo": ident if ident.startswith("T") else None,
            "mg": _numero(m.group(2)),
            "proteina": _numero(m.group(3)),
            "lactosa": _numero(m.group(4)),
            "st": _numero(m.group(5)),
            "rcs": _numero(m.group(6)),
            "rm": _numero(m.group(7)),
            # Campos que no siempre vienen en texto plano
            "sng": None, "prov": None, "caseina": None,
            "mun": None, "crioscopía": None,
        }
        filas.append(fila)
    return filas


def _es_identificador(s: str) -> bool:
    if not s:
        return False
    if s in IDS_CONOCIDOS:
        return True
    if re.match(r"^T\d+$", s):   # T5, T6, etc.
        return True
    return False


def _mapear_columnas_tabla(ident: str, row: list) -> dict | None:
    """
    Mapea una fila de la tabla pdfplumber a un diccionario con nombres de campo.
    El orden de columnas en el informe LABVIMA es:
      [0]=Ident  [1]=M.G.  [2]=Prote  [3]=Lacto  [4]=SNG  [5]=ST
      [6]=Pro.V  [7]=Case.  [8]=MUN  [9]=Crioscopía  [10]=RCS  [11]=RM
    Pero a veces faltan columnas, así que usamos posición relativa con fallback.
    """
    # Limpiar la fila: quitar Nones y strings vacíos entre valores
    vals = [str(c).strip() if c else "" for c in row]

    def get(idx, default=None):
        if idx < len(vals):
            v = vals[idx]
            return _numero(v) if v else default
        return default

    return {
        "identificacion": ident,
        "rodeo": ident if ident.startswith("T") else None,
        "mg":        get(1),
        "proteina":  get(2),
        "lactosa":   get(3),
        "sng":       get(4),
        "st":        get(5),
        "prov":      get(6),
        "caseina":   get(7),
        "mun":       get(8),
        "crioscopía": get(9),
        "rcs":       get(10),
        "rm":        get(11),
    }


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Uso: python labvima_parser.py archivo.pdf")
        sys.exit(1)
    resultado = extraer_informe(sys.argv[1])
    resultado["fecha_proceso"] = str(resultado["fecha_proceso"])
    resultado["fecha_ingreso"] = str(resultado["fecha_ingreso"])
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
