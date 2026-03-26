# sigic_georeference

Módulo para unir capas tabulares con capas geográficas directamente sobre la base de datos PostGIS, con generación automática de estilos SLD por columna.

---

## Endpoints

Todos los endpoints requieren autenticación Keycloak (`Authorization: Bearer <token>`).

Base path: `/sigic/georeference`

| Método | Path | Descripción |
|--------|------|-------------|
| `POST` | `/join` | Ejecuta la unión entre una capa tabular y una geográfica |
| `GET` | `/status/<layer_id>/` | Consulta el estado de procesamiento de un dataset |
| `POST` | `/reset` | Fuerza la resincronización de un dataset con GeoServer |

---

## POST /join

### Parámetros (form-data o JSON)

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `layer` | int | ✓ | ID del dataset tabular |
| `geo_layer` | int | ✓ | ID del dataset geográfico |
| `layer_pivot` | string | ✓ | Columna pivot en la capa tabular |
| `geo_pivot` | string | ✓ | Columna pivot en la capa geográfica |
| `columns` | list | ✓ | Columnas a transferir (repetir el parámetro por cada columna) |
| `reverse` | bool | — | `false` (default): tabular → geo \| `true`: geo → tabular |

> **Nota:** Al enviar JSON, usar una petición `application/x-www-form-urlencoded` para que `columns` se pueda pasar múltiples veces. En JSON, `columns` debe ser un array.

### Dirección del join

#### Dirección normal (`reverse=false`, default)

Los datos de la capa tabular se copian hacia la capa geográfica.

```
Tabular  ──[columnas]──▶  Geo
                          (recibe datos + estilos por columna)
```

**Caso de uso:** Tienes estadísticas municipales en CSV y quieres visualizarlas sobre un shapefile de municipios.

#### Dirección inversa (`reverse=true`)

La geometría de la capa geográfica se copia hacia la capa tabular.

```
Geo  ──[geometry + bbox + srid]──▶  Tabular
                                     (se convierte en capa geográfica)
```

**Caso de uso:** Tienes un CSV con claves municipales y quieres que se convierta en una capa visualizable en el mapa.

### Ejemplo — dirección normal

```bash
curl -X POST https://<host>/sigic/georeference/join \
  -H "Authorization: Bearer <token>" \
  -d "layer=21" \
  -d "geo_layer=20" \
  -d "layer_pivot=cve_geo" \
  -d "geo_pivot=cvegeo" \
  -d "columns=pobtot" \
  -d "columns=pobfem" \
  -d "columns=pobmas" \
  -d "reverse=false"
```

### Ejemplo — dirección inversa

```bash
curl -X POST https://<host>/sigic/georeference/join \
  -H "Authorization: Bearer <token>" \
  -d "layer=21" \
  -d "geo_layer=20" \
  -d "layer_pivot=cve_geo" \
  -d "geo_pivot=cvegeo" \
  -d "columns=geometry" \
  -d "reverse=true"
```

### Respuesta exitosa

```json
{ "status": "success" }
```

### Respuesta de error

```json
{
  "status": "failed running database changes",
  "error": "column \"pobtot\" of relation \"qro_utm14n\" already exists",
  "traceback": "..."
}
```

---

## GET /status/\<layer_id\>/

Retorna el estado actual de un dataset.

```bash
curl https://<host>/sigic/georeference/status/20/ \
  -H "Authorization: Bearer <token>"
```

```json
{ "status": "PROCESSED" }
```

### Estados posibles

| Estado | Significado |
|--------|-------------|
| `PROCESSED` | Listo, visible en GeoServer |
| `WAITING` | En cola de procesamiento Celery |
| `RUNNING` | Join en ejecución |
| `INCOMPLETE` | Error durante el join |
| `INVALID` | Error en la sincronización con GeoServer |

---

## POST /reset

Fuerza la resincronización del dataset con GeoServer (recalcula bbox y native bbox).

```bash
curl -X POST https://<host>/sigic/georeference/reset \
  -H "Authorization: Bearer <token>" \
  -d "layer=20"
```

```json
{ "status": "success" }
```

---

## Generación automática de estilos

Al completar el join, se lanza una tarea Celery (`generate_column_styles`) que:

1. Clasifica cada columna transferida:
   - **Categórica:** ≤ 15 valores distintos o tipo texto → paleta cualitativa ColorBrewer (15 colores)
   - **Numérica:** > 15 valores distintos o tipo entero/decimal → 5 clases por cuantiles, paleta YlOrRd
   - **Omitida:** columnas con nombre tipo ID (`id`, `ogc_fid`, `fid`, `cve*`, `codigo`, etc.)

2. Genera un SLD 1.0.0 válido por columna

3. Registra el estilo en GeoServer y en GeoNode asociado al dataset

4. Asigna el **primer estilo generado** como `default_style` del dataset (tanto en GeoNode como en GeoServer)

Los estilos siguen el patrón de nombre: `<nombre_capa>__<nombre_columna>`.

### Join inverso y estilos

Cuando `reverse=true` y solo se transfiere `geometry`, la tarea de estilos genera estilos automáticamente para **todas las columnas existentes** del dataset destino (las que ya tenía antes de recibir la geometría), excluyendo columnas tipo ID.

---

## Notas técnicas

- El join opera directamente con SQL (`ALTER TABLE ... ADD COLUMN` + `UPDATE ... FROM`) sin usar pandas, para mayor eficiencia con tablas grandes.
- Los tipos de columna del origen se preservan en el destino (INTEGER, BIGINT, DOUBLE PRECISION, etc.) consultando `information_schema.columns`.
- En el join inverso, el SRID, `ll_bbox_polygon` y `bbox_polygon` del dataset geo se copian al dataset tabular en GeoNode.
- El nombre de la columna de geometría en la tabla fuente se detecta automáticamente desde `geometry_columns` (no asume que sea `geometry`).
- Los SLDs generados pasan por `fix_sld()` antes de subirse a GeoServer para garantizar compatibilidad SLD 1.0.0.
