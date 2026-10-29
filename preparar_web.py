import json
import os

print("[+] Convirtiendo catálogo a productos.js para carga directa e instantánea...")

if os.path.exists('productos.json'):
    with open('productos.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Estructura ultra-comprimida
    data_opt = []
    for item in data:
        data_opt.append({
            "id": item.get("id"),
            "t": item.get("titulo", ""),
            "i": item.get("imagen", ""),
            "u": item.get("url_yupoo", ""),
            "p": item.get("precio", "25.00€")
        })

    # Guardar como variable JavaScript directa
    js_content = "window.TODOS_LOS_PRODUCTOS = " + json.dumps(data_opt, ensure_ascii=False, separators=(',', ':')) + ";"
    
    with open('productos.js', 'w', encoding='utf-8') as f:
        f.write(js_content)

    peso_mb = os.path.getsize('productos.js') / (1024 * 1024)
    print(f"[OK] ¡Generado productos.js ({peso_mb:.2f} MB)! Ya puedes hacer doble clic en index.html.")
else:
    print("[!] No se encontró productos.json")