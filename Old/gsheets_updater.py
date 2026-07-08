"""
gsheets_updater.py
------------------
Vuelca los datos parseados de un informe LABVIMA a la hoja
"Registro_Calidad" de un Google Sheet.
Evita duplicados chequeando Nº de informe + Identificación.
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import date


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Encabezados de la hoja — en este orden exacto
HEADERS = [
    "Fecha",
    "Nº Informe LABVIMA",
    "Identificación",
    "Rodeo",
    "M.G. (g/100ml)",
    "Proteína (g/100ml)",
    "Lactosa (g/100ml)",
    "SNG (g/100ml)",
    "ST (g/100ml)",
    "Pro.V (g/100ml)",
    "Caseína (g/100ml)",
    "MUN (mg/dl)",
    "Crioscopía (mºC)",
    "RCS (cél/ml x1000)",
    "RM (ufc/ml x1000)",
    "Observaciones",
]

# Índices (0-based) de las columnas clave para dedup
COL_NRO   = 1   # Nº Informe
COL_IDENT = 2   # Identificación


def conectar(credentials_path: str, sheet_url: str, sheet_nombre: str):
    """
    Devuelve (worksheet, gspread_client).
    Crea la hoja con encabezados si no existe.
    """
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    gc = gspread.authorize(creds)

    try:
        spreadsheet = gc.open_by_url(sheet_url)
    except gspread.exceptions.NoValidUrlKeyFound:
        raise ValueError(
            f"URL del Sheet inválida: {sheet_url}\n"
            "Verificá que SHEET_URL en config.env sea la URL completa del spreadsheet."
        )
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(
            "No se encontró el spreadsheet. Verificá que:\n"
            "  1. La URL en config.env sea correcta\n"
            "  2. Hayas compartido el Sheet con el email de la cuenta de servicio"
        )

    # Buscar la hoja (pestaña) por nombre, o crearla
    try:
        ws = spreadsheet.worksheet(sheet_nombre)
    except gspread.exceptions.WorksheetNotFound:
        print(f"  → Creando hoja '{sheet_nombre}'...")
        ws = spreadsheet.add_worksheet(title=sheet_nombre, rows=2000, cols=len(HEADERS))
        _inicializar_hoja(ws)

    # Verificar que tenga encabezados; si está vacía, inicializar
    primera_fila = ws.row_values(1)
    if not primera_fila or primera_fila[0] != "Fecha":
        print(f"  → Inicializando encabezados en '{sheet_nombre}'...")
        _inicializar_hoja(ws)

    return ws


def _inicializar_hoja(ws):
    """Escribe los encabezados y formatea la primera fila."""
    ws.update("A1", [HEADERS])
    # Negrita en la primera fila
    ws.format("A1:P1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.122, "green": 0.306, "blue": 0.471},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER",
    })


def actualizar_sheet(ws, informe: dict) -> tuple[int, int]:
    """
    Agrega las filas del informe al Sheet.
    Retorna (filas_agregadas, filas_omitidas_por_duplicado).
    """
    # Traer todos los datos existentes para chequear duplicados
    todos = ws.get_all_values()
    existentes = _obtener_existentes(todos)

    nro = informe["nro_informe"]
    fecha = informe["fecha_proceso"] or informe["fecha_ingreso"]
    fecha_str = fecha.strftime("%d/%m/%Y") if fecha else ""

    filas_nuevas = []
    omitidas = 0

    for fila in informe["filas"]:
        clave = (str(nro), fila["identificacion"].upper())
        if clave in existentes:
            omitidas += 1
            continue

        fila_sheet = [
            fecha_str,
            nro,
            fila["identificacion"],
            fila.get("rodeo") or "",
            _v(fila.get("mg")),
            _v(fila.get("proteina")),
            _v(fila.get("lactosa")),
            _v(fila.get("sng")),
            _v(fila.get("st")),
            _v(fila.get("prov")),
            _v(fila.get("caseina")),
            _v(fila.get("mun")),
            _v(fila.get("crioscopía")),
            _v(fila.get("rcs")),
            _v(fila.get("rm")),
            "",   # Observaciones
        ]
        filas_nuevas.append(fila_sheet)
        existentes.add(clave)

    if filas_nuevas:
        ws.append_rows(filas_nuevas, value_input_option="USER_ENTERED")

    return len(filas_nuevas), omitidas


def _obtener_existentes(todas_las_filas: list) -> set:
    """Devuelve un set de (nro_informe_str, identificacion_upper) ya presentes."""
    existentes = set()
    for fila in todas_las_filas[1:]:   # saltar header
        if len(fila) > COL_IDENT:
            nro   = str(fila[COL_NRO]).strip()
            ident = str(fila[COL_IDENT]).strip().upper()
            if nro and ident:
                existentes.add((nro, ident))
    return existentes


def _v(val):
    """Convierte None a string vacío, deja los números como están."""
    if val is None:
        return ""
    return val
