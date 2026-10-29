import json
import os

print("[+] Ejecutando LIMPIEZA COMPLETA (Portadas de carpetas + Logos de ligas)...")

# Lista unificada de todas las portadas, logos, banners y tablas de tallas
PORTADAS_Y_LOGOS = {
    # 1. Portadas de categorías y prendas generales
    "long-sleeve shirt", "kids kit shirt", "retro shirt", "windbreaker/training top",
    "player version", "woman shirt", "training suit kit", "shorts", "polo shirt",
    "baby jersey", "sports socks", "panties", "football boots logo", "sports shoes",
    "nrl", "nba", "nfl", "nhl", "afl", "gaa", "f1", "size chart", "size table",
    "sizing", "table", "menu 1", "menu 2",
    
    # 2. Logos de ligas y banners de competiciones
    "brasileiro série a", "brasileiro serie a", "premier league", "la liga",
    "bundesliga", "serie a", "ligue 1", "primeira liga", "chilean league",
    "scottish league", "mls", "saf", "eredivisie", "liga mx", "saudi league",
    "super lig", "j1 league", "k league", "greek league", "belgian league",
    "russian premier league", "swiss super league", "austrian bundesliga",
    "national team", "national teams", "world cup", "euro cup", "copa america",
    "champions league", "europa league", "conference league", "libertadores",
    "other league", "others league", "special edition", "concept edition"
}

if os.path.exists('productos.json'):
    with open('productos.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    data_limpia = []
    eliminados = 0

    for item in data:
        titulo_orig = item.get("titulo") or item.get("t") or ""
        titulo_clean = titulo_orig.strip().lower()

        # Filtrar si coincide con alguna portada de carpeta o logo de liga
        if titulo_clean in PORTADAS_Y_LOGOS:
            eliminados += 1
            continue

        data_limpia.append({
            "id": item.get("id"),
            "t": titulo_orig,
            "i": item.get("imagen") or item.get("i") or "",
            "u": item.get("url_yupoo") or item.get("u") or "",
            "p": item.get("precio") or item.get("p") or "25.00€"
        })

    # Guardar cambios en productos.json
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(data_limpia, f, ensure_ascii=False, separators=(',', ':'))

    # Reconstruir productos.js para la web
    js_content = "window.TODOS_LOS_PRODUCTOS = " + json.dumps(data_limpia, ensure_ascii=False, separators=(',', ':')) + ";"
    with open('productos.js', 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"[OK] ¡Limpieza total completada! Se han eliminado {eliminados} elementos inservibles.")
    print(f"[+] Quedan {len(data_limpia)} camisetas reales listas en la web.")
else:
    print("[!] No se encontró productos.json")