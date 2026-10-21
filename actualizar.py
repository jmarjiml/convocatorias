import urllib.request
import urllib.parse
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

URL = "https://www.gobiernodecanarias.org/educacion/web/programas-redes-educativas/convocatorias/"

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
req = urllib.request.Request(URL, headers=headers)

try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    
    convocatorias = []
    links = soup.find_all('a', href=True)
    
    for a in links:
        texto = a.get_text(strip=True)
        href = a['href']
        
        if not texto or len(texto) < 10 or href.startswith('#') or 'javascript:' in href:
            continue
            
        full_url = href if href.startswith('http') else urllib.parse.urljoin(URL, href)
        lower_text = texto.lower()
        
        # Filtrar solo proyectos, programas y convocatorias
        if any(k in lower_text for k in ['2026', 'proyecto', 'programa', 'convocatoria', 'curso']):
            estado = "Matrícula abierta"
            estado_clave = "abierta"
            detalle = "⚡ Inscripción o plazo abierto según el portal oficial del Gobierno de Canarias."

            if "provisional" in lower_text:
                estado = "Lista provisional"
                estado_clave = "provisional"
                detalle = "Listado provisional publicado."
            elif "definitiv" in lower_text:
                estado = "Listado definitivo"
                estado_clave = "definitiva"
                detalle = "Listado definitivo publicado."
            elif "instrucciones" in lower_text:
                estado = "Otros estados"
                estado_clave = "otros"
                detalle = "Instrucciones de la convocatoria."

            tipo = "General"
            if any(x in lower_text for x in ['steam', 'peter', 'idescubre', 'georrutas', 'robotica']): tipo = 'STEAM'
            elif any(x in lower_text for x in ['podcaster', 'viera', 'zurron', 'lengua', 'lectura', 'radio']): tipo = 'Comunicación lingüística'
            elif any(x in lower_text for x in ['salud', 'solidarios', 'murgavalores', 'igualdad', 'plato']): tipo = 'Igualdad / Salud'
            elif any(x in lower_text for x in ['natural', 'ambiental', 'clima', 'ecologia']): tipo = 'Educación Ambiental'
            elif 'matemat' in lower_text: tipo = 'Matemáticas'

            convocatorias.append({
                "titulo": texto.replace('\n', ' ').strip(),
                "url": full_url,
                "curso": "2026-2027",
                "tipo": tipo,
                "fuente": "Gobierno de Canarias",
                "estado": estado,
                "estadoClave": estado_clave,
                "detalle": detalle
            })
            
    # Eliminar duplicados manteniendo el orden
    vistos = set()
    unicas = []
    for item in convocatorias:
        if item['titulo'] not in vistos:
            vistos.add(item['titulo'])
            unicas.append(item)

    # Guardar en archivo JSON
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    resultado = {
        "updated": fecha_actual,
        "data": unicas
    }
    
    with open('convocatorias.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
        
    print(f"Sincronización exitosa: {len(unicas)} convocatorias encontradas.")

except Exception as e:
    print(f"Error durante la sincronización: {e}")
