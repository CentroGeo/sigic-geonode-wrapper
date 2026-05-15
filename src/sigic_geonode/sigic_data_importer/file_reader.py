# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Lectura de archivos tabulares (CSV, Excel, JSON) a DataFrame.
"""

import json

import pandas as pd


def read_file_to_dataframe(file_path: str, file_format: str) -> pd.DataFrame:
    """Lee un archivo y retorna un DataFrame con dtype=str para preservar leading zeros."""
    if file_format == "csv":
        # dtype=str preserva leading zeros; low_memory=False para mejor inferencia
        return pd.read_csv(file_path, dtype=str, low_memory=False, encoding_errors="replace")
    elif file_format in ("xlsx", "xls"):
        return pd.read_excel(file_path, dtype=str)
    elif file_format == "json":
        with open(file_path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, list):
            return pd.DataFrame(data)
        # Si viene como {data: [...]} u otros wrappers comunes
        for key in ("data", "features", "results", "records", "items"):
            if key in data and isinstance(data[key], list):
                return pd.DataFrame(data[key])
        # Ultimo recurso: normalize
        return pd.json_normalize(data)
    else:
        raise ValueError(f"Formato no soportado: {file_format}")


def infer_format_from_filename(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    mapping = {"csv": "csv", "xlsx": "xlsx", "xls": "xls", "json": "json"}
    return mapping.get(ext, "csv")
