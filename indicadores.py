# -*- coding: utf-8 -*-
"""
Definición central de todos los indicadores del dashboard.

Cada indicador dice:
  - id: identificador interno (nombre del archivo en /data)
  - nombre: nombre para mostrar en el dashboard
  - categoria: para agrupar visualmente
  - dataset: nombre del dataset en la librería econuy (fuente: BCU/INE/MEF)
  - columna_contiene: lista de palabras que deben estar en el nombre en español
                       de la columna para identificarla (evita depender de un
                       número de columna fijo, que puede cambiar)
  - unidad: unidad de medida para mostrar
  - fuente_tipo: "oficial" (INE/BCU/MEF) o "mercado" (ej. riesgo país, calculado
                 por privados/JP Morgan, no por un organismo del estado)
  - requiere_navegador: True si econuy necesita un navegador (Chrome) para
                        bajar el dato. Son más lentos y algo más frágiles.
  - frecuencia: cada cuánto publica el dato el organismo oficial (referencia)
"""

INDICADORES = {
    "inflacion_ipc": {
        "nombre": "Inflación (IPC)",
        "categoria": "Precios",
        "dataset": "cpi",
        "columna_contiene": ["índice de precios al consumo"],
        "unidad": "Índice (base oct-2022=100)",
        "fuente_tipo": "oficial",
        "fuente_organismo": "INE",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "ui": {
        "nombre": "Unidad Indexada (UI)",
        "categoria": "Precios",
        "dataset": "indexed_unit",
        "columna_contiene": [],  # dataset de una sola columna
        "unidad": "UYU",
        "fuente_tipo": "oficial",
        "fuente_organismo": "INE",
        "requiere_navegador": False,
        "frecuencia": "diaria",
    },
    "tipo_cambio": {
        "nombre": "Tipo de cambio USD/UYU",
        "categoria": "Cambiario",
        "dataset": "nxr_daily",
        "columna_contiene": ["tipo de cambio venta"],
        "unidad": "UYU por USD",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU",
        "requiere_navegador": False,
        "frecuencia": "diaria",
    },
    "tipo_cambio_real": {
        "nombre": "Tipo de cambio real (multilateral)",
        "categoria": "Cambiario",
        "dataset": "rxr",
        "columna_contiene": ["global"],
        "unidad": "Índice (2019=100)",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "actividad": {
        "nombre": "Tasa de actividad",
        "categoria": "Mercado laboral",
        "dataset": "labor_rates_gender",
        "columna_contiene": ["tasa de actividad", "total"],
        "unidad": "%",
        "fuente_tipo": "oficial",
        "fuente_organismo": "INE",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "empleo": {
        "nombre": "Tasa de empleo",
        "categoria": "Mercado laboral",
        "dataset": "labor_rates_gender",
        "columna_contiene": ["tasa de empleo", "total"],
        "unidad": "%",
        "fuente_tipo": "oficial",
        "fuente_organismo": "INE",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "desempleo": {
        "nombre": "Tasa de desempleo",
        "categoria": "Mercado laboral",
        "dataset": "labor_rates_gender",
        "columna_contiene": ["tasa de desempleo", "total"],
        "unidad": "%",
        "fuente_tipo": "oficial",
        "fuente_organismo": "INE",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "salario_real": {
        "nombre": "Salario real",
        "categoria": "Mercado laboral",
        "dataset": "real_wages",
        "columna_contiene": ["índice medio de salarios reales"],
        "columna_excluye": ["privados", "públicos"],
        "unidad": "Índice (2008-07=100)",
        "fuente_tipo": "oficial",
        "fuente_organismo": "INE",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "pib": {
        "nombre": "PIB (precios constantes)",
        "categoria": "Actividad",
        "dataset": "national_accounts_demand_constant_nsa",
        "columna_contiene": ["producto bruto interno"],
        "unidad": "Millones de UYU (precios constantes), trimestral",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU",
        "requiere_navegador": False,
        "frecuencia": "trimestral",
    },
    "imae": {
        "nombre": "IMAE (actividad económica mensual)",
        "categoria": "Actividad",
        "dataset": "monthly_gdp",
        "columna_contiene": ["indicador mensual de actividad económica"],
        "columna_excluye": ["desestacionalizado", "tendencia"],
        "unidad": "Índice (2016=100)",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU",
        "requiere_navegador": True,
        "frecuencia": "mensual",
    },
    "consumo_privado": {
        "nombre": "Consumo privado (hogares)",
        "categoria": "Actividad",
        "dataset": "national_accounts_demand_constant_nsa",
        "columna_contiene": ["gasto de consumo: hogares"],
        "unidad": "Millones de UYU (precios constantes), trimestral",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU",
        "requiere_navegador": False,
        "frecuencia": "trimestral",
    },
    "tasa_politica_monetaria": {
        "nombre": "Tasa call / política monetaria (proxy)",
        "categoria": "Financiero",
        "dataset": "call_rate",
        "columna_contiene": ["tasa call a 1 día", "promedio"],
        "unidad": "% anual",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU / BEVSA",
        "requiere_navegador": True,
        "frecuencia": "diaria",
        "nota": (
            "BCU no publica una serie descargable de la Tasa de Política "
            "Monetaria como tal; se usa la tasa call interbancaria a 1 día, "
            "que es el mercado que la TPM regula directamente, como proxy."
        ),
    },
    "expectativas_inflacion": {
        "nombre": "Expectativas de inflación (12 meses, mediana)",
        "categoria": "Precios",
        "dataset": "inflation_expectations",
        "columna_contiene": ["próximos 12 meses", "mediana"],
        "unidad": "%",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "resultado_fiscal": {
        "nombre": "Resultado fiscal (Sector Público No Financiero)",
        "categoria": "Fiscal",
        "dataset": "fiscal_balance_nonfinancial_public_sector",
        "columna_contiene": ["resultado: global"],
        "unidad": "Millones de UYU, acumulado últimos 12 meses",
        "fuente_tipo": "oficial",
        "fuente_organismo": "MEF / BCU",
        "requiere_navegador": False,
        "frecuencia": "mensual",
    },
    "deuda_publica": {
        "nombre": "Deuda pública (Sector Público No Financiero)",
        "categoria": "Fiscal",
        "dataset": "public_debt_nonfinancial_public_sector",
        "columna_contiene": ["total deuda"],
        "unidad": "Millones de USD, trimestral",
        "fuente_tipo": "oficial",
        "fuente_organismo": "BCU",
        "requiere_navegador": False,
        "frecuencia": "trimestral",
    },
    "riesgo_pais": {
        "nombre": "Riesgo país (UBI)",
        "categoria": "Financiero",
        "dataset": "sovereign_risk_index",
        "columna_contiene": ["ubi"],
        "unidad": "Puntos básicos",
        "fuente_tipo": "mercado",
        "fuente_organismo": "República AFAP / BEVSA (cálculo tipo JP Morgan EMBI)",
        "requiere_navegador": True,
        "frecuencia": "diaria",
        "nota": (
            "No es un dato publicado por un organismo del Estado uruguayo: "
            "es un índice de mercado. Se incluye por su relevancia práctica, "
            "marcado siempre como 'fuente de mercado' en el dashboard."
        ),
    },
}

# Indicadores pedidos originalmente que NO tienen todavía una fuente
# automatizable confirmada (quedan para una segunda etapa):
#   - informalidad
#   - subempleo
#   - pobreza
#   - pobreza infantil
#   - expectativas económicas generales (más allá de inflación)
PENDIENTES_SEGUNDA_ETAPA = [
    "informalidad",
    "subempleo",
    "pobreza",
    "pobreza_infantil",
    "expectativas_economicas_generales",
]
