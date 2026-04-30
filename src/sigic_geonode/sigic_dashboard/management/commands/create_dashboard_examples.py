# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Crea dos sitios de dashboard de ejemplo con datos reales de educacion
superior, ligados a capas GeoNode ya importadas:

  Sitio 1: Posgrados y Mercado Laboral  (capa enoe_25_I_posgrado)
  Sitio 2: Movilidad Estudiantil        (capas origen_destino_PU_*)

Uso:
    python manage.py create_dashboard_examples
    python manage.py create_dashboard_examples --flush
    python manage.py create_dashboard_examples --layer-name-enoe <name> --layer-name-od <name>
"""

import sqlite3

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
# Constantes
# ---------------------------------------------------------------------------

GPKG_BASE = "/tmp/capas_prueba"

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
# Helpers de calculo
# ---------------------------------------------------------------------------

def _quantile_plot_map(df, value_col, id_col, name_col, palette, n=5):
    """
    Clasifica value_col en n cuantiles y devuelve (plot_values, map_values).
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
# Carga de datos desde GPKG
# ---------------------------------------------------------------------------

def _load_enoe(gpkg_path):
    conn = sqlite3.connect(gpkg_path)
    df = pd.read_sql(
        """SELECT CVE_ENT, NOMGEO,
               tasa_general_entidad, total_posgrado_entidad, total_poblacion_entidad,
               tasa_servicios_profesionales, tasa_servicios_sociales, tasa_gobierno,
               tasa_industria_manufacturera, tasa_comercio
           FROM ent_2024""",
        conn,
    )
    conn.close()
    return df


def _load_od(gpkg_path, prefix="PU_"):
    conn = sqlite3.connect(gpkg_path)
    df = pd.read_sql("SELECT * FROM cat_estadogeom_1", conn)
    conn.close()
    pu_cols = [c for c in df.columns if c.startswith(prefix) and c != prefix]
    df["total_outgoing"] = df[pu_cols].sum(axis=1)
    return df


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
    df_enoe = _load_enoe(f"{GPKG_BASE}/enoe_25_I_posgrado.gpkg")
    layer_enoe = _resolve_layer(layer_name_enoe) if layer_name_enoe else None

    site, _ = Site.objects.get_or_create(
        name="Posgrados y Mercado Laboral",
        defaults={
            "title": "Posgrados y Mercado Laboral en Mexico",
            "subtitle": (
                "Insercion laboral de personas con estudios de posgrado "
                "por entidad federativa y sector economico (ENOE 2025-I)"
            ),
            "url": "/dashboard/posgrados",
            "info_text": (
                "Indicadores de ocupacion y tasa de posgrado por sector economico "
                "basados en la Encuesta Nacional de Ocupacion y Empleo (ENOE), "
                "primer trimestre 2025. Fuente: INEGI / CONAHCYT."
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
                "Clasificacion por cuantiles (ENOE 2025-I)."
            ),
            layer=layer_enoe,
            layer_id_field="CVE_ENT",
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
                "field_one": "tasa_general_entidad",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_tasa,
            },
            plot_values=plot_tasa,
            map_values=map_tasa,
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )

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
        ind_prof = Indicator.objects.create(
            subgroup=sg_prof,
            name="Tasa de posgrado en servicios profesionales por estado",
            plot_type="bar",
            info_text=(
                "Porcentaje de ocupados en servicios profesionales que tienen "
                "grado de posgrado, por entidad federativa."
            ),
            layer=layer_enoe,
            layer_id_field="CVE_ENT",
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
                "field_one": "NOMGEO",
                "field_two": "tasa_servicios_profesionales",
                "method": "quantil",
                "categories": 5,
            },
            plot_values=plot_prof,
            map_values=map_prof,
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )

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
                "economicos. Fuente: ENOE 2025-I."
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
        ind_mfg = Indicator.objects.create(
            subgroup=sg_mfg,
            name="Tasa de posgrado en industria manufacturera",
            plot_type="bar",
            info_text="Porcentaje de trabajadores manufactureros con grado de posgrado por estado.",
            layer=layer_enoe,
            layer_id_field="CVE_ENT",
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
                "field_one": "NOMGEO",
                "field_two": "tasa_industria_manufacturera",
                "method": "quantil",
                "categories": 5,
            },
            plot_values=plot_mfg,
            map_values=map_mfg,
            show_general_values=True,
            use_filter=True,
            filters=[
                {"field": "region", "label": "Region", "values": ["Norte", "Centro", "Sur"]}
            ],
            stack_order=1,
        )

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

