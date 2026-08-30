# Panel Económico de Uruguay

Dashboard para la TV de la oficina con el histórico de los principales
indicadores económicos de Uruguay, tomados siempre de fuentes oficiales
primarias (INE, BCU, MEF), actualizado en forma automática.

## Cómo funciona

1. Todos los días a las 09:00 (hora Uruguay), GitHub ejecuta solo
   `collect_data.py`, que va a buscar el último dato de cada indicador
   directamente a las páginas oficiales del BCU, el INE y el MEF.
2. Ese script agrega los datos nuevos a los archivos de la carpeta `data/`.
   **Nunca borra ni pisa un dato que ya estaba guardado** — solo agrega.
3. La página `index.html` lee esos archivos y arma el panel visual.
4. Todo queda publicado en GitHub Pages, así que la TV siempre muestra la
   última versión sin que nadie tenga que tocar nada.

## Archivos

- `index.html` — el dashboard que se ve en la TV
- `collect_data.py` — el script que baja los datos y calcula las alertas
- `indicadores.py` — qué indicadores mostramos y de dónde sale cada uno
- `requirements.txt` — las librerías que necesita el script
- `data/` — el historial guardado (se genera solo, no hay que tocarlo)

## Indicadores incluidos (primera etapa)

Inflación (IPC), Unidad Indexada, expectativas de inflación, tipo de cambio
nominal y real, tasa de actividad, empleo, desempleo, salario real, PIB,
IMAE, consumo privado, resultado fiscal, deuda pública, tasa call (proxy de
la tasa de política monetaria) y riesgo país — este último marcado siempre
como "fuente de mercado", porque no lo publica ningún organismo del Estado.

Pendientes para una segunda etapa (no tienen todavía una fuente oficial
automatizable confirmada): informalidad, subempleo, pobreza, pobreza
infantil y expectativas económicas generales.

## Sistema de alertas

Cada indicador tiene un estado — **Normal**, **Atención** o **Alerta** —
calculado de forma objetiva: se compara la última variación del indicador
contra el comportamiento histórico de sus propias variaciones (desvíos
estándar). No es una opinión ni un umbral inventado a mano.

## Segunda etapa (futura)

Incorporar los indicadores internos de la empresa (facturación, clientes,
ticket promedio, costos, margen, empleados) para cruzarlos con la economía
del país.
