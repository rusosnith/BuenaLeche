"""
labvima_sync.py
---------------
Script principal — versión Google Sheets.
Hace login al portal de LABVIMA, detecta informes nuevos,
los descarga en PDF, los parsea y vuelca los datos al Google Sheet.

Uso:
    python labvima_sync.py                    → sincroniza informes nuevos
    python labvima_sync.py --pdf archivo.pdf  → procesa un PDF local
"""

import os
import sys
import argparse
import re
import time
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from labvima_parser import extraer_informe
from gsheets_updater import conectar, actualizar_sheet


# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL  = "http://190.105.213.89/administracion"
LOGIN_URL = f"{BASE_URL}/index.php"
TIMEOUT   = 30
DELAY     = 1.5

_DIR_SCRIPT = Path(__file__).parent
_ENV_PATH   = _DIR_SCRIPT / "config.env"


def cargar_config() -> dict:
    load_dotenv(_ENV_PATH)
    cfg = {
        "usuario":      os.getenv("LABVIMA_USUARIO", "").strip(),
        "clave":        os.getenv("LABVIMA_CLAVE", "").strip(),
        "sheet_url":    os.getenv("SHEET_URL", "").strip(),
        "sheet_nombre": os.getenv("SHEET_NOMBRE", "Registro_Calidad").strip(),
        "credentials":  os.getenv("GOOGLE_CREDENTIALS_JSON", "credenciales_google.json").strip(),
        "pdf_folder":   os.getenv("PDF_FOLDER", "./pdfs_labvima").strip(),
    }

    errores = []
    if not cfg["usuario"]:
        errores.append("LABVIMA_USUARIO no configurado en config.env")
    if not cfg["clave"]:
        errores.append("LABVIMA_CLAVE no configurada en config.env")
    if not cfg["sheet_url"] or "TU_ID_AQUI" in cfg["sheet_url"]:
        errores.append("SHEET_URL no configurada en config.env")

    cred_path = _DIR_SCRIPT / cfg["credentials"]
    if not cred_path.exists():
        errores.append(
            f"Archivo de credenciales Google no encontrado: {cred_path}\n"
            "  → Seguí los pasos del LEEME.txt para generarlo."
        )
    else:
        cfg["credentials"] = str(cred_path)

    if errores:
        print("\n  ✗ Configuración incompleta:")
        for e in errores:
            print(f"    • {e}")
        print(f"\n  → Editá: {_ENV_PATH}")
        sys.exit(1)

    pdf_folder = Path(cfg["pdf_folder"])
    if not pdf_folder.is_absolute():
        pdf_folder = (_DIR_SCRIPT / pdf_folder).resolve()
    pdf_folder.mkdir(parents=True, exist_ok=True)
    cfg["pdf_folder"] = pdf_folder

    return cfg


