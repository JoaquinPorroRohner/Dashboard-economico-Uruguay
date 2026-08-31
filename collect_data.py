# -*- coding: utf-8 -*-
"""
Script principal de recolección de datos.

Qué hace:
  1. Para cada indicador definido en indicadores.py, baja la serie
     completa desde su fuente oficial (a través de la librería econuy, que
     se conecta directamente a BCU/INE/MEF).
  2. Identifica la columna correcta buscando por nombre (no por posición fija).
  3. Agrega los datos nuevos al historial en /data/<id>.json SIN pisar ni
     borrar nunca un registro que ya existía (histórico inmutable).
  4. Calcula un estado de alerta objetivo (Normal / Atención / Alerta) para
     el último dato de cada indicador, basado en cuántos desvíos estándar
     se aleja del comportamiento histórico de esa serie.
  5. Deja todo en /data, listo para que el dashboard (index.html) lo lea.

Este script está pensado para correr automáticamente todos los días desde
GitHub Actions (ver .github/workflows/actualizar-datos.yml), pero también
se puede correr a mano con: python collect_data.py
"""
import contextlib
import json
import os
import ssl
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def preparar_certificados():
    """Arregla el error 'CERTIFICATE_VERIFY_FAILED' con las webs del Estado.

    El problema: los sitios del INE y del BCU publican su certificado de
    seguridad de forma incompleta (les falta un eslabón intermedio de la
    cadena). Los navegadores lo disimulan, pero Python es estricto y por eso
    rechaza la conexión.

    La solución: la librería econuy trae guardados esos certificados que
    faltan. Acá los juntamos con los que Python ya conoce y armamos un
    paquete único que usan tanto pandas como httpx (las dos formas en que
    este script se conecta).

    IMPORTANTE: esto NO desactiva ninguna verificación de seguridad. Solo
    completa la información que los sitios oficiales publican mal. Las
    conexiones se siguen verificando igual que siempre.
    """
    # 1) Los certificados oficiales uruguayos que faltan (los trae econuy).
    certificados_uruguayos = []
    try:
        from econuy.utils.retrieval import get_certs_path
        for fuente in ("bcu", "ine", "inac", "bcra"):
            ruta = Path(get_certs_path(fuente))
            if ruta.exists():
                certificados_uruguayos.append(ruta)
    except Exception as e:
        print(f"  Aviso: no se encontraron los certificados oficiales ({e})")

    if not certificados_uruguayos:
        print("  Aviso: sigo sin certificados extra, puede haber errores de SSL")
        return

    # 2) El contexto para pandas/urllib: partimos de los certificados que ya
    #    tiene el sistema (así no rompemos nada de lo que ya funcionaba) y
    #    les SUMAMOS los uruguayos.
    contexto = ssl.create_default_context()
    for ruta in certificados_uruguayos:
        contexto.load_verify_locations(cafile=str(ruta))
    ssl._create_default_https_context = lambda *a, **kw: contexto

    # 3) httpx no usa ese contexto, sino un archivo indicado por variable de
    #    entorno. Armamos un paquete que junta TODO: los del sistema, los de
    #    certifi y los uruguayos.
    partes = []
    rutas_sistema = ssl.get_default_verify_paths()
    candidatos = [
        rutas_sistema.cafile,
        rutas_sistema.openssl_cafile,
        "/etc/ssl/certs/ca-certificates.crt",
    ]
    try:
        import certifi
        candidatos.append(certifi.where())
    except Exception:
        pass

    ya_agregados = set()
    for candidato in candidatos:
        if not candidato:
            continue
        p = Path(candidato)
        if p.exists() and p.resolve() not in ya_agregados:
            ya_agregados.add(p.resolve())
            partes.append(p.read_bytes())
    for ruta in certificados_uruguayos:
        partes.append(ruta.read_bytes())

    paquete = Path(tempfile.gettempdir()) / "certificados_uruguay.pem"
    paquete.write_bytes(b"\n".join(partes))
    os.environ["SSL_CERT_FILE"] = str(paquete)
    os.environ["REQUESTS_CA_BUNDLE"] = str(paquete)

    print(f"  Certificados listos ({len(contexto.get_ca_certs())} autoridades, "
          f"{len(certificados_uruguayos)} paquetes oficiales sumados)")


print("Preparando conexión segura con los sitios oficiales...")
preparar_certificados()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indicadores import INDICADORES  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HOY = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def elegir_columna(dataset, spec):
    """Encuentra la columna correcta dentro de un dataset de econuy buscando
    por texto en su nombre en español, en vez de depender de un índice fijo
    que puede cambiar si la fuente oficial reordena sus datos."""
    nombrado = dataset.to_named()
    incluye = [s.lower() for s in spec.get("columna_contiene", [])]
    excluye = [s.lower() for s in spec.get("columna_excluye", [])]

    if not incluye:
        # Dataset de una sola columna: la tomamos directo.
        return nombrado.iloc[:, 0], nombrado.columns[0]

    for col in nombrado.columns:
        col_low = str(col).lower()
        if all(term in col_low for term in incluye) and not any(
            term in col_low for term in excluye
        ):
            return nombrado[col], col

    raise ValueError(
        f"No encontré ninguna columna que contenga {incluye} "
        f"(excluyendo {excluye}). Columnas disponibles: {list(nombrado.columns)}"
    )


