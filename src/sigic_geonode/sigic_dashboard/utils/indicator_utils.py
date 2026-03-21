# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

# -*- encoding: utf-8 -*-
import traceback

import jenkspy
import numpy as np
import pandas as pd
import psycopg2

from django.conf import settings


def get_data_from_db(attributes, field_id, table_name):
    """
    Hace un query a la base de datos recuperando
    la tabla de atributos de la capa asociada al indicador.

    Params:
        attributes (list or string): El campo de atributos de la capa por los cuales
                                     se quiere hacer el filtrado y construir la data.
        field_id (string):           El campo id que identifica a las geometrias.
        table_name (string):         El nombre de la capa (tabla de atributos en la db).

    Return:
        (list): Lista de tuplas con los atributos de la capa.
    """
    db = settings.DATABASES["geonode_data"]
    conn = psycopg2.connect(
        dbname=db["NAME"],
        user=db["USER"],
        password=db["PASSWORD"],
        port=db["PORT"],
        host=db["HOST"],
    )

    try:
        cur = conn.cursor()

        if isinstance(attributes, list):
            fields = (
                '"'
                + attributes[0]
                + '","'
                + attributes[1]
                + '","'
                + field_id
                + '"'
            )
        else:
            fields = '"' + attributes + '","' + field_id + '"'

        cur.execute("select %s from %s;" % (fields, table_name))
        results = cur.fetchall()
        return results
    except Exception as e:
        print(e)
    finally:
        conn.close()


def gen_data_dicts(indicadores, attributes, field_id):
    """
    Genera los diccionarios de datos para las graficas
    y la tematizacion de las capas.

    Params:
        indicadores (list): Lista de diccionarios con los datos ya procesados.
        attributes (list or string): Campos de atributos de la capa.
        field_id (string): Campo id que identifica a las geometrias.

    Returns:
        (list): [theming_data, plot_data]
    """
    if isinstance(attributes, list):
        layer_value = attributes[0]
        plot_value = attributes[1]
    else:
        layer_value = attributes
        plot_value = "one_field"

    plot_data = []
    for idx, i in enumerate(indicadores):
        plot_data.append(
            {"sortPosition": idx + 1, "label": i[layer_value], "value": i[plot_value]}
        )

    theming_data = {}
    for i in indicadores:
        for j in i[field_id]:
            theming_data[j] = {"value": i[layer_value]}

    return [theming_data, plot_data]


def is_number_repl_isdigit(s):
    """Regresa True si la cadena es un numero."""
    return s.replace(".", "", 1).isdigit()


def change_header_labels(df):
    """
    Cambia el nombre de los headers de un dataframe
    del formato "(number, number]" a "number a number".
    """
    df.columns = [str(x).replace("(", "") for x in df.columns]
    df.columns = [str(x).replace("]", "") for x in df.columns]
    df.columns = [str(x).replace(", ", "   -   ") for x in df.columns]
    return df


