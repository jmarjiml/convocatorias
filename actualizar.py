import urllib.request
import urllib.parse
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

URL = "https://www.gobiernodecanarias.org/educacion/web/programas-redes-educativas/convocatorias/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def obtener_soup(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            return BeautifulSoup(html, 'html.parser'), html
    except Exception as e:
        print(f"Aviso: No se pudo analizar {url}: {e}")
        return None, ""

def determinar_estado_real(soup_pagina, html_pagina, titulo_link):
    if not soup_pagina:
        return "Matrícula abierta", "abierta", "⚡ Convocatoria publicada con plazo de inscripción activo."

    # 1. Aislar el contenido principal para ignorar menús y pies de página
    main_content = soup_pagina.find('main') or soup_pagina.find('article') or soup_pagina.find('body')
    texto_main = main_content.get_text(" ", strip=True).lower() if main_content else html_pagina.lower()

    # Extraer el texto de los enlaces adjuntos (resoluciones o PDFs publicados)
    enlaces_main = [a.get_text(strip=True).lower() for a in (main_content.find_all('a') if main_content else [])]
    texto_enlaces = " ".join(enlaces_main)

    # 2. Comprobar si hay una RESOLUCIÓN DEFINITIVA efectivamente publicada
    # (Buscamos enlaces específicos de resolución o menciones explícitas de listado definitivo adjunto)
    tiene_resolucion_definitiva = any(k in texto_enlaces for k in ['listado definitivo', 'resolución definitiva', 'resolucion definitiva', 'admitidos definitivos']) or \
                                   ('resolución' in texto_main and 'definitiv' in texto_main and ('publicación' in texto_main or 'admitidos' in texto_main))

    # 3. Comprobar si hay una RESOLUCIÓN PROVISIONAL efectivamente publicada
    tiene_resolucion_provisional = any(k in texto_enlaces for k in ['listado provisional', 'resolución provisional', 'resolucion provisional', 'admitidos provisionales']) or \
                                    ('resolución' in texto_main and 'provisional' in texto_main and ('reclamación' in texto_main or 'alegaciones' in texto_main))

    # 4. Comprobar si la convocatoria tiene la inscripción/solicitud activa
    tiene_solicitud_activa = any(k in texto_main for k in [
        'solicitud de participación', 'acceder al aplicativo', 'formulario de inscripción',
        'plazo de presentación', 'cumplimentar la solicitud', 'abierto el plazo'
    ]) or any('solicitud' in e or 'inscripción' in e or 'aplicativo' in e for e in enlaces_main)

    # REGLAS DE DECISIÓN DE ESTADO

    # A) Si ya existe un Listado Definitivo publicado y no hay nueva solicitud abierta
    if tiene_resolucion_definitiva and not tiene_solicitud_activa:
        return "Listado definitivo", "definitiva", "Listado definitivo publicado oficialmente en la sede."

    # B) Si ya existe un Listado Provisional publicado (y no el definitivo ni solicitud abierta)
    if tiene_resolucion_provisional and not tiene_resolucion_definitiva and not tiene_solicitud_activa:
        return "Lista provisional", "provisional", "Listado provisional publicado (periodo de alegaciones/reclamaciones abierto)."

    # C) Si el plazo o la solicitud están activos, o es una convocatoria nueva sin resoluciones aún
    if tiene_solicitud_activa or (not tiene_resolucion_provisional and not tiene_resolucion_definitiva):
        return "Matrícula abierta", "abierta", "⚡ Plazo de inscripción y entrega de solicitudes actualmente abierto."

    return "Plazo cerrado / Consulta", "otros", "Consulta las bases e instrucciones oficiales de la convocatoria."

def clasificar_area(texto):
    lower = texto.lower()
    if any(x in lower for x in ['steam', 'peter', 'idescubre', 'georrutas', 'robotica', 'ciencia', 'tecnologia', 'matemat']): return 'STEAM'
    if any(x in lower for x in ['podcaster', 'viera', 'zurron', 'lengua', 'lectura', 'radio', 'comunicacion', 'escritura']): return 'Comunicación lingüística'
    if any(x in lower for x in ['salud', 'solidarios', 'murgavalores', 'igualdad', 'plato', 'afectivo', 'deporte']): return 'Igualdad / Salud'
    if any(x in lower for x in ['natural', 'ambiental', 'clima', 'ecologia', 'sostenibilidad', 'biodiversidad']): return 'Educación Ambiental'
    return 'General'

def main():
    print("Iniciando análisis preciso de convocatorias...")
    soup_principal, html_principal = obtener_soup(URL)
    if not soup_principal:
        print("Error: No se pudo cargar la página principal.")
        return

    links = soup_principal.find_all('a', href=True)
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

        if any(k in lower_text for k in ['2026', 'proyecto', 'programa', 'convocatoria', 'curso']) and full_url not in vistos:
            vistos.add(full_url)
            print(f"[{posicion}] Analizando: {texto[:50]}...")
            
            soup_sub, html_sub = obtener_soup(full_url)
            estado, estado_clave, detalle = determinar_estado_real(soup_sub, html_sub, texto)
            tipo = clasificar_area(texto + " " + html_sub)

            convocatorias.append({
                "orden": posicion,
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

    print(f"Proceso completado con éxito. Se procesaron {len(convocatorias)} convocatorias.")

if __name__ == "__main__":
    main()