def calcular_estado_alerta(serie: pd.Series) -> dict:
    """Metodología objetiva y simple:
    - Se calcula la variación entre cada dato y el anterior (mensual,
      trimestral o diaria según la frecuencia real de la serie).
    - Se mide cuántos desvíos estándar históricos representa la ÚLTIMA
      variación, comparada contra todas las variaciones históricas de esa
      misma serie (z-score).
    - |z| < 1   -> "Normal"
    - 1 <= |z| < 2 -> "Atención"
    - |z| >= 2  -> "Alerta"
    Devuelve también la variación intermensual/interanual en % para mostrar
    en el dashboard.
    """
    serie = serie.dropna()
    if len(serie) < 8:
        return {"estado": "Sin datos suficientes", "z_score": None,
                "variacion_periodo_pct": None, "variacion_interanual_pct": None}

    variaciones = serie.pct_change().dropna()
    ultima_variacion = variaciones.iloc[-1]
    media_hist = variaciones[:-1].mean()
    desvio_hist = variaciones[:-1].std()

    if desvio_hist == 0 or np.isnan(desvio_hist):
        z = 0.0
    else:
        z = (ultima_variacion - media_hist) / desvio_hist

    if abs(z) >= 2:
        estado = "Alerta"
    elif abs(z) >= 1:
        estado = "Atención"
    else:
        estado = "Normal"

    # Variación interanual, si hay al menos 13 datos (para series mensuales).
    #
    # OJO con los indicadores que pueden ser negativos (el resultado fiscal,
    # por ejemplo): ahí el porcentaje MIENTE. Si un déficit pasa de -32.000 a
    # -35.407, la cuenta del porcentaje da +10%, y leído sin cuidado parece
    # una mejora cuando en realidad el déficit creció. Por eso:
    #   - el porcentaje solo se calcula si el punto de partida es positivo,
    #   - y siempre guardamos además la diferencia real (resta), que nunca
    #     se da vuelta y es la que el dashboard usa para decidir el color.
    variacion_interanual = None
    variacion_interanual_abs = None
    if len(serie) >= 13:
        try:
            anterior = float(serie.iloc[-13])
            actual = float(serie.iloc[-1])
            variacion_interanual_abs = round(actual - anterior, 4)
            if anterior > 0:
                variacion_interanual = round((actual / anterior - 1) * 100, 2)
        except (IndexError, ZeroDivisionError, ValueError):
            pass

    return {
        "estado": estado,
        "z_score": round(float(z), 2),
        "variacion_periodo_pct": round(float(ultima_variacion) * 100, 2),
        "variacion_interanual_pct": variacion_interanual,
        "variacion_interanual_abs": variacion_interanual_abs,
    }


def cargar_historial(indicador_id: str) -> list:
    archivo = DATA_DIR / f"{indicador_id}.json"
    if archivo.exists():
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)
            return contenido.get("historial", [])
    return []


def guardar_historial(indicador_id: str, spec: dict, historial: list, estado: dict,
                       fuente_url: str, verificacion_relajada: bool = False):
    archivo = DATA_DIR / f"{indicador_id}.json"
    salida = {
        "id": indicador_id,
        "nombre": spec["nombre"],
        "categoria": spec["categoria"],
        "unidad": spec["unidad"],
        "fuente_tipo": spec["fuente_tipo"],
        "fuente_organismo": spec["fuente_organismo"],
        "fuente_url": fuente_url,
        "nota": spec.get("nota", ""),
        "ultima_actualizacion": HOY,
        "certificado_verificado": not verificacion_relajada,
        "estado_actual": estado,
        "historial": historial,
    }
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


@contextlib.contextmanager
def verificacion_relajada():
    """Baja temporalmente la verificación del certificado, y la restaura.

    Se usa SOLO como reintento, y SOLO cuando el intento normal falló
    justamente por un certificado mal publicado (hoy: www5.ine.gub.uy).
    Cada indicador que pasa por acá queda marcado en el archivo de datos y
    en el resumen de la corrida, para que siempre se sepa cuál se bajó así.

    Por qué es aceptable en este caso puntual: son datos públicos, la
    conexión es de solo lectura y no se envía ninguna contraseña ni dato
    privado. Lo peor que podría pasar es recibir un dato adulterado, y eso
    se detectaría porque el dashboard muestra siempre la fuente oficial al
    lado de cada número.
    """
    contexto_previo = ssl._create_default_https_context
    cert_previo = os.environ.get("SSL_CERT_FILE")
    sin_verificar = ssl._create_unverified_context()
    ssl._create_default_https_context = lambda *a, **kw: sin_verificar
    os.environ.pop("SSL_CERT_FILE", None)
    try:
        yield
    finally:
        ssl._create_default_https_context = contexto_previo
        if cert_previo is not None:
            os.environ["SSL_CERT_FILE"] = cert_previo