def create_movilidad_site(layer_name_od, layer_name_lic, layer_name_maes, layer_name_doc):
    df_od = _load_od(f"{GPKG_BASE}/origen_destino_PU.gpkg", prefix="PU_")
    df_lic = _load_od(f"{GPKG_BASE}/origen_destino_PU_licenciatura.gpkg", prefix="PU_L_")
    df_maes = _load_od(f"{GPKG_BASE}/origen_destino_PU_maestria.gpkg", prefix="PU_M_")
    df_doc = _load_od(f"{GPKG_BASE}/origen_destino_PU_doctorado.gpkg", prefix="PU_D_")

    layer_od = _resolve_layer(layer_name_od) if layer_name_od else None
    layer_lic = _resolve_layer(layer_name_lic) if layer_name_lic else None
    layer_maes = _resolve_layer(layer_name_maes) if layer_name_maes else None
    layer_doc = _resolve_layer(layer_name_doc) if layer_name_doc else None

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
                "field_one": "total_outgoing",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_od,
            },
            plot_values=plot_od,
            map_values=map_od,
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )

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
            "description": "Flujos estudiantiles desglosados por nivel: licenciatura, maestria y doctorado",
            "info_text": "Comparativa de la movilidad interestatal segun el nivel de estudios.",
            "stack_order": 2,
        },
    )

    # SubGrupo Licenciatura
    sg_lic, _ = SubGroup.objects.get_or_create(
        group=g_nivel,
        name="Licenciatura",
        defaults={
            "info_text": "Flujo de estudiantes de licenciatura que estudian fuera de su estado.",
            "icon": "fas fa-book",
            "stack_order": 1,
        },
    )
    plot_lic, map_lic, labels_lic, bins_lic = _quantile_plot_map(
        df_lic, "total_outgoing", "cve_ent", "nombre_entidad", PALETTE_BLUES
    )
    ind_lic = Indicator.objects.filter(
        subgroup=sg_lic, name="Flujo de licenciatura por estado origen"
    ).first()
    if not ind_lic:
        ind_lic = Indicator.objects.create(
            subgroup=sg_lic,
            name="Flujo de licenciatura por estado origen",
            plot_type="bar",
            info_text="Estudiantes de licenciatura que estudian fuera de su entidad de origen.",
            layer=layer_lic,
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
                "field_one": "total_outgoing",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_lic,
            },
            plot_values=plot_lic,
            map_values=map_lic,
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )
    if not ind_lic.infoboxes.exists():
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_lic,
            field="total_outgoing",
            is_percentage=False,
            name="Estudiantes de licenciatura",
            icon="fas fa-book",
            color="#084081",
            size="2",
            edge_style="7",
            edge_color="#2b8cbe",
            text_color="#ffffff",
            stack_order=1,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_lic,
            field="PU_L_CDMX",
            is_percentage=False,
            name="Hacia CDMX (lic.)",
            icon="fas fa-map-pin",
            color="#0868ac",
            size="1",
            edge_style="5",
            edge_color="#4eb3d3",
            text_color="#ffffff",
            stack_order=2,
        )

    # SubGrupo Maestria
    sg_maes, _ = SubGroup.objects.get_or_create(
        group=g_nivel,
        name="Maestria",
        defaults={
            "info_text": "Flujo de estudiantes de maestria que estudian fuera de su estado.",
            "icon": "fas fa-book-open",
            "stack_order": 2,
        },
    )
    plot_maes, map_maes, labels_maes, bins_maes = _quantile_plot_map(
        df_maes, "total_outgoing", "cve_ent", "nombre_entidad", PALETTE_PURPLES
    )
    ind_maes = Indicator.objects.filter(
        subgroup=sg_maes, name="Flujo de maestria por estado origen"
    ).first()
    if not ind_maes:
        ind_maes = Indicator.objects.create(
            subgroup=sg_maes,
            name="Flujo de maestria por estado origen",
            plot_type="bar",
            info_text="Estudiantes de maestria que estudian fuera de su entidad de origen.",
            layer=layer_maes,
            layer_id_field="cve_ent",
            layer_nom_field="nombre_entidad",
            high_values_percentage=10,
            use_single_field=True,
            field_one="total_outgoing",
            field_two="",
            field_popup=["nombre_entidad", "total_outgoing"],
            category_method="quantil",
            field_category=5,
            colors="morados",
            use_custom_colors=False,
            plot_config={
                "field_one": "total_outgoing",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_maes,
            },
            plot_values=plot_maes,
            map_values=map_maes,
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )
    if not ind_maes.infoboxes.exists():
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_maes,
            field="total_outgoing",
            is_percentage=False,
            name="Estudiantes de maestria",
            icon="fas fa-book-open",
            color="#810f7c",
            size="2",
            edge_style="7",
            edge_color="#dd3497",
            text_color="#ffffff",
            stack_order=1,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_maes,
            field="PU_M_CDMX",
            is_percentage=False,
            name="Hacia CDMX (maes.)",
            icon="fas fa-map-pin",
            color="#88419d",
            size="1",
            edge_style="5",
            edge_color="#8c96c6",
            text_color="#ffffff",
            stack_order=2,
        )

    # SubGrupo Doctorado
    sg_doc, _ = SubGroup.objects.get_or_create(
        group=g_nivel,
        name="Doctorado",
        defaults={
            "info_text": "Flujo de estudiantes de doctorado que estudian fuera de su estado.",
            "icon": "fas fa-microscope",
            "stack_order": 3,
        },
    )
    plot_doc, map_doc, labels_doc, bins_doc = _quantile_plot_map(
        df_doc, "total_outgoing", "cve_ent", "nombre_entidad", PALETTE_GREENS
    )
    ind_doc = Indicator.objects.filter(
        subgroup=sg_doc, name="Flujo de doctorado por estado origen"
    ).first()
    if not ind_doc:
        ind_doc = Indicator.objects.create(
            subgroup=sg_doc,
            name="Flujo de doctorado por estado origen",
            plot_type="bar",
            info_text="Estudiantes de doctorado que estudian fuera de su entidad de origen.",
            layer=layer_doc,
            layer_id_field="cve_ent",
            layer_nom_field="nombre_entidad",
            high_values_percentage=10,
            use_single_field=True,
            field_one="total_outgoing",
            field_two="",
            field_popup=["nombre_entidad", "total_outgoing"],
            category_method="quantil",
            field_category=5,
            colors="verdes_2",
            use_custom_colors=False,
            plot_config={
                "field_one": "total_outgoing",
                "method": "quantil",
                "categories": 5,
                "bin_edges": bins_doc,
            },
            plot_values=plot_doc,
            map_values=map_doc,
            show_general_values=True,
            use_filter=False,
            filters=None,
            stack_order=1,
        )
    if not ind_doc.infoboxes.exists():
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_doc,
            field="total_outgoing",
            is_percentage=False,
            name="Estudiantes de doctorado",
            icon="fas fa-microscope",
            color="#006d2c",
            size="2",
            edge_style="7",
            edge_color="#41ae76",
            text_color="#ffffff",
            stack_order=1,
        )
        IndicatorFieldBoxInfo.objects.create(
            indicator=ind_doc,
            field="PU_D_CDMX",
            is_percentage=False,
            name="Hacia CDMX (doc.)",
            icon="fas fa-map-pin",
            color="#238b45",
            size="1",
            edge_style="5",
            edge_color="#66c2a4",
            text_color="#ffffff",
            stack_order=2,
        )

    return site


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Crea dos sitios de dashboard con datos reales de educacion superior"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Elimina los sitios de ejemplo antes de recrearlos")
        parser.add_argument("--layer-name-enoe", default="ent_2024",
                            help="Nombre de la capa ENOE en GeoNode (default: ent_2024)")
        parser.add_argument("--layer-name-od", default="cat_estadogeom_1",
                            help="Nombre base de capas origen-destino (default: cat_estadogeom_1)")

    def handle(self, *args, **options):
        if options["flush"]:
            names = [
                "Posgrados y Mercado Laboral",
                "Movilidad Estudiantil Universitaria",
                # ejemplos anteriores
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
        s2 = create_movilidad_site(lname_od, lname_od, lname_od, lname_od)
        self.stdout.write(self.style.SUCCESS(f"  '{s2.name}' (id={s2.id}) listo."))

        self.stdout.write(self.style.SUCCESS("\nDashboards creados correctamente."))
        self.stdout.write(
            f"  - Posgrados  → /api/v2/dashboard/sites/{s1.id}/\n"
            f"  - Movilidad  → /api/v2/dashboard/sites/{s2.id}/"
        )