def process_data(data, attributes, field_id, method, categories, indicator, manual_bins):
    """
    Procesa la data de la capa para generar los datos del indicador.

    Params:
        data (list):                    Datos de la capa (lista de tuplas).
        attributes (list or string):    Campos de atributos.
        field_id (string):              Campo id de geometrias.
        method (string):                Metodo de clasificacion (quantil/naturalb/sameintervals/manual).
        categories (int):               Numero de categorias.
        indicator (object):             Instancia del modelo Indicator.
        manual_bins (list):             Bins manuales (para method='manual').

    Return:
        (dict): {"plot_data": [...], "theming_data": {...}} o {"error": "..."}
    """
    if isinstance(attributes, list):
        df = pd.DataFrame(data, columns=[attributes[0], attributes[1], field_id])
    else:
        df = pd.DataFrame(data, columns=[attributes, field_id])

    try:
        if not indicator.use_single_field and isinstance(attributes, list):
            df_temp = df.groupby(attributes[0])[attributes[1]].sum().reset_index()
            df_temp[[attributes[0]]] = df_temp[[attributes[0]]].astype(str)

            df_temp2 = (
                df.groupby(attributes[0])[field_id]
                .apply(list)
                .reset_index(name=field_id)
            )
            df_temp2[[attributes[0]]] = df_temp2[[attributes[0]]].astype(str)

            indicadores = pd.merge(df_temp, df_temp2, on=attributes[0]).to_dict(
                "records"
            )
            data_dicts = gen_data_dicts(indicadores, attributes, field_id)

            return {"plot_data": data_dicts[1], "theming_data": data_dicts[0]}

        else:
            if np.issubdtype(df[attributes].dtype, object):
                df[attributes] = df[attributes].astype(str)

                if df[attributes].str.contains(r"\[.*\]").any():
                    df[attributes] = df[attributes].str.strip("[]")
                    df[attributes] = pd.to_numeric(df[attributes], errors="coerce")

            if np.issubdtype(df[attributes].dtype, np.number):
                df_temp = df[[attributes]]
                df_nbreaks = df_temp[attributes].dropna()

                df_tmp = None
                if method == "quantil":
                    bins = pd.qcut(df_temp[attributes], q=categories, duplicates="drop")
                    if len(bins.cat.categories) < categories:
                        custom_cat = categories + 1
                        while len(bins.cat.categories) < categories:
                            bins = pd.qcut(
                                df_temp[attributes], q=custom_cat, duplicates="drop"
                            )
                            custom_cat += 1
                    df_tmp = pd.get_dummies(bins)
                elif method == "naturalb":
                    df_tmp = pd.get_dummies(
                        pd.cut(
                            df_temp[attributes],
                            bins=jenkspy.jenks_breaks(
                                np.array(df_nbreaks), n_classes=categories
                            ),
                            include_lowest=True,
                        )
                    )
                elif method == "sameintervals":
                    min_value = df_nbreaks.min()
                    max_value = df_nbreaks.max()
                    bins = np.linspace(min_value, max_value, categories + 1)
                    df_tmp = pd.get_dummies(
                        pd.cut(df_temp[attributes], bins=bins, include_lowest=True)
                    )
                elif method == "manual":
                    df_tmp = pd.get_dummies(
                        pd.cut(df_temp[attributes], bins=manual_bins)
                    )

                change_header_labels(df_tmp)

                df_temp = df_temp[[attributes]].join(df_tmp)
                df_temp = df_temp.drop([attributes], axis=1).sum().to_frame(name="one_field")
                df_temp.index.name = attributes
                df_temp = df_temp.reset_index()

                df_temp2 = df[[field_id]].join(df_tmp)
                df_temp2.replace(False, np.nan, inplace=True)
                df_temp2 = df_temp2.mask(
                    df_temp2.notnull(), df_temp2.pop(field_id), axis=0
                )
                df_temp2 = df_temp2.apply(
                    lambda s: s.fillna({i: [] for i in df_temp2.index})
                )
                df_temp2 = df_temp2.map(
                    lambda s: [s] if not isinstance(s, list) else s
                )
                df_temp2 = df_temp2.sum().to_frame(name=field_id)
                df_temp2.index.name = attributes
                df_temp2 = df_temp2.reset_index()
                indicadores = (
                    pd.merge(df_temp, df_temp2, on=attributes)
                    .iloc[::-1]
                    .to_dict("records")
                )

                data_dicts = gen_data_dicts(indicadores, attributes, field_id)
            else:
                df_temp = df.groupby(attributes).size().reset_index(name="one_field")
                df_temp = df_temp.replace(to_replace="None", value=np.nan).dropna()
                df_temp = df_temp[df_temp[attributes] != ""]
                df_temp[[attributes]] = df_temp[[attributes]].astype(str)
                df_temp2 = (
                    df.groupby(attributes)[field_id]
                    .apply(list)
                    .reset_index(name=field_id)
                )
                df_temp2[[attributes]] = df_temp2[[attributes]].astype(str)
                indicadores = pd.merge(
                    df_temp.iloc[::-1], df_temp2.iloc[::-1], on=attributes
                ).to_dict("records")

                data_dicts = gen_data_dicts(indicadores, attributes, field_id)

            return {"plot_data": data_dicts[1], "theming_data": data_dicts[0]}

    except Exception:
        print("ERROR AT INDICATOR " + str(indicator.name) + ":")
        print(traceback.format_exc())
        return {"error": "No es posible generar datos para los campos y el metodo elegido"}