def _bajar_indicador(indicador_id: str, spec: dict) -> tuple:
    """Baja un indicador y devuelve (historial actualizado, estado, url, columna)."""
    from econuy import load_dataset

    dataset = load_dataset(spec["dataset"])
    serie, nombre_columna = elegir_columna(dataset, spec)

    # Algunas planillas oficiales traen filas sueltas con la fecha vacía o
    # rota (encabezados, notas al pie, filas de relleno). Si no las sacamos
    # acá, rompen todo el indicador al momento de convertir la fecha.
    serie = serie[~pd.isna(serie.index)]
    serie = serie.dropna().sort_index()

    historial_existente = cargar_historial(indicador_id)
    fechas_existentes = {r["fecha"] for r in historial_existente}

    nuevos = 0
    for fecha, valor in serie.items():
        if pd.isna(fecha) or pd.isna(valor):
            continue  # dato incompleto en la fuente: lo salteamos
        fecha_str = fecha.strftime("%Y-%m-%d")
        if fecha_str in fechas_existentes:
            continue  # nunca pisamos un dato histórico ya guardado
        historial_existente.append({
            "fecha": fecha_str,
            "valor": round(float(valor), 4),
            "fecha_incorporado": HOY,
        })
        nuevos += 1

    historial_existente.sort(key=lambda r: r["fecha"])
    estado = calcular_estado_alerta(serie)

    fuente_url = ""
    try:
        from econuy.utils.operations import get_download_sources
        urls = get_download_sources(spec["dataset"])
        fuente_url = urls.get("main") or urls.get("historical") or urls.get("current") or ""
    except Exception:
        pass

    return historial_existente, estado, fuente_url, nombre_columna, nuevos


def procesar_indicador(indicador_id: str, spec: dict) -> dict:
    resultado = {"id": indicador_id, "ok": False, "mensaje": "",
                 "verificacion_relajada": False}
    try:
        datos = _bajar_indicador(indicador_id, spec)
    except Exception as e:
        # ¿Falló por el certificado? Si no, no insistimos: es otro problema.
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            resultado["mensaje"] = f"{type(e).__name__}: {e}"
            resultado["traceback"] = traceback.format_exc()
            return resultado
        # Sí fue el certificado: reintentamos una sola vez, sin verificar,
        # y lo dejamos anotado.
        try:
            with verificacion_relajada():
                datos = _bajar_indicador(indicador_id, spec)
            resultado["verificacion_relajada"] = True
        except Exception as e2:
            resultado["mensaje"] = (f"Fallo tambien sin verificar -> "
                                    f"{type(e2).__name__}: {e2}")
            resultado["traceback"] = traceback.format_exc()
            return resultado

    historial, estado, fuente_url, nombre_columna, nuevos = datos
    guardar_historial(indicador_id, spec, historial, estado, fuente_url,
                      resultado["verificacion_relajada"])
    resultado["ok"] = True
    aviso = " [certificado no verificado]" if resultado["verificacion_relajada"] else ""
    resultado["mensaje"] = f"{nuevos} dato(s) nuevo(s) (columna: {nombre_columna}){aviso}"
    return resultado


def main():
    print(f"=== Recolección de datos — {HOY} ===\n")
    resumen = []
    for indicador_id, spec in INDICADORES.items():
        print(f"-> {indicador_id} ({spec['nombre']})...", end=" ")
        r = procesar_indicador(indicador_id, spec)
        resumen.append(r)
        print("OK:", r["mensaje"]) if r["ok"] else print("ERROR:", r["mensaje"])

    # Guardamos un resumen de la última corrida, útil para diagnosticar
    # sin tener que leer los logs de GitHub Actions.
    with open(DATA_DIR / "_ultima_corrida.json", "w", encoding="utf-8") as f:
        json.dump({"fecha": HOY, "resultados": resumen}, f, ensure_ascii=False, indent=2)

    # Y una versión corta y liviana (sin los detalles técnicos largos), que
    # es la que conviene abrir para ver de un vistazo cómo salió cada uno.
    corto = {
        "fecha": HOY,
        "andan": [r["id"] for r in resumen if r["ok"]],
        "fallan": {r["id"]: r["mensaje"][:220] for r in resumen if not r["ok"]},
        "sin_verificar": [r["id"] for r in resumen if r.get("verificacion_relajada")],
    }
    with open(DATA_DIR / "resumen.json", "w", encoding="utf-8") as f:
        json.dump(corto, f, ensure_ascii=False, indent=2)

    fallidos = [r for r in resumen if not r["ok"]]
    relajados = [r for r in resumen if r.get("verificacion_relajada")]
    print(f"\nTotal: {len(resumen)} indicadores | OK: {len(resumen) - len(fallidos)} | "
          f"Con error: {len(fallidos)}")
    if relajados:
        print(f"\nBajados sin verificar el certificado ({len(relajados)}) — "
              f"el sitio oficial lo tiene mal publicado:")
        for r in relajados:
            print(f"  - {r['id']}")
    if fallidos:
        print("\nIndicadores con error (revisar, pero no se detiene el resto):")
        for r in fallidos:
            print(f"  - {r['id']}: {r['mensaje']}")


if __name__ == "__main__":
    main()
