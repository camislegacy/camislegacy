import os
import json
import time
import shutil
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# 1. CARGA DE PRODUCTOS EXISTENTES (EVITA BORRAR LO ANTERIOR)
# ==========================================
print("[1/4] Verificando catálogo existente para fusionar sin duplicados...")
if not os.path.exists('imagenes'):
    os.makedirs('imagenes')

productos_existentes = []
urls_existentes = set()
titulos_existentes = set()

if os.path.exists('productos.json'):
    try:
        with open('productos.json', 'r', encoding='utf-8') as f:
            productos_existentes = json.load(f)
            for p in productos_existentes:
                urls_existentes.add(p.get("url_yupoo"))
                titulos_existentes.add(p.get("titulo", "").strip().lower())
        print(f"[+] Se han cargado {len(productos_existentes)} productos previos en la memoria.")
    except Exception as e:
        print(f"[!] No se pudo leer el archivo productos.json anterior: {e}")

# Determinar el siguiente ID disponible para no pisar los contadores anteriores
next_id = max([p.get("id", 0) for p in productos_existentes], default=0) + 1

# ==========================================
# 2. CONFIGURACIÓN DE CONEXIONES Y SESIÓN
# ==========================================
base_url = "https://minkang.x.yupoo.com"

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=retries)
session.mount('http://', adapter)
session.mount('https://', adapter)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://minkang.x.yupoo.com/"
}
session.headers.update(headers)

# Descartar solo deportes ajenos y tablas de tallas solas
EXCLUIR_OTROS_DEPORTES = [
    "nba", "nfl", "nhl", "mlb", "f1", "formula 1", "formula1", "afl", "gaa",
    "shoes", "boots", "size chart", "size table"
]

def es_equipacion_valida(titulo):
    t = titulo.lower().strip()
    for excl in EXCLUIR_OTROS_DEPORTES:
        if excl in t:
            return False
    return True

# ==========================================
# 3. EXTRAER TODAS LAS RUTAS DE CATEGORÍAS Y COLECCIONES
# ==========================================
print("[2/4] Buscando secciones y colecciones nuevas en Yupoo...")

secciones_a_escanear = set()

for endpoint in ["/categories", "/collections"]:
    try:
        r = session.get(base_url + endpoint, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/categories/' in href or '/collections/' in href:
                    full_url = base_url + href if href.startswith('/') else href
                    secciones_a_escanear.add(full_url)
    except Exception as e:
        print(f"[!] Error leyendo {endpoint}: {e}")

print(f"[+] Se han descubierto {len(secciones_a_escanear)} subcategorías internas.")

def extraer_albumes_de_pagina(url):
    try:
        r = session.get(url, timeout=10)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, 'html.parser')
        elementos = soup.select('a.album__main') or soup.select('.showindex_main_a')

        resultados = []
        for el in elementos:
            href = el.get('href', '')
            if '/albums/' not in href:
                continue

            titulo = (el.get('title') or el.text).strip()
            titulo = " ".join(titulo.split())

            if not titulo or len(titulo) < 3 or not es_equipacion_valida(titulo):
                continue

            full_href = base_url + href if href.startswith('/') else href

            img = el.find('img')
            img_src = ""
            if img:
                img_src = img.get('data-src') or img.get('data-origin-src') or img.get('src') or ""
                if img_src.startswith('//'):
                    img_src = "https:" + img_src

            if img_src:
                resultados.append((full_href, titulo, img_src))

        return resultados
    except Exception:
        return []

# ==========================================
# 4. ESCANEO DINÁMICO E INFINITO DE PÁGINAS
# ==========================================
print("[3/4] Rastreando el catálogo para incorporar novedades...")

albumes_nuevos_detectados = []
urls_procesadas_sesion = set()

# 1. Escaneo dinámico del feed general
pagina = 1
vacias_seguidas = 0

while True:
    url_general = f"{base_url}/albums?page={pagina}"
    items = extraer_albumes_de_pagina(url_general)

    if not items:
        vacias_seguidas += 1
        if vacias_seguidas >= 3:
            print(f" -> Fin del catálogo general en la página {pagina - vacias_seguidas}.")
            break
    else:
        vacias_seguidas = 0
        nuevos = 0
        for href, titulo, img_src in items:
            # Comprobamos que no esté ya en la sesión ni en el json antiguo guardado
            if href not in urls_existentes and href not in urls_procesadas_sesion and titulo.lower() not in titulos_existentes:
                urls_procesadas_sesion.add(href)
                albumes_nuevos_detectados.append({
                    "titulo": titulo,
                    "imagen_url": img_src,
                    "url_yupoo": href
                })
                nuevos += 1
        print(f" -> Catálogo general - Página {pagina}: {nuevos} camisetas nuevas detectadas.")

    pagina += 1

# 2. Escaneo profundo en subcategorías
print("[+] Comprobando novedades dentro de cada subcategoría...")
for idx, sec_url in enumerate(secciones_a_escanear, 1):
    pag_sec = 1
    while True:
        target = f"{sec_url}&page={pag_sec}" if '?' in sec_url else f"{sec_url}?page={pag_sec}"
        items_sec = extraer_albumes_de_pagina(target)

        if not items_sec or pag_sec > 25:
            break

        for href, titulo, img_src in items_sec:
            if href not in urls_existentes and href not in urls_procesadas_sesion and titulo.lower() not in titulos_existentes:
                urls_procesadas_sesion.add(href)
                albumes_nuevos_detectados.append({
                    "titulo": titulo,
                    "imagen_url": img_src,
                    "url_yupoo": href
                })

        pag_sec += 1

print(f"\n[+] ¡Rastreo completado! Se han encontrado {len(albumes_nuevos_detectados)} camisetas nuevas que no estaban guardadas.")
print(f"[4/4] DESCARGA DE NOVEDADES: Procesando imágenes nuevas...")

# ==========================================
# 5. DESCARGA Y FUSIÓN DE NUEVOS PRODUCTOS
# ==========================================
nuevos_productos_guardados = []

def descargar_imagen_fast(index, item):
    ruta_local = f"imagenes/camiseta_{index}.jpg"
    try:
        res = session.get(item["imagen_url"], timeout=8)
        if res.status_code == 200:
            with open(ruta_local, 'wb') as f:
                f.write(res.content)
            return {
                "id": index,
                "titulo": item["titulo"],
                "imagen": ruta_local,
                "url_yupoo": item["url_yupoo"],
                "precio": "25.00€"
            }
    except Exception:
        pass
    return None

if albumes_nuevos_detectados:
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(descargar_imagen_fast, next_id + i, item) for i, item in enumerate(albumes_nuevos_detectados)]
        for i, future in enumerate(futures):
            res = future.result()
            if res:
                nuevos_productos_guardados.append(res)
            if (i + 1) % 100 == 0 or (i + 1) == len(albumes_nuevos_detectados):
                print(f" -> Progreso descargas nuevas: {i + 1}/{len(albumes_nuevos_detectados)}")

# Fusionar antiguos con los nuevos descargados
catalogo_final_fusionado = productos_existentes + nuevos_productos_guardados

# Guardar catálogo completo actualizado en productos.json
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(catalogo_final_fusionado, f, ensure_ascii=False, indent=4)

print(f"\n[OK] ¡FUSIÓN COMPLETADA! Catálogo total actualizado con {len(catalogo_final_fusionado)} camisetas en 'productos.json'.")