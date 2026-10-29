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
# 1. AUTO-LIMPIEZA DE ARCHIVOS
# ==========================================
print("[1/4] Limpiando archivos e imágenes antiguas...")
if os.path.exists('imagenes'):
    shutil.rmtree('imagenes')
os.makedirs('imagenes')

if os.path.exists('productos.json'):
    os.remove('productos.json')

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
print("[2/4] Buscando todas las secciones, subcategorías y colecciones de Yupoo...")

secciones_a_escanear = set()

# A) Recoger todas las URLs de /categories y /collections
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

# B) Función para extraer los álbumes de una URL específica
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
print("[3/4] Rastreando páginas ilimitadas del catálogo principal y subsecciones...")

albumes_totales = []
urls_procesadas = set()

# 1. Escaneo dinámico del feed general (/albums?page=X) hasta que no haya más productos
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
            if href not in urls_procesadas:
                urls_procesadas.add(href)
                albumes_totales.append({
                    "titulo": titulo,
                    "imagen_url": img_src,
                    "url_yupoo": href
                })
                nuevos += 1
        print(f" -> Catálogo general - Página {pagina}: {nuevos} camisetas encontradas (Total: {len(albumes_totales)})")

    pagina += 1

# 2. Escaneo profundo paginado dentro de cada subcategoría descubierta
print("[+] Escaneando páginas internas dentro de cada categoría...")
for idx, sec_url in enumerate(secciones_a_escanear, 1):
    pag_sec = 1
    while True:
        target = f"{sec_url}&page={pag_sec}" if '?' in sec_url else f"{sec_url}?page={pag_sec}"
        items_sec = extraer_albumes_de_pagina(target)

        if not items_sec or pag_sec > 25:
            break

        for href, titulo, img_src in items_sec:
            if href not in urls_procesadas:
                urls_procesadas.add(href)
                albumes_totales.append({
                    "titulo": titulo,
                    "imagen_url": img_src,
                    "url_yupoo": href
                })

        pag_sec += 1

print(f"\n[+] ¡Rastreo exhaustivo completado! Se han localizado {len(albumes_totales)} equipaciones únicas de fútbol.")
print("[4/4] DESCARGA MÁXIMA VELOCIDAD: Procesando imágenes con 50 hilos en paralelo...")

# ==========================================
# 5. DESCARGA ULTRA-RÁPIDA MULTIHILO (50 HILOS)
# ==========================================
productos_finales = []

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

with ThreadPoolExecutor(max_workers=50) as executor:
    futures = [executor.submit(descargar_imagen_fast, i + 1, item) for i, item in enumerate(albumes_totales)]
    for i, future in enumerate(futures):
        res = future.result()
        if res:
            productos_finales.append(res)
        if (i + 1) % 200 == 0 or (i + 1) == len(albumes_totales):
            print(f" -> Progreso de descargas: {i + 1}/{len(albumes_totales)} completadas")

# Guardar catálogo completo
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_finales, f, ensure_ascii=False, indent=4)

print(f"\n[OK] ¡COMPLETADO EXHAUSTIVO! Se han guardado {len(productos_finales)} camisetas en 'productos.json'.")