import json
import os

print("[+] Comprimiendo catálogo de 22.000 camisetas para la web...")

if os.path.exists('productos.json'):
    with open('productos.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Convertir a claves de 1 sola letra para reducir el tamaño al máximo
    data_opt = []
    for item in data:
        data_opt.append({
            "id": item.get("id"),
            "t": item.get("titulo", ""),
            "i": item.get("imagen", ""),
            "u": item.get("url_yupoo", ""),
            "p": item.get("precio", "25.00€")
        })

    # Guardar en formato plano minificado
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(data_opt, f, ensure_ascii=False, separators=(',', ':'))

    peso_mb = os.path.getsize('productos.json') / (1024 * 1024)
    print(f"[OK] ¡Listo! Peso reducido a solo {peso_mb:.2f} MB.")
else:
    print("[!] No se encontró productos.json")