def get_color_palette(palette_name):
    colors_palette = {
        "azules": ["#084081", "#0868ac", "#2b8cbe", "#4eb3d3", "#7bccc4", "#a8ddb5", "#ccebc5", "#e0f3db", "#f7fcf0"],
        "azules_2": ["#023858", "#045a8d", "#0570b0", "#3690c0", "#74a9cf", "#a6bddb", "#d0d1e6", "#ece7f2", "#fff7fb"],
        "azules_3": ["#081d58", "#253494", "#225ea8", "#1d91c0", "#41b6c4", "#7fcdbb", "#c7e9b4", "#edf8b1", "#ffffd9"],
        "azules_4": ["#0a5066", "#206880", "#3a859e", "#6caec4", "#b1e6e6", "#edf8b1", "#ffffe5"],
        "azules_5": ["#052731", "#06313E", "#073B4B", "#094558", "#0A4F65", "#156579", "#227C8F", "#2F94A5", "#3BABBA", "#4EBBC2", "#66C4BE", "#7ECDBA", "#A5DBC8", "#B0E0B1", "#CDEBAD", "#EAF7A8", "#FFFF9B", "#FFFFC1", "#FFFFE1", "#FFFFF3"],
        "cafes": ["#663b14", "#a85411", "#dc7a2d", "#ff9b4d", "#ffc699", "#fec44f", "#fee391", "#fff7bc", "#ffffe5"],
        "cafes_2": ["#80541e", "#c47318", "#e89638", "#ffaf54", "#ffcf99", "#feb24c", "#fed976", "#ffeda0", "#ffffcc"],
        "cafes_3": ["#916f24", "#cc8d14", "#edb342", "#ffcb66", "#ffdc99", "#ffeda0", "#ffffcc"],
        "cafes_verdes": ["#543005", "#8c510a", "#bf812d", "#dfc27d", "#f6e8c3", "#f5f5f5", "#c7eae5", "#80cdc1", "#35978f", "#01665e", "#003c30"],
        "grises": ["#000000", "#252525", "#525252", "#737373", "#969696", "#bdbdbd", "#d9d9d9", "#f0f0f0", "#ffffff"],
        "morados": ["#4d004b", "#810f7c", "#88419d", "#8c6bb1", "#8c96c6", "#9ebcda", "#bfd3e6", "#e0ecf4", "#f7fcfd"],
        "morados_2": ["#49006a", "#7a0177", "#ae017e", "#dd3497", "#f768a1", "#fa9fb5", "#fcc5c0", "#fde0dd", "#fff7f3"],
        "naranjas": ["#7f0000", "#b30000", "#d7301f", "#ef6548", "#fc8d59", "#fdbb84", "#fdd49e", "#fee8c8", "#fff7ec"],
        "naranja_azul": ["#803411", "#b33900", "#e64e17", "#ff7c4d", "#ffb499", "#fddbc7", "#d1e5f0", "#92c5de", "#4393c3", "#2166ac", "#053061"],
        "rosa_verde": ["#8e0152", "#c51b7d", "#de77ae", "#f1b6da", "#fde0ef", "#f7f7f7", "#e6f5d0", "#b8e186", "#7fbc41", "#4d9221", "#276419"],
        "rosas": ["#67001f", "#980043", "#ce1256", "#e7298a", "#df65b0", "#c994c7", "#d4b9da", "#e7e1ef", "#f7f4f9"],
        "semaforo": ["#cbf7cb", "#a1e0ac", "#6ca66c", "#ffd373", "#ffa35c", "#ff6b36"],
        "semaforo_2": ["#cbf7cb", "#57dda6", "#31af7c", "#fcea92", "#fa741c", "#ed1f07"],
        "semaforo_3": ["#31af7c", "#ffd373", "#ed1f07"],
        "semaforo_4": ["#ff6b36", "#ffa35c", "#ffd373", "#6ca66c", "#a1e0ac", "#cbf7cb"],
        "semaforo_5": ["#ed1f07", "#fa741c", "#fcea92", "#31af7c", "#57dda6", "#cbf7cb"],
        "semaforo_6": ["#ed1f07", "#ffd373", "#31af7c"],
        "semaforo_7": ["#ff2200", "#ff9900", "#ffff00", "#7bab00", "#006100"],
        "semaforo_8": ["#006100", "#7bab00", "#ffff00", "#ff9900", "#ff2200"],
        "varios": ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f"],
        "varios_2": ["#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a", "#ffff99", "#b15928"],
        "varios_3": ["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43", "#d53e4f", "#9e0142"],
        "verdes": ["#7f825f", "#9e9e5c", "#cccc99", "#e3e3bf", "#f2f2c9", "#e1e5d6", "#f0f2ea"],
        "verdes_2": ["#00441b", "#006d2c", "#238b45", "#41ae76", "#66c2a4", "#99d8c9", "#ccece6", "#e5f5f9", "#f7fcfd"],
        "verdes_3": ["#546655", "#689468", "#99cc99", "#bfe0bf", "#d9f7d9", "#d9f0a3", "#f7fcb9", "#ffffe5"],
        "verdes_4": ["#004529", "#006837", "#238443", "#41ab5d", "#78c679", "#addd8e", "#d9f0a3", "#f7fcb9", "#ffffe5"],
        "verdes_5": ["#455448", "#56785c", "#81a888", "#9fcca7", "#b7e6bf", "#edf8b1", "#ffffe5"],
        "verdes_6": ["#204d49", "#266e68", "#4b9b94", "#6eb5af", "#a3d9d4", "#edf8b1", "#ffffe5"],
    }

    return colors_palette[palette_name]


def assign_color(data, color_selection, custom_colors=None):
    data_p = []
    color_dict = {}

    colors = custom_colors if custom_colors else get_color_palette(color_selection)

    for idx, d in enumerate(data["plot_data"]):
        d.update({"color": colors[idx]})
        data_p.append(d)
        color_dict[d["label"]] = colors[idx]

    data_c = {}
    for idx, d in enumerate(data["theming_data"]):
        data["theming_data"][d].update({"color": color_dict[data["theming_data"][d]["value"]]})
        data_c.update({d: data["theming_data"][d]})

    return {"plot_data": data_p, "theming_data": data_c}
