# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Crea dos sitios de dashboard de ejemplo con datos representativos de
educacion superior en Mexico (ENOE 2024 / ANUIES), sin dependencias
de archivos GPKG externos.

  Sitio 1: Posgrados y Mercado Laboral  (datos ENOE 2024-I por entidad)
  Sitio 2: Movilidad Estudiantil        (datos ANUIES flujos origen-destino)

Uso:
    python manage.py create_dashboard_examples
    python manage.py create_dashboard_examples --flush
    python manage.py create_dashboard_examples --layer-name-enoe <name>
    python manage.py create_dashboard_examples --layer-name-od <name>
"""

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand

from sigic_geonode.sigic_dashboard.models import (
    Indicator,
    IndicatorFieldBoxInfo,
    IndicatorGroup,
    Site,
    SiteConfiguration,
    SubGroup,
)

# ---------------------------------------------------------------------------
# Paletas de color
# ---------------------------------------------------------------------------

PALETTE_BLUES = [
    "#084081", "#0868ac", "#2b8cbe", "#4eb3d3", "#7bccc4",
    "#a8ddb5", "#ccebc5", "#e0f3db", "#f7fcf0",
]
PALETTE_PURPLES = [
    "#4d004b", "#810f7c", "#88419d", "#8c6bb1", "#8c96c6",
    "#9ebcda", "#bfd3e6", "#e0ecf4", "#f7fcfd",
]
PALETTE_NARANJAS = [
    "#7f0000", "#b30000", "#d7301f", "#ef6548", "#fc8d59",
    "#fdbb84", "#fdd49e", "#fee8c8", "#fff7ec",
]
PALETTE_GREENS = [
    "#00441b", "#006d2c", "#238b45", "#41ae76", "#66c2a4",
    "#99d8c9", "#ccece6", "#e5f5f9", "#f7fcfd",
]
PALETTE_MORADOS2 = [
    "#49006a", "#7a0177", "#ae017e", "#dd3497", "#f768a1",
    "#fa9fb5", "#fcc5c0", "#fde0dd", "#fff7f3",
]


# ---------------------------------------------------------------------------
# Datos estaticos representativos (ENOE 2024-I / ANUIES)
# ---------------------------------------------------------------------------

ESTADOS = [
    ("01", "Aguascalientes"),
    ("02", "Baja California"),
    ("03", "Baja California Sur"),
    ("04", "Campeche"),
    ("05", "Coahuila"),
    ("06", "Colima"),
    ("07", "Chiapas"),
    ("08", "Chihuahua"),
    ("09", "Ciudad de Mexico"),
    ("10", "Durango"),
    ("11", "Guanajuato"),
    ("12", "Guerrero"),
    ("13", "Hidalgo"),
    ("14", "Jalisco"),
    ("15", "Mexico"),
    ("16", "Michoacan"),
    ("17", "Morelos"),
    ("18", "Nayarit"),
    ("19", "Nuevo Leon"),
    ("20", "Oaxaca"),
    ("21", "Puebla"),
    ("22", "Queretaro"),
    ("23", "Quintana Roo"),
    ("24", "San Luis Potosi"),
    ("25", "Sinaloa"),
    ("26", "Sonora"),
    ("27", "Tabasco"),
    ("28", "Tamaulipas"),
    ("29", "Tlaxcala"),
    ("30", "Veracruz"),
    ("31", "Yucatan"),
    ("32", "Zacatecas"),
]

# Tasas de posgrado sobre poblacion ocupada (%) — basado en ENOE 2024-I
TASA_GENERAL = [
    8.5, 7.2, 6.8, 5.9, 7.8, 7.1, 3.2, 6.4, 14.2, 5.7,
    6.1, 3.8, 5.4, 8.9, 7.6, 4.9, 7.8, 5.2, 10.4, 4.1,
    7.3, 9.2, 5.6, 6.0, 5.8, 7.0, 5.1, 7.5, 5.9, 5.3,
    7.1, 5.5,
]

TOTAL_POSGRADO = [
    45200, 82100, 19400, 15300, 72800, 16200, 52100, 77600,
    610200, 37100, 92300, 38700, 47200, 193400, 296100, 63200,
    54800, 24100, 199800, 41500, 148200, 68400, 36100, 52700,
    55300, 73400, 43900, 88200, 28600, 112100, 61300, 25700,
]

TOTAL_POBLACION = [
    531700, 1138900, 285400, 258600, 933100, 228000, 1629000,
    1211100, 4295400, 650700, 1512600, 1018500, 873100, 2173400,
    3896700, 1289600, 701800, 462900, 1922700, 1011900, 2029300,
    742800, 644600, 877800, 952400, 1049400, 860500, 1174400,
    483700, 2113900, 862100, 467900,
]

TASA_SERV_PROF = [
    12.1, 9.8, 8.4, 6.2, 10.5, 9.1, 3.1, 8.7, 22.4, 7.2,
    8.3, 4.1, 6.8, 12.7, 10.9, 6.3, 10.2, 6.5, 16.8, 4.8,
    9.4, 13.1, 7.2, 7.9, 7.5, 9.5, 6.3, 10.1, 7.4, 6.8,
    9.4, 6.9,
]

TASA_SERV_SOC = [
    8.4, 7.1, 6.2, 5.1, 7.6, 6.8, 3.8, 6.0, 14.8, 5.9,
    6.2, 4.2, 5.6, 9.1, 8.3, 5.7, 8.5, 5.4, 12.1, 5.0,
    7.8, 9.8, 5.8, 6.3, 6.1, 7.3, 5.8, 7.9, 6.2, 6.0,
    8.1, 5.8,
]

TASA_GOBIERNO = [
    6.2, 5.9, 5.8, 5.2, 6.4, 5.7, 3.5, 5.3, 10.1, 5.4,
    5.3, 3.9, 5.1, 6.8, 6.5, 5.0, 6.4, 4.9, 8.2, 4.5,
    5.9, 7.0, 5.1, 5.6, 5.5, 6.0, 5.2, 6.3, 5.3, 5.1,
    6.0, 5.0,
]

TASA_MANUFACTURA = [
    4.1, 3.8, 2.9, 2.4, 4.5, 3.1, 1.8, 3.9, 5.2, 3.0,
    3.8, 2.1, 3.2, 4.6, 4.3, 2.9, 3.8, 2.5, 5.8, 2.3,
    3.7, 4.8, 2.8, 3.3, 3.0, 3.6, 2.7, 3.9, 3.1, 3.0,
    3.5, 2.8,
]

TASA_COMERCIO = [
    3.2, 2.9, 2.5, 2.1, 3.4, 2.8, 1.5, 2.8, 4.6, 2.5,
    2.9, 1.8, 2.6, 3.7, 3.5, 2.4, 3.2, 2.1, 4.5, 1.9,
    3.0, 3.9, 2.4, 2.7, 2.5, 2.9, 2.2, 3.1, 2.5, 2.4,
    2.8, 2.3,
]

# Flujos de movilidad estudiantil — basado en ANUIES
TOTAL_OUTGOING = [
    5420, 12300, 3200, 2800, 9800, 2900, 8100, 10200,
    45000, 4200, 13500, 7200, 9100, 22400, 38700, 12100,
    8300, 3600, 18500, 7800, 21300, 8900, 5100, 8500,
    7900, 10600, 6400, 11300, 5200, 17800, 9200, 4600,
]

FLUJO_CDMX = [
    1200, 3400, 800, 600, 2100, 700, 1900, 2300,
    8000, 900, 2800, 1600, 2200, 4800, 9500, 2700,
    1900, 800, 3900, 1800, 5200, 2000, 1100, 1900,
    1700, 2200, 1400, 2500, 1200, 4100, 2000, 1000,
]

FLUJO_NL = [
    800, 1200, 400, 200, 1900, 300, 500, 1500,
    2100, 600, 1100, 400, 500, 1600, 2800, 700,
    500, 300, 4200, 400, 1100, 600, 300, 700,
    600, 1800, 300, 1600, 300, 800, 400, 300,
]


# ---------------------------------------------------------------------------
# Funciones de carga de datos
# ---------------------------------------------------------------------------

def _load_enoe():
    cves = [e[0] for e in ESTADOS]
    nombres = [e[1] for e in ESTADOS]
    return pd.DataFrame({
        "CVE_ENT": cves,
        "NOMGEO": nombres,
        "tasa_general_entidad": TASA_GENERAL,
        "total_posgrado_entidad": TOTAL_POSGRADO,
        "total_poblacion_entidad": TOTAL_POBLACION,
        "tasa_servicios_profesionales": TASA_SERV_PROF,
        "tasa_servicios_sociales": TASA_SERV_SOC,
        "tasa_gobierno": TASA_GOBIERNO,
        "tasa_industria_manufacturera": TASA_MANUFACTURA,
        "tasa_comercio": TASA_COMERCIO,
    })


def _load_od():
    cves = [e[0] for e in ESTADOS]
    nombres = [e[1] for e in ESTADOS]
    return pd.DataFrame({
        "cve_ent": cves,
        "nombre_entidad": nombres,
        "total_outgoing": TOTAL_OUTGOING,
        "PU_CDMX": FLUJO_CDMX,
        "PU_NL": FLUJO_NL,
    })


# ---------------------------------------------------------------------------
# Helpers de calculo
# ---------------------------------------------------------------------------

def _quantile_plot_map(df, value_col, id_col, name_col, palette, n=5):
    """
    Clasifica value_col en n cuantiles y devuelve (plot_values, map_values, labels, bin_edges).
    """
    df = df.dropna(subset=[value_col]).copy()
    _, bin_edges = pd.qcut(df[value_col], q=n, retbins=True, duplicates="drop")
    labels = [
        f"{bin_edges[i]:.2f}   -   {bin_edges[i+1]:.2f}"
        for i in range(len(bin_edges) - 1)
    ]
    df["_cat"] = pd.cut(
        df[value_col], bins=bin_edges, labels=labels, include_lowest=True
    )
    counts = df.groupby("_cat", observed=True).size()

    plot_values = [
        {
            "sortPosition": idx + 1,
            "label": str(label),
            "value": int(count),
            "color": palette[idx % len(palette)],
        }
        for idx, (label, count) in enumerate(counts.items())
    ]
    color_map = {str(l): palette[i % len(palette)] for i, l in enumerate(counts.index)}

    map_values = {}
    for _, row in df.iterrows():
        cat = str(row["_cat"])
        map_values[str(row[id_col])] = {
            "value": cat,
            "color": color_map.get(cat, "#999999"),
        }

    return plot_values, map_values, labels, list(bin_edges)


def _group_plot_map(df, group_col, value_col, id_col, palette):
    """
    Agrupa por group_col sumando value_col.
    Devuelve (plot_values, map_values) ordenados descendente.
    """
    grouped = (
        df.groupby(group_col)[value_col]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    color_map = {
        row[group_col]: palette[i % len(palette)]
        for i, row in grouped.iterrows()
    }
    plot_values = [
        {
            "sortPosition": i + 1,
            "label": str(row[group_col]),
            "value": float(round(row[value_col], 3)),
            "color": color_map[row[group_col]],
        }
        for i, row in grouped.iterrows()
    ]
    map_values = {}
    for _, row in df.iterrows():
        label = str(row[group_col])
        map_values[str(row[id_col])] = {
            "value": label,
            "color": color_map.get(label, "#999999"),
        }
    return plot_values, map_values


# ---------------------------------------------------------------------------
# Resolucion de layer Django
# ---------------------------------------------------------------------------

def _resolve_layer(layer_name):
    """Busca un Dataset de GeoNode por nombre de capa."""
    try:
        from geonode.layers.models import Dataset

        qs = Dataset.objects.filter(name__icontains=layer_name)
        if qs.exists():
            return qs.first()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Sitio 1: Posgrados y Mercado Laboral
# ---------------------------------------------------------------------------

def create_posgrados_site(layer_name_enoe):
    df_enoe = _load_enoe()
    layer_enoe = _resolve_layer(layer_name_enoe) if layer_name_enoe else None

    site, _ = Site.objects.get_or_create(
        name="Posgrados y Mercado Laboral",
        defaults={
            "title": "Posgrados y Mercado Laboral en Mexico",
            "subtitle": (
                "Insercion laboral de personas con estudios de posgrado "
                "por entidad federativa y sector economico (ENOE 2024-I)"
            ),
            "url": "/dashboard/posgrados",
            "info_text": (
                "Indicadores de ocupacion y tasa de posgrado por sector economico "
                "basados en la Encuesta Nacional de Ocupacion y Empleo (ENOE), "
                "primer trimestre 2024. Fuente: INEGI / CONAHCYT."
            ),
        },
    )

    SiteConfiguration.objects.get_or_create(
        site=site,
        defaults={
            "show_header": True,
            "show_footer": True,
            "header_background_color": "#1565C0",
            "header_text_color": "#ffffff",
            "header_font_size": 24,
            "site_font_style": "Montserrat",
            "site_text_color": "#212121",
            "site_interface_text_color": "#212121",
            "site_background_color": "#E3F2FD",
            "site_interface_background_color": "#ffffff",
            "site_font_size": 15,
            "indicator_box_title": "Indicador de posgrado",
        },
    )

    # ── Grupo 1: Insercion Laboral ─────────────────────────────────────────
    g_ins, _ = IndicatorGroup.objects.get_or_create(
        site=site,
        name="Insercion Laboral de Posgrados",
        defaults={
            "description": "Tasa de ocupacion con nivel de posgrado por entidad federativa",
            "info_text": (
                "La tasa de posgrado mide el porcentaje de la poblacion ocupada "
                "que cuenta con estudios de maestria o doctorado terminados."
            ),
            "stack_order": 1,
        },
    )

    sg_tasa, _ = SubGroup.objects.get_or_create(
        group=g_ins,
        name="Tasa de posgrado por entidad",
        defaults={
            "info_text": "Clasificacion estatal por tasa de posgrado sobre poblacion ocupada.",
            "icon": "fas fa-graduation-cap",
            "stack_order": 1,
        },
    )

    plot_tasa, map_tasa, labels_tasa, bins_tasa = _quantile_plot_map(
        df_enoe, "tasa_general_entidad", "CVE_ENT", "NOMGEO", PALETTE_BLUES
    )

    ind_tasa = Indicator.objects.filter(
        subgroup=sg_tasa, name="Clasificacion estatal por tasa de posgrado"
    ).first()
    if not ind_tasa:
        ind_tasa = Indicator.objects.create(
            subgroup=sg_tasa,
            name="Clasificacion estatal por tasa de posgrado",
            plot_type="bar",
            info_text=(
                "Numero de estados dentro de cada rango de tasa de posgrado (%). "
                "Clasificacion por cuantiles (ENOE 2024-I)."
            ),
            layer=layer_enoe,
            layer_id_field="cve_ent",
            layer_nom_field="NOMGEO",
            high_values_percentage=10,
            use_single_field=True,
            field_one="tasa_general_entidad",
            field_two="",
            field_popup=["NOMGEO", "tasa_general_entidad", "total_posgrado_entidad"],
            category_method="quantil",
            field_category=5,
            colors="azules",
            use_custom_colors=False,
            plot_config={
                "chart_type": "bar",
                "field_one": "tasa_general_entidad",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_tasa,
                "ranges": [
                    {
                        "label": labels_tasa[i],
                        "alias": labels_tasa[i],
                        "color": PALETTE_BLUES[i],
                        "count": plot_tasa[i]["value"],
                    }
                    for i in range(len(labels_tasa))
                ],
            },
            plot_values=plot_tasa,
            map_values=map_tasa,
            general_values={
                "tasa_general_entidad": round(float(df_enoe["tasa_general_entidad"].mean()), 2),
                "total_posgrado_entidad": int(df_enoe["total_posgrado_entidad"].sum()),
                "total_poblacion_entidad": int(df_enoe["total_poblacion_entidad"].sum()),
            },
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )
    else:
        ind_tasa.general_values = {
            "tasa_general_entidad": round(float(df_enoe["tasa_general_entidad"].mean()), 2),
            "total_posgrado_entidad": int(df_enoe["total_posgrado_entidad"].sum()),
            "total_poblacion_entidad": int(df_enoe["total_poblacion_entidad"].sum()),
        }
        if not ind_tasa.plot_config or not ind_tasa.plot_config.get("ranges"):
            ind_tasa.plot_config = {
                "chart_type": "bar",
                "field_one": "tasa_general_entidad",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_tasa,
                "ranges": [
                    {
                        "label": labels_tasa[i],
                        "alias": labels_tasa[i],
                        "color": PALETTE_BLUES[i],
                        "count": plot_tasa[i]["value"],
                    }
                    for i in range(len(labels_tasa))
                ],
            }
            ind_tasa.plot_values = plot_tasa
            ind_tasa.map_values = map_tasa
        ind_tasa.save(update_fields=["general_values", "plot_config", "plot_values", "map_values"])

    if not ind_tasa.infoboxes.exists():
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_tasa,
            field="tasa_general_entidad",
            is_percentage=False,
            name="Tasa de posgrado (%)",
            icon="fas fa-percentage",
            color="#1565C0",
            size="2",
            edge_style="7",
            edge_color="#42A5F5",
            text_color="#ffffff",
            stack_order=1,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_tasa,
            field="total_posgrado_entidad",
            is_percentage=False,
            name="Personas con posgrado",
            icon="fas fa-user-graduate",
            color="#0868ac",
            size="1",
            edge_style="5",
            edge_color="#4eb3d3",
            text_color="#ffffff",
            stack_order=2,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_tasa,
            field="total_poblacion_entidad",
            is_percentage=False,
            name="Poblacion ocupada total",
            icon="fas fa-users",
            color="#2b8cbe",
            size="1",
            edge_style="5",
            edge_color="#7bccc4",
            text_color="#ffffff",
            stack_order=3,
        )

    # ── SubGrupo: Servicios profesionales ─────────────────────────────────
    sg_prof, _ = SubGroup.objects.get_or_create(
        group=g_ins,
        name="Sector servicios profesionales",
        defaults={
            "info_text": (
                "Tasa de posgrado en el sector de servicios profesionales, "
                "corporativos y financieros por entidad."
            ),
            "icon": "fas fa-briefcase",
            "stack_order": 2,
        },
    )

    plot_prof, map_prof = _group_plot_map(
        df_enoe, "NOMGEO", "tasa_servicios_profesionales", "CVE_ENT", PALETTE_PURPLES
    )

    ind_prof = Indicator.objects.filter(
        subgroup=sg_prof, name="Tasa de posgrado en servicios profesionales por estado"
    ).first()
    if not ind_prof:
        prof_labels = [pv["label"] for pv in plot_prof]
        prof_colors = [pv["color"] for pv in plot_prof]
        ind_prof = Indicator.objects.create(
            subgroup=sg_prof,
            name="Tasa de posgrado en servicios profesionales por estado",
            plot_type="bar",
            info_text=(
                "Porcentaje de ocupados en servicios profesionales que tienen "
                "grado de posgrado, por entidad federativa."
            ),
            layer=layer_enoe,
            layer_id_field="cve_ent",
            layer_nom_field="NOMGEO",
            high_values_percentage=10,
            use_single_field=False,
            field_one="NOMGEO",
            field_two="tasa_servicios_profesionales",
            field_popup=["NOMGEO", "tasa_servicios_profesionales", "tasa_gobierno"],
            category_method="quantil",
            field_category=5,
            colors="morados",
            use_custom_colors=False,
            plot_config={
                "chart_type": "horizontal_bar",
                "field_one": "NOMGEO",
                "field_two": "tasa_servicios_profesionales",
                "method": "quantil",
                "categories": 5,
                "ranges": [
                    {
                        "label": prof_labels[i],
                        "alias": prof_labels[i],
                        "color": prof_colors[i],
                        "count": 1,
                    }
                    for i in range(min(5, len(plot_prof)))
                ],
            },
            plot_values=plot_prof,
            map_values=map_prof,
            general_values={
                "tasa_servicios_profesionales": round(
                    float(df_enoe["tasa_servicios_profesionales"].mean()), 2
                ),
                "tasa_servicios_sociales": round(
                    float(df_enoe["tasa_servicios_sociales"].mean()), 2
                ),
                "tasa_gobierno": round(float(df_enoe["tasa_gobierno"].mean()), 2),
            },
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )
    else:
        ind_prof.general_values = {
            "tasa_servicios_profesionales": round(
                float(df_enoe["tasa_servicios_profesionales"].mean()), 2
            ),
            "tasa_servicios_sociales": round(
                float(df_enoe["tasa_servicios_sociales"].mean()), 2
            ),
            "tasa_gobierno": round(float(df_enoe["tasa_gobierno"].mean()), 2),
        }
        ind_prof.save(update_fields=["general_values"])

    if not ind_prof.infoboxes.exists():
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_prof,
            field="tasa_servicios_profesionales",
            is_percentage=False,
            name="Tasa serv. profesionales",
            icon="fas fa-briefcase",
            color="#810f7c",
            size="1",
            edge_style="7",
            edge_color="#dd3497",
            text_color="#ffffff",
            stack_order=1,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_prof,
            field="tasa_servicios_sociales",
            is_percentage=False,
            name="Tasa serv. sociales",
            icon="fas fa-hand-holding-heart",
            color="#88419d",
            size="1",
            edge_style="7",
            edge_color="#8c6bb1",
            text_color="#ffffff",
            stack_order=2,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_prof,
            field="tasa_gobierno",
            is_percentage=False,
            name="Tasa gobierno",
            icon="fas fa-landmark",
            color="#4d004b",
            size="1",
            edge_style="7",
            edge_color="#810f7c",
            text_color="#ffffff",
            stack_order=3,
        )

    # ── Grupo 2: Sectores Economicos ───────────────────────────────────────
    g_sect, _ = IndicatorGroup.objects.get_or_create(
        site=site,
        name="Sectores Economicos",
        defaults={
            "description": "Distribucion de posgrados por sector economico de ocupacion",
            "info_text": (
                "Comparativa de la tasa de posgrado entre diferentes sectores "
                "economicos. Fuente: ENOE 2024-I."
            ),
            "stack_order": 2,
        },
    )

    sg_mfg, _ = SubGroup.objects.get_or_create(
        group=g_sect,
        name="Industria manufacturera",
        defaults={
            "info_text": "Insercion de posgrados en la industria manufacturera.",
            "icon": "fas fa-industry",
            "stack_order": 1,
        },
    )

    plot_mfg, map_mfg = _group_plot_map(
        df_enoe, "NOMGEO", "tasa_industria_manufacturera", "CVE_ENT", PALETTE_GREENS
    )

    ind_mfg = Indicator.objects.filter(
        subgroup=sg_mfg, name="Tasa de posgrado en industria manufacturera"
    ).first()
    if not ind_mfg:
        mfg_labels = [pv["label"] for pv in plot_mfg]
        mfg_colors = [pv["color"] for pv in plot_mfg]
        ind_mfg = Indicator.objects.create(
            subgroup=sg_mfg,
            name="Tasa de posgrado en industria manufacturera",
            plot_type="bar",
            info_text="Porcentaje de trabajadores manufactureros con grado de posgrado por estado.",
            layer=layer_enoe,
            layer_id_field="cve_ent",
            layer_nom_field="NOMGEO",
            high_values_percentage=10,
            use_single_field=False,
            field_one="NOMGEO",
            field_two="tasa_industria_manufacturera",
            field_popup=["NOMGEO", "tasa_industria_manufacturera", "total_posgrado_entidad"],
            category_method="quantil",
            field_category=5,
            colors="verdes_2",
            use_custom_colors=False,
            plot_config={
                "chart_type": "treemap",
                "field_one": "NOMGEO",
                "field_two": "tasa_industria_manufacturera",
                "method": "quantil",
                "categories": 5,
                "ranges": [
                    {
                        "label": mfg_labels[i],
                        "alias": mfg_labels[i],
                        "color": mfg_colors[i],
                        "count": 1,
                    }
                    for i in range(min(5, len(plot_mfg)))
                ],
            },
            plot_values=plot_mfg,
            map_values=map_mfg,
            general_values={
                "tasa_industria_manufacturera": round(
                    float(df_enoe["tasa_industria_manufacturera"].mean()), 2
                ),
                "tasa_comercio": round(float(df_enoe["tasa_comercio"].mean()), 2),
            },
            show_general_values=True,
            use_filter=True,
            filters=[
                {"field": "region", "label": "Region", "values": ["Norte", "Centro", "Sur"]}
            ],
            stack_order=1,
        )
    else:
        ind_mfg.general_values = {
            "tasa_industria_manufacturera": round(
                float(df_enoe["tasa_industria_manufacturera"].mean()), 2
            ),
            "tasa_comercio": round(float(df_enoe["tasa_comercio"].mean()), 2),
        }
        ind_mfg.save(update_fields=["general_values"])

    if not ind_mfg.infoboxes.exists():
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_mfg,
            field="tasa_industria_manufacturera",
            is_percentage=False,
            name="Tasa manufactura (%)",
            icon="fas fa-industry",
            color="#006d2c",
            size="2",
            edge_style="7",
            edge_color="#41ae76",
            text_color="#ffffff",
            stack_order=1,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_mfg,
            field="tasa_comercio",
            is_percentage=False,
            name="Tasa comercio (%)",
            icon="fas fa-store",
            color="#238b45",
            size="1",
            edge_style="5",
            edge_color="#66c2a4",
            text_color="#ffffff",
            stack_order=2,
        )

    return site


# ---------------------------------------------------------------------------
# Sitio 2: Movilidad Estudiantil
# ---------------------------------------------------------------------------

def create_movilidad_site(layer_name_od):
    df_od = _load_od()
    layer_od = _resolve_layer(layer_name_od) if layer_name_od else None

    site, _ = Site.objects.get_or_create(
        name="Movilidad Estudiantil Universitaria",
        defaults={
            "title": "Movilidad Estudiantil Universitaria en Mexico",
            "subtitle": (
                "Flujos de origen-destino de estudiantes de licenciatura, "
                "maestria y doctorado por entidad federativa"
            ),
            "url": "/dashboard/movilidad",
            "info_text": (
                "Datos de movilidad estudiantil interestatal en instituciones de "
                "educacion superior publica (IES). Muestra cuantos estudiantes de "
                "cada estado acuden a instituciones en otros estados. "
                "Fuente: ANUIES / SEP."
            ),
        },
    )

    SiteConfiguration.objects.get_or_create(
        site=site,
        defaults={
            "show_header": True,
            "show_footer": True,
            "header_background_color": "#E65100",
            "header_text_color": "#ffffff",
            "header_font_size": 24,
            "site_font_style": "Poppins",
            "site_text_color": "#212121",
            "site_interface_text_color": "#212121",
            "site_background_color": "#FFF3E0",
            "site_interface_background_color": "#ffffff",
            "site_font_size": 15,
            "indicator_box_title": "Indicador de movilidad",
        },
    )

    # ── Grupo 1: Flujos totales ───────────────────────────────────────────
    g_total, _ = IndicatorGroup.objects.get_or_create(
        site=site,
        name="Flujos Estudiantiles Totales",
        defaults={
            "description": "Numero de estudiantes que se movilizan desde cada estado a otras entidades",
            "info_text": (
                "Total de estudiantes matriculados en IES fuera de su entidad de origen, "
                "sumando todos los niveles (licenciatura, maestria y doctorado)."
            ),
            "stack_order": 1,
        },
    )

    sg_total, _ = SubGroup.objects.get_or_create(
        group=g_total,
        name="Todos los niveles educativos",
        defaults={
            "info_text": "Flujo total de estudiantes (licenciatura + maestria + doctorado).",
            "icon": "fas fa-university",
            "stack_order": 1,
        },
    )

    plot_od, map_od, labels_od, bins_od = _quantile_plot_map(
        df_od, "total_outgoing", "cve_ent", "nombre_entidad", PALETTE_NARANJAS
    )

    ind_total = Indicator.objects.filter(
        subgroup=sg_total, name="Clasificacion estatal por flujo estudiantil total"
    ).first()
    if not ind_total:
        ind_total = Indicator.objects.create(
            subgroup=sg_total,
            name="Clasificacion estatal por flujo estudiantil total",
            plot_type="bar",
            info_text=(
                "Numero de estudiantes que se movilizan desde cada estado a "
                "otras entidades, todos los niveles educativos."
            ),
            layer=layer_od,
            layer_id_field="cve_ent",
            layer_nom_field="nombre_entidad",
            high_values_percentage=10,
            use_single_field=True,
            field_one="total_outgoing",
            field_two="",
            field_popup=["nombre_entidad", "total_outgoing"],
            category_method="quantil",
            field_category=5,
            colors="naranjas",
            use_custom_colors=False,
            plot_config={
                "chart_type": "donut",
                "field_one": "total_outgoing",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_od,
                "ranges": [
                    {
                        "label": labels_od[i],
                        "alias": labels_od[i],
                        "color": PALETTE_NARANJAS[i],
                        "count": plot_od[i]["value"],
                    }
                    for i in range(len(labels_od))
                ],
            },
            plot_values=plot_od,
            map_values=map_od,
            general_values={
                "total_outgoing": int(df_od["total_outgoing"].sum()),
                "PU_CDMX": int(df_od["PU_CDMX"].sum()),
                "PU_NL": int(df_od["PU_NL"].sum()),
            },
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )
    else:
        ind_total.general_values = {
            "total_outgoing": int(df_od["total_outgoing"].sum()),
            "PU_CDMX": int(df_od["PU_CDMX"].sum()),
            "PU_NL": int(df_od["PU_NL"].sum()),
        }
        if not ind_total.plot_config or not ind_total.plot_config.get("ranges"):
            ind_total.plot_config = {
                "chart_type": "donut",
                "field_one": "total_outgoing",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_od,
                "ranges": [
                    {
                        "label": labels_od[i],
                        "alias": labels_od[i],
                        "color": PALETTE_NARANJAS[i],
                        "count": plot_od[i]["value"],
                    }
                    for i in range(len(labels_od))
                ],
            }
            ind_total.plot_values = plot_od
            ind_total.map_values = map_od
        ind_total.save(update_fields=["general_values", "plot_config", "plot_values", "map_values"])

    if not ind_total.infoboxes.exists():
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_total,
            field="total_outgoing",
            is_percentage=False,
            name="Estudiantes en movilidad",
            icon="fas fa-user-graduate",
            color="#E65100",
            size="2",
            edge_style="7",
            edge_color="#FF8F00",
            text_color="#ffffff",
            stack_order=1,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_total,
            field="PU_CDMX",
            is_percentage=False,
            name="Hacia Ciudad de Mexico",
            icon="fas fa-map-marker-alt",
            color="#b30000",
            size="1",
            edge_style="5",
            edge_color="#ef6548",
            text_color="#ffffff",
            stack_order=2,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_total,
            field="PU_NL",
            is_percentage=False,
            name="Hacia Nuevo Leon",
            icon="fas fa-map-marker-alt",
            color="#d7301f",
            size="1",
            edge_style="5",
            edge_color="#fc8d59",
            text_color="#ffffff",
            stack_order=3,
        )

    # ── Grupo 2: Por nivel educativo ──────────────────────────────────────
    g_nivel, _ = IndicatorGroup.objects.get_or_create(
        site=site,
        name="Movilidad por Nivel Educativo",
        defaults={
            "description": (
                "Flujos estudiantiles desglosados por nivel: "
                "licenciatura, maestria y doctorado"
            ),
            "info_text": (
                "Comparativa de la movilidad interestatal segun el nivel de estudios."
            ),
            "stack_order": 2,
        },
    )

    for nivel_name, nivel_icon, nivel_col_prefix, palette, nivel_order, nivel_chart in [
        ("Licenciatura", "fas fa-book", "PU_CDMX", PALETTE_BLUES, 1, "horizontal_bar"),
        ("Maestria", "fas fa-book-open", "PU_CDMX", PALETTE_PURPLES, 2, "bar"),
        ("Doctorado", "fas fa-microscope", "PU_CDMX", PALETTE_GREENS, 3, "treemap"),
    ]:
        sg_nivel, _ = SubGroup.objects.get_or_create(
            group=g_nivel,
            name=nivel_name,
            defaults={
                "info_text": (
                    f"Flujo de estudiantes de {nivel_name.lower()} "
                    "que estudian fuera de su estado."
                ),
                "icon": nivel_icon,
                "stack_order": nivel_order,
            },
        )

        ind_name = f"Flujo de {nivel_name.lower()} por estado origen"
        plot_niv, map_niv, labels_niv, bins_niv = _quantile_plot_map(
            df_od, "total_outgoing", "cve_ent", "nombre_entidad", palette
        )

        ind_niv = Indicator.objects.filter(
            subgroup=sg_nivel, name=ind_name
        ).first()
        if not ind_niv:
            ind_niv = Indicator.objects.create(
                subgroup=sg_nivel,
                name=ind_name,
                plot_type="bar",
                info_text=(
                    f"Estudiantes de {nivel_name.lower()} que estudian "
                    "fuera de su entidad de origen."
                ),
                layer=layer_od,
                layer_id_field="cve_ent",
                layer_nom_field="nombre_entidad",
                high_values_percentage=10,
                use_single_field=True,
                field_one="total_outgoing",
                field_two="",
                field_popup=["nombre_entidad", "total_outgoing"],
                category_method="quantil",
                field_category=5,
                colors="azules",
                use_custom_colors=False,
                plot_config={
                    "chart_type": nivel_chart,
                    "field_one": "total_outgoing",
                    "method": "quantil",
                    "categories": 5,
                    "bin_edges": bins_niv,
                    "ranges": [
                        {
                            "label": labels_niv[i],
                            "alias": labels_niv[i],
                            "color": palette[i],
                            "count": plot_niv[i]["value"],
                        }
                        for i in range(len(labels_niv))
                    ],
                },
                plot_values=plot_niv,
                map_values=map_niv,
                general_values={
                    "total_outgoing": int(df_od["total_outgoing"].sum()),
                    "PU_CDMX": int(df_od["PU_CDMX"].sum()),
                },
                show_general_values=True,
                use_filter=False,
                filters=None,
                stack_order=nivel_order,
            )
        else:
            ind_niv.general_values = {
                "total_outgoing": int(df_od["total_outgoing"].sum()),
                "PU_CDMX": int(df_od["PU_CDMX"].sum()),
            }
            ind_niv.save(update_fields=["general_values"])

        if not ind_niv.infoboxes.exists():
            IndicatorFieldBoxInfo.objects.create(
                indicator=ind_niv,
                field="total_outgoing",
                is_percentage=False,
                name=f"Estudiantes de {nivel_name.lower()}",
                icon=nivel_icon,
                color=palette[0],
                size="2",
                edge_style="7",
                edge_color=palette[2],
                text_color="#ffffff",
                stack_order=1,
            )
            IndicatorFieldBoxInfo.objects.create(
                indicator=ind_niv,
                field="PU_CDMX",
                is_percentage=False,
                name="Hacia CDMX",
                icon="fas fa-map-pin",
                color=palette[1],
                size="1",
                edge_style="5",
                edge_color=palette[3],
                text_color="#ffffff",
                stack_order=2,
            )

    return site


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Crea dos sitios de dashboard con datos representativos de educacion superior"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Elimina los sitios de ejemplo antes de recrearlos",
        )
        parser.add_argument(
            "--layer-name-enoe",
            default="ent_2024",
            help="Nombre de la capa ENOE en GeoNode (default: ent_2024)",
        )
        parser.add_argument(
            "--layer-name-od",
            default="ent_2024",
            help="Nombre base de capas origen-destino (default: ent_2024)",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            names = [
                "Posgrados y Mercado Laboral",
                "Movilidad Estudiantil Universitaria",
                "Monitoreo Climatico Nacional",
                "Demografia y Urbanizacion",
            ]
            deleted, _ = Site.objects.filter(name__in=names).delete()
            self.stdout.write(self.style.WARNING(f"Eliminados {deleted} registros previos."))

        lname_enoe = options["layer_name_enoe"]
        lname_od = options["layer_name_od"]

        self.stdout.write("Creando sitio 1: Posgrados y Mercado Laboral...")
        s1 = create_posgrados_site(lname_enoe)
        self.stdout.write(self.style.SUCCESS(f"  '{s1.name}' (id={s1.id}) listo."))

        self.stdout.write("Creando sitio 2: Movilidad Estudiantil...")
        s2 = create_movilidad_site(lname_od)
        self.stdout.write(self.style.SUCCESS(f"  '{s2.name}' (id={s2.id}) listo."))

        self.stdout.write(self.style.SUCCESS("\nDashboards creados correctamente."))
        self.stdout.write(
            f"  - Posgrados  -> /api/v2/dashboard/sites/{s1.id}/\n"
            f"  - Movilidad  -> /api/v2/dashboard/sites/{s2.id}/"
        )
