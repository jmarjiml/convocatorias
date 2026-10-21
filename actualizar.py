import urllib.request
import urllib.parse
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

URL = "https://www.gobiernodecanarias.org/educacion/web/programas-redes-educativas/convocatorias/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def obtener_html(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Aviso: No se pudo analizar en detalle {url}: {e}")
        return ""

def determinar_estado_real(texto_completo, html_pagina):
    lower_texto = texto_completo.lower()
    lower_html = html_pagina.lower() if html_pagina else ""
    todo = lower_texto + " " + lower_html

    # 1. Comprobar si existe Listado Definitivo
    if any(k in todo for k in [
        'listado definitivo', 'resolución definitiva', 'resolucion definitiva', 
        'centros admitidos de forma definitiva', 'adjudicación definitiva', 'admitidos definitivos'
    ]):
        return "Listado definitivo", "definitiva", "Listado definitivo publicado oficialmente en la sede."

    # 2. Comprobar si existe Listado Provisional
    if any(k in todo for k in [
        'listado provisional', 'resolución provisional', 'resolucion provisional', 
        'admitidos provisionalmente', 'plazo de reclamación', 'periodo de alegaciones'
    ]):
        return "Lista provisional", "provisional", "Listado provisional publicado (periodo de reclamaciones o alegaciones)."

    # 3. Comprobar si la matrícula/solicitud está Abierta
    palabras_abiertas = [
        'plazo de presentación', 'solicitud de participación', 'plazo de inscripción', 
        'cumplimentar la solicitud', 'acceder a la solicitud', 'periodo de solicitud', 
        'plazo abierto', 'abierto el plazo'
    ]
    palabras_cerradas = [
        'plazo finalizado', 'plazo cerrado', 'finalizado el plazo', 
        'fuera de plazo', 'solicitud cerrada', 'plazo de solicitud finalizado'
    ]

    esta_cerrado = any(k in todo for k in palabras_cerradas)
    tiene_indicador_abierto = any(k in todo for k in palabras_abiertas)

    if tiene_indicador_abierto and not esta_cerrado:
        return "Matrícula abierta", "abierta", "⚡ Plazo de inscripción y entrega de solicitudes actualmente abierto."

    if esta_cerrado:
        return "Plazo cerrado", "otros", "El plazo de presentación de solicitudes ha finalizado."

    return "Instrucciones / Consulta", "otros", "Consulta las bases e instrucciones de la convocatoria."

def clasificar_area(texto):
    lower = texto.lower()
    if any(x in lower for x in ['steam', 'peter', 'idescubre', 'georrutas', 'robotica', 'ciencia', 'tecnologia', 'matemat']): return 'STEAM'
    if any(x in lower for x in ['podcaster', 'viera', 'zurron', 'lengua', 'lectura', 'radio', 'comunicacion', 'escritura']): return 'Comunicación lingüística'
    if any(x in lower for x in ['salud', 'solidarios', 'murgavalores', 'igualdad', 'plato', 'afectivo', 'deporte']): return 'Igualdad / Salud'
    if any(x in lower for x in ['natural', 'ambiental', 'clima', 'ecologia', 'sostenibilidad', 'biodiversidad']): return 'Educación Ambiental'
    return 'General'

def main():
    print("Iniciando análisis de convocatorias ordenadas por novedad...")
    html_principal = obtener_html(URL)
    if not html_principal:
        print("Error: No se pudo cargar la página principal.")
        return

    soup = BeautifulSoup(html_principal, 'html.parser')
    links = soup.find_all('a', href=True)
    
    convocatorias = []
    vistos = set()
    posicion = 1

    for a in links:
        texto = a.get_text(strip=True)
        href = a['href']

        if not texto or len(texto) < 10 or href.startswith('#') or 'javascript:' in href:
            continue

        full_url = href if href.startswith('http') else urllib.parse.urljoin(URL, href)
        lower_text = texto.lower()

        # Filtrar enlaces relevantes preservando el orden de publicación
        if any(k in lower_text for k in ['2026', 'proyecto', 'programa', 'convocatoria', 'curso']) and full_url not in vistos:
            vistos.add(full_url)
            print(f"[{posicion}] Analizando: {texto[:50]}...")
            
            sub_html = obtener_html(full_url)
            estado, estado_clave, detalle = determinar_estado_real(texto, sub_html)
            tipo = clasificar_area(texto + " " + sub_html)

            convocatorias.append({
                "orden": posicion,  # Posición 1 = la más reciente
                "titulo": texto.replace('\n', ' ').strip(),
                "url": full_url,
                "curso": "2026-2027",
                "tipo": tipo,
                "fuente": "Gobierno de Canarias",
                "estado": estado,
                "estadoClave": estado_clave,
                "detalle": detalle
            })
            posicion += 1

    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    resultado = {
        "updated": fecha_actual,
        "data": convocatorias
    }

    with open('convocatorias.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Completado: {len(convocatorias)} convocatorias ordenadas por recencia.")

if __name__ == "__main__":
    main()
