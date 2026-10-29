import json
import os

print("[+] Reconstruyendo productos.js con títulos e imágenes reales...")

if os.path.exists('productos.json'):
    with open('productos.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    data_opt = []
    for item in data:
        # Recupera los datos sea cual sea el nombre de la clave
        titulo = item.get("titulo") or item.get("t") or ""
        imagen = item.get("imagen") or item.get("i") or ""
        url_yupoo = item.get("url_yupoo") or item.get("u") or ""
        precio = item.get("precio") or item.get("p") or "25.00€"

        data_opt.append({
            "id": item.get("id"),
            "t": titulo,
            "i": imagen,
            "u": url_yupoo,
            "p": precio
        })

    # Guardar variable JS global
    js_content = "window.TODOS_LOS_PRODUCTOS = " + json.dumps(data_opt, ensure_ascii=False, separators=(',', ':')) + ";"
    
    with open('productos.js', 'w', encoding='utf-8') as f:
        f.write(js_content)

    peso_mb = os.path.getsize('productos.js') / (1024 * 1024)
    print(f"[OK] ¡REPARADO! productos.js generado correctamente ({peso_mb:.2f} MB).")
else:
    print("[!] No se encontró productos.json")