# ── Login al portal LABVIMA ──────────────────────────────────────────────────
def crear_sesion(usuario: str, clave: str) -> requests.Session:
    sesion = requests.Session()
    sesion.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/125.0 Safari/537.36",
        "Referer": LOGIN_URL,
    })

    print("  Conectando al portal LABVIMA...")
    resp = sesion.get(LOGIN_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form")

    if form:
        campos = _detectar_campos_login(form, usuario, clave)
        action = form.get("action") or LOGIN_URL
        if not action.startswith("http"):
            action = f"{BASE_URL}/{action.lstrip('/')}"
        method = (form.get("method") or "post").lower()
    else:
        print("  ⚠  Formulario no detectado, usando campos por defecto...")
        campos = {"usuario": usuario, "clave": clave}
        action = LOGIN_URL
        method = "post"

    resp = sesion.request(method, action, data=campos, timeout=TIMEOUT)
    resp.raise_for_status()

    if _login_exitoso(resp.text):
        print("  ✓ Login exitoso en LABVIMA")
        return sesion
    else:
        print("\n  ✗ Login fallido. Verificá usuario y clave en config.env")
        _guardar_debug(resp.text, "debug_login.html")
        sys.exit(1)


def _detectar_campos_login(form, usuario, clave):
    campos = {}
    inputs = form.find_all("input")
    for inp in inputs:
        if (inp.get("type") or "").lower() == "hidden":
            campos[inp.get("name", "")] = inp.get("value", "")

    campo_usuario = campo_clave = None
    for inp in inputs:
        tipo    = (inp.get("type") or "text").lower()
        nombre  = (inp.get("name") or "").lower()
        id_     = (inp.get("id") or "").lower()
        hint    = nombre + id_
        if tipo in ("text", "") and not campo_usuario:
            campo_usuario = inp.get("name")
        if tipo == "password" and not campo_clave:
            campo_clave = inp.get("name")

    if campo_usuario:
        campos[campo_usuario] = usuario
    if campo_clave:
        campos[campo_clave] = clave

    print(f"    Campos detectados: '{campo_usuario}' / '{campo_clave}'")
    return campos


def _login_exitoso(html: str) -> bool:
    html_l = html.lower()
    exito  = sum(1 for k in ["logout", "salir", "resultado", "informe", "consulta", "bienvenido"] if k in html_l)
    return exito >= 2


# ── Navegación y descarga ────────────────────────────────────────────────────
def obtener_lista_informes(sesion: requests.Session) -> list[dict]:
    print("  Buscando informes disponibles...")

    candidatos = [
        f"{BASE_URL}/resultados.php",
        f"{BASE_URL}/consulta.php",
        f"{BASE_URL}/informes.php",
        f"{BASE_URL}/menu.php",
        f"{BASE_URL}/principal.php",
        f"{BASE_URL}/inicio.php",
    ]

    for url in candidatos:
        try:
            r = sesion.get(url, timeout=TIMEOUT)
            if r.status_code != 200 or len(r.text) < 500:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            links = soup.find_all("a", href=True)
            tiene = any(
                any(k in l["href"].lower() for k in [".pdf", "informe", "protocolo", "resultado"])
                for l in links
            )
            if tiene or "informe" in r.text.lower():
                print(f"    → Resultados en: {url}")
                _guardar_debug(soup.prettify(), "debug_resultados.html")
                return _parsear_lista(soup, url)
        except Exception:
            continue

    print("  ⚠  No se encontró la página de resultados automáticamente.")
    print("     Se generó debug_post_login.html — mandámelo para ajustar el script.")
    try:
        r = sesion.get(f"{BASE_URL}/", timeout=TIMEOUT)
        _guardar_debug(r.text, "debug_post_login.html")
    except Exception:
        pass
    return []


def _parsear_lista(soup: BeautifulSoup, base_url: str) -> list[dict]:
    informes = []
    for link in soup.find_all("a", href=True):
        href  = link["href"]
        texto = link.get_text(strip=True)
        if href.lower().endswith(".pdf"):
            informes.append({"protocolo": _num(href) or _num(texto), "url_pdf": _abs(href, base_url), "url_pagina": None, "texto": texto})
        elif any(k in href.lower() for k in ["informe", "resultado", "protocolo", "id="]):
            informes.append({"protocolo": _num(href) or _num(texto), "url_pdf": None, "url_pagina": _abs(href, base_url), "texto": texto})

    if not informes:
        for row in soup.find_all("tr"):
            numeros = [_num(c.get_text()) for c in row.find_all(["td","th"]) if _num(c.get_text())]
            for l in row.find_all("a", href=True):
                if numeros:
                    href = l["href"]
                    informes.append({
                        "protocolo": numeros[0],
                        "url_pdf":   _abs(href, base_url) if ".pdf" in href.lower() else None,
                        "url_pagina": _abs(href, base_url) if ".pdf" not in href.lower() else None,
                        "texto": l.get_text(strip=True),
                    })
    print(f"    → {len(informes)} informe(s) encontrado(s)")
    return informes


def descargar_pdf(sesion: requests.Session, info: dict, pdf_folder: Path) -> Path | None:
    protocolo = info.get("protocolo") or "sin_protocolo"
    pdf_path  = pdf_folder / f"LABVIMA_{protocolo}.pdf"

    if pdf_path.exists():
        print(f"    → PDF {protocolo} ya descargado, reutilizando.")
        return pdf_path

    url_pdf = info.get("url_pdf")

    if not url_pdf and info.get("url_pagina"):
        try:
            r    = sesion.get(info["url_pagina"], timeout=TIMEOUT)
            soup = BeautifulSoup(r.text, "html.parser")
            for l in soup.find_all("a", href=True):
                if ".pdf" in l["href"].lower():
                    url_pdf = _abs(l["href"], info["url_pagina"])
                    break
            if not url_pdf:
                for iframe in soup.find_all("iframe", src=True):
                    if ".pdf" in iframe["src"].lower():
                        url_pdf = _abs(iframe["src"], info["url_pagina"])
                        break
        except Exception as e:
            print(f"    ⚠  Error buscando PDF: {e}")
            return None

    if not url_pdf:
        print(f"    ⚠  Sin URL de PDF para protocolo {protocolo}")
        return None

    try:
        r = sesion.get(url_pdf, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        with open(pdf_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"    ✓ Descargado: {pdf_path.name}")
        return pdf_path
    except Exception as e:
        print(f"    ✗ Error descargando PDF: {e}")
        return None


# ── Utilidades ───────────────────────────────────────────────────────────────
def _num(texto: str):
    if not texto:
        return None
    m = re.search(r"\d{5,}", str(texto))
    return int(m.group()) if m else None


def _abs(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        from urllib.parse import urlparse
        p = urlparse(base)
        return f"{p.scheme}://{p.netloc}{href}"
    return f"{base.rsplit('/', 1)[0]}/{href}"


def _guardar_debug(contenido: str, nombre: str):
    try:
        with open(_DIR_SCRIPT / nombre, "w", encoding="utf-8", errors="replace") as f:
            f.write(contenido)
    except Exception:
        pass


# ── Flujo principal ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=str, help="Procesa un PDF local sin conectarse al portal")
    args = parser.parse_args()

    print("\n" + "═"*55)
    print("  LABVIMA → Google Sheets   |   Cabaña San Roque")
    print(f"  {datetime.now().strftime('%d/%m/%Y  %H:%M')}")
    print("═"*55)

    cfg = cargar_config()

    # Conectar al Sheet
    print(f"\n  Conectando a Google Sheets...")
    try:
        ws = conectar(cfg["credentials"], cfg["sheet_url"], cfg["sheet_nombre"])
        print(f"  ✓ Conectado a hoja '{cfg['sheet_nombre']}'")
    except Exception as e:
        print(f"\n  ✗ Error conectando al Sheet: {e}")
        sys.exit(1)

    # ── Modo PDF local ────────────────────────────────────────────────────
    if args.pdf:
        print(f"\n  Procesando PDF local: {args.pdf}")
        _procesar_pdf(args.pdf, ws)
        print("\n" + "═"*55)
        return

    # ── Modo web ──────────────────────────────────────────────────────────
    print()
    sesion   = crear_sesion(cfg["usuario"], cfg["clave"])
    time.sleep(DELAY)
    informes = obtener_lista_informes(sesion)

    if not informes:
        print("\n  Sin informes nuevos para procesar.")
        print("═"*55)
        return

    total_agg = total_omi = errores = 0

    for info in informes:
        time.sleep(DELAY)
        print(f"\n  ── Protocolo {info.get('protocolo','?')} ──")
        pdf_path = descargar_pdf(sesion, info, cfg["pdf_folder"])
        if not pdf_path:
            errores += 1
            continue
        agg, omi = _procesar_pdf(str(pdf_path), ws)
        total_agg += agg
        total_omi += omi

    print("\n" + "═"*55)
    print(f"  Informes procesados : {len(informes) - errores}")
    print(f"  Filas nuevas        : {total_agg}")
    print(f"  Ya existentes       : {total_omi}")
    if errores:
        print(f"  Errores             : {errores}")
    print("═"*55 + "\n")


def _procesar_pdf(pdf_path: str, ws) -> tuple[int, int]:
    try:
        informe = extraer_informe(pdf_path)
        fecha   = informe["fecha_proceso"] or informe["fecha_ingreso"]
        print(f"    Nº {informe['nro_informe']}  |  Fecha: {fecha}  |  {len(informe['filas'])} registros")
        for f in informe["filas"]:
            print(f"      {f['identificacion']:5}  MG={f.get('mg')}  Prot={f.get('proteina')}  ST={f.get('st')}  RCS={f.get('rcs')}  RM={f.get('rm')}")
        agg, omi = actualizar_sheet(ws, informe)
        print(f"    → {agg} fila(s) nuevas cargadas, {omi} ya existían.")
        return agg, omi
    except Exception as e:
        print(f"    ✗ Error procesando {pdf_path}: {e}")
        return 0, 0


if __name__ == "__main__":
    main()
