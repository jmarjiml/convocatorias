import urllib.request
import urllib.parse
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

URL = "https://www.gobiernodecanarias.org/educacion/web/programas-redes-educativas/convocatorias/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def obtener_soup(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8', errors='ignore')
            return BeautifulSoup(html, 'html.parser'), html
    except Exception as e:
        print(f"Error accediendo a {url}: {e}")
        return None, ""

def calcular_dias_habiles(fecha_inicio, dias_habiles):
    # Calcula la fecha límite sumando días hábiles (excluyendo sábados y domingos)
    cur = fecha_inicio
    added = 0
    while added < dias_habiles:
        cur += timedelta(days=1)
        if cur.weekday() < 5:  # Lunes a Viernes
            added += 1
    return cur

def determinar_estado_automatico(soup, html_pagina, titulo_link):
    if not soup:
        return "Matrícula abierta", "abierta", "⚡ Convocatoria publicada."

    main = soup.find('main') or soup.find('article') or soup.find('body')
    if not main:
        return "Matrícula abierta", "abierta", "⚡ Convocatoria publicada."

    # 1. ANALIZAR EL TITULAR SUPERIOR DE LA PUBLICACIÓN (h1, h2, h3 y primeros párrafos)
    # Si la Consejería publicó un listado, el título superior o la resolución lo indican explícitamente
    primeros_encabezados = main.find_all(['h1', 'h2', 'h3', 'a'], limit=5)
    texto_titulos = " ".join([h.get_text(" ", strip=True).lower() for h in primeros_encabezados])
    
    primeros_p = main.find_all('p', limit=4)
    texto_resolucion = " ".join([p.get_text(" ", strip=True).lower() for p in primeros_p])

    cabecera_completa = texto_titulos + " " + texto_resolucion

    # A) ¿El titular superior indica Listado Definitivo?
    if 'listado definitivo' in cabecera_completa or 'resolución definitiva' in cabecera_completa or 'resolucion definitiva' in cabecera_completa:
        return "Listado definitivo", "definitiva", "Listado definitivo publicado mediante resolución oficial."

    # B) ¿El titular superior indica Listado Provisional?
    if 'listado provisional' in cabecera_completa or 'resolución provisional' in cabecera_completa or 'resolucion provisional' in cabecera_completa:
        return "Lista provisional", "provisional", "Listado provisional publicado (periodo de reclamaciones/alegaciones)."

    # 2. CÁLCULO MATEMÁTICO DE FECHAS (Extraer Fecha de publicación y Días hábiles)
    texto_pagina = main.get_text(" ", strip=True)
    
    match_fecha = re.search(r'Fecha de publicación:\s*(\d{2}/\d{2}/\d{4})', texto_pagina, re.IGNORECASE)
    match_dias = re.search(r'(\d+)\s*días hábiles', texto_pagina, re.IGNORECASE)

    hoy = datetime.now()

    if match_fecha:
        try:
            fecha_pub = datetime.strptime(match_fecha.group(1), "%d/%m/%Y")
            dias_hab = int(match_dias.group(1)) if match_dias else 10
            fecha_limite = calcular_dias_habiles(fecha_pub, dias_hab)

            # Si la fecha actual no ha superado el plazo computable de días hábiles
            if hoy.date() <= fecha_limite.date():
                return "Matrícula abierta", "abierta", f"⚡ Plazo de inscripción abierto hasta el {fecha_limite.strftime('%d/%m/%Y')}."
            else:
                return "Plazo cerrado", "otros", f"Plazo finalizado el {fecha_limite.strftime('%d/%m/%Y')} (en baremación)."
        except Exception as e:
            print(f"Error parseando fechas: {e}")

    # 3. VERIFICAR BOTÓN ACTIVO "Acceder a la SOLICITUD"
    tiene_boton_solicitud = any('solicitud' in a.get_text().lower() or 'aplicativo' in a.get_text().lower() for a in main.find_all('a'))
    if tiene_boton_solicitud:
        return "Matrícula abierta", "abierta", "⚡ Plazo de inscripción y entrega de solicitudes abierto."

    return "Instrucciones / Consulta", "otros", "Consulta las bases e instrucciones oficiales."

def clasificar_area(texto):
    lower = texto.lower()
    if any(x in lower for x in ['steam', 'peter', 'idescubre', 'georrutas', 'robotica', 'ciencia', 'tecnologia', 'matemat']): return 'STEAM'
    if any(x in lower for x in ['podcaster', 'viera', 'zurron', 'lengua', 'lectura', 'radio', 'comunicacion', 'escritura']): return 'Comunicación lingüística'
    if any(x in lower for x in ['salud', 'solidarios', 'murgavalores', 'igualdad', 'plato', 'afectivo', 'deporte']): return 'Igualdad / Salud'
    if any(x in lower for x in ['natural', 'ambiental', 'clima', 'ecologia', 'sostenibilidad', 'biodiversidad']): return 'Educación Ambiental'
    return 'General'

def main():
    print("Iniciando extracción automática por estructura de publicación...")
    soup_principal, html_principal = obtener_soup(URL)
    if not soup_principal:
        print("Error al conectar con la Consejería.")
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
            print(f"[{posicion}] Procesando: {texto[:50]}...")

            soup_sub, html_sub = obtener_soup(full_url)
            estado, estado_clave, detalle = determinar_estado_automatico(soup_sub, html_sub, texto)
            tipo = clasificar_area(texto + " " + (html_sub or ""))

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

    print(f"Proceso completado: {len(convocatorias)} convocatorias analizadas automáticamente.")

if __name__ == "__main__":
    main()
