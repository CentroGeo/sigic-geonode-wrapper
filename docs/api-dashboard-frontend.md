# Manual de integración Frontend — Dashboard de Indicadores

**Base URL:** `http://10.2.102.133` (dev) | `https://<dominio>` (prod)
**Prefijo API:** `/api/v2/dashboard/`
**Autenticación:** Bearer JWT (Keycloak) para escritura; lectura es pública.

---

## Índice

1. [Estructura de datos](#1-estructura-de-datos)
2. [Autenticación](#2-autenticación)
3. [Sitios (`/sites/`)](#3-sitios)
4. [Grupos de Indicadores (`/groups/`)](#4-grupos-de-indicadores)
5. [Subgrupos (`/subgroups/`)](#5-subgrupos)
6. [Indicadores (`/indicators/`)](#6-indicadores)
7. [Infoboxes (`/infoboxes/`)](#7-infoboxes)
8. [Logos de Sitio (`/site-logos/`)](#8-logos-de-sitio)
9. [Configuración de Sitio (`/site-configs/`)](#9-configuración-de-sitio)
10. [Flujo de carga de un dashboard completo](#10-flujo-de-carga-de-un-dashboard-completo)
11. [Paletas de color disponibles](#11-paletas-de-color-disponibles)
12. [Ejemplos de dashboards creados](#12-ejemplos-de-dashboards-creados)

---

## 1. Estructura de datos

La jerarquía del dashboard es:

```
Site
├── SiteConfiguration (1:1)
├── SiteLogos (1:N)
└── IndicatorGroup (1:N)
    └── SubGroup (1:N)
        └── Indicator (1:N)
            └── IndicatorFieldBoxInfo (1:N)
```

Un **Indicator** puede asociarse directamente a `Site`, `IndicatorGroup` o `SubGroup` —  no necesariamente requiere subgrupo. La capa de datos se referencia vía `layer` (ID de un Dataset de GeoNode).

**Paginación:** Todos los endpoints de lista devuelven:

```json
{
  "links": { "next": "...", "previous": "..." },
  "total": 42,
  "page": 1,
  "page_size": 10,
  "results": [...]
}
```

---

## 2. Autenticación

Los endpoints de **lectura** (`GET list`, `GET detail`) son **públicos** — sin header.

Los endpoints de **escritura** (`POST`, `PUT`, `PATCH`, `DELETE`) requieren:

```http
Authorization: Bearer <keycloak_access_token>
```

Para obtener el token desde el frontend (Nuxt/Vue):

```js
// El token ya está disponible en la sesión de Keycloak
const token = useAuthStore().accessToken

const res = await fetch('/api/v2/dashboard/sites/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ name: 'mi-sitio', title: '...', subtitle: '...', url: 'mi-sitio' }),
})
```

---

## 3. Sitios

### `GET /api/v2/dashboard/sites/`

Lista todos los sitios. Soporta paginación.

```json
{
  "results": [
    {
      "id": 1,
      "name": "idegeo",
      "title": "IDEGeo - Infraestructura de Datos Espaciales",
      "subtitle": "Estadísticas y análisis del territorio nacional",
      "url": "idegeo"
    }
  ]
}
```

### `GET /api/v2/dashboard/sites/{id}/`

Detalle del sitio con logos y configuración anidados.

```json
{
  "id": 1,
  "name": "idegeo",
  "title": "IDEGeo - Infraestructura de Datos Espaciales",
  "subtitle": "Estadísticas y análisis del territorio nacional",
  "url": "idegeo",
  "info_text": "<p>Plataforma de visualización...</p>",
  "logos": [
    {
      "id": 1,
      "site": 1,
      "icon": "/uploaded/dashboard/logos/logo.png",
      "icon_link": "https://centrogeo.org.mx",
      "stack_order": 1
    }
  ],
  "configuration": {
    "id": 1,
    "site": 1,
    "show_header": true,
    "show_footer": true,
    "header_background_color": "#073B4B",
    "header_text_color": "#FFFFFF",
    "header_font_size": 28,
    "site_font_style": "Montserrat",
    "site_interface_background_color": "#F5F7FA",
    "site_interface_text_color": "#2D3748",
    "site_font_size": 14,
    "indicator_box_title": "Selecciona un indicador"
  }
}
```

### `GET /api/v2/dashboard/sites/{id}/logos/`

Lista los logos del sitio ordenados por `stack_order`.

### `GET /api/v2/dashboard/sites/{id}/config/`

Devuelve la configuración visual del sitio (se crea automáticamente si no existe).

### `PATCH /api/v2/dashboard/sites/{id}/config/` 🔒

Actualiza la configuración visual.

```json
{
  "header_background_color": "#1a1a2e",
  "site_font_style": "Poppins",
  "indicator_box_title": "Elige un indicador"
}
```

### `POST /api/v2/dashboard/sites/` 🔒

```json
{
  "name": "mi-sitio",
  "title": "Mi Dashboard",
  "subtitle": "Subtítulo",
  "url": "mi-sitio",
  "info_text": "<p>Texto opcional HTML</p>"
}
```

---

## 4. Grupos de Indicadores

### `GET /api/v2/dashboard/groups/`

Lista grupos. Filtro por sitio desde el cliente con query params opcionales.

```json
{
  "results": [
    {
      "id": 1,
      "site": 1,
      "name": "Territorio",
      "description": "Indicadores de uso y cobertura del suelo",
      "stack_order": 1
    }
  ]
}
```

### `GET /api/v2/dashboard/groups/{id}/`

Incluye `info_text` (HTML) para mostrar en popover/tooltip.

### `GET /api/v2/dashboard/groups/{id}/select-data/`

**Endpoint principal para poblar el selector de indicadores del dashboard.**

Devuelve la estructura anidada completa de subgrupos e indicadores del grupo, filtrando solo los que tienen datos calculados (`plot_values` o `is_histogram`):

```json
{
  "subgroups": [
    {
      "subgroup_id": 1,
      "subgroup_name": "Cobertura Forestal",
      "subgroup_icon": "fas fa-tree",
      "icon_custom": null,
      "indicators": [
        {
          "indicator_id": 1,
          "indicator_name": "Porcentaje de Cobertura Forestal",
          "is_histogram": false
        }
      ]
    }
  ],
  "indicators": []
}
```

> **Nota:** Si el grupo no tiene subgrupos, los indicadores aparecen en `indicators` directamente.

### `POST /api/v2/dashboard/groups/bulk-reorder/` 🔒

```json
[
  { "id": 1, "stack_order": 1 },
  { "id": 2, "stack_order": 2 }
]
```

---

## 5. Subgrupos

### `GET /api/v2/dashboard/subgroups/`

```json
{
  "results": [
    {
      "id": 1,
      "group": 1,
      "name": "Cobertura Forestal",
      "info_text": "<p>...</p>",
      "icon": "fas fa-tree",
      "icon_custom": null,
      "stack_order": 1
    }
  ]
}
```

`icon` es una clase CSS de Font Awesome 6 para renderizar con `<i class="fas fa-tree"></i>`.
`icon_custom` es una URL relativa a una imagen de icon personalizado (si se subió una).

---

## 6. Indicadores

### `GET /api/v2/dashboard/indicators/`

Lista resumida de indicadores.

```json
{
  "results": [
    {
      "id": 1,
      "site": 1,
      "group": 1,
      "subgroup": 1,
      "layer": 42,
      "name": "Porcentaje de Cobertura Forestal",
      "plot_type": "bar",
      "is_histogram": false,
      "stack_order": 1
    }
  ]
}
```

### `GET /api/v2/dashboard/indicators/{id}/`

Detalle completo con todos los campos e infoboxes anidados.

### `GET /api/v2/dashboard/indicators/{id}/view-data/`

**Endpoint principal para renderizar un indicador ya procesado.**

```json
{
  "data": {
    "plot_values": [
      { "sortPosition": 5, "label": "80 - 100", "value": 45, "color": "#004529" },
      { "sortPosition": 4, "label": "60 - 80",  "value": 123, "color": "#006837" },
      { "sortPosition": 3, "label": "40 - 60",  "value": 201, "color": "#238443" }
    ],
    "map_values": {
      "01001": { "value": "60 - 80", "color": "#006837" },
      "02003": { "value": "40 - 60", "color": "#238443" }
    },
    "plot_config": {
      "x_label": "Municipios",
      "y_label": "Cantidad",
      "title": "Distribución por rango de cobertura"
    },
    "layer_id_field": "cve_mun",
    "field_popup": ["cve_mun", "nom_mun", "pct_cobertura"],
    "info_text": "<p>Porcentaje de cobertura forestal...</p>",
    "field_one": "pct_cobertura",
    "use_filter": false,
    "filters": {},
    "info_boxes": [
      {
        "id": 1,
        "field": "pct_cobertura",
        "is_percentage": true,
        "name": "Cobertura Prom.",
        "icon": "fas fa-tree",
        "color": "#006837",
        "size": "1",
        "text_color": "#ffffff",
        "order": 1
      }
    ]
  }
}
```

**Estructura `plot_values`:**

| Campo | Tipo | Descripción |
|---|---|---|
| `sortPosition` | int | Posición en la gráfica (1 = primero) |
| `label` | string | Etiqueta de la categoría o valor |
| `value` | number | Conteo de elementos en esa categoría |
| `color` | string | Color hexadecimal para esta barra/slice |

**Estructura `map_values`:**

Diccionario `{ id_geometria: { value: label, color: hex } }` para tematizar la capa WMS:

```js
// Ejemplo: colorear una capa GeoNode usando map_values
const mapValues = data.map_values
const featureId = feature.properties.cve_mun
const style = mapValues[featureId]
if (style) {
  layer.setStyle({ fillColor: style.color, weight: 1 })
}
```

### `GET /api/v2/dashboard/indicators/{id}/info/`

Devuelve el texto informativo del indicador siguiendo la cadena de herencia: subgrupo → grupo → sitio.

```json
{ "info": "<p>Porcentaje de cobertura forestal calculado...</p>" }
```

### `GET /api/v2/dashboard/indicators/get-data/?indicator_ids=1,2,3`

Retorna datos resumidos de múltiples indicadores en una sola llamada (útil para precargar).

```json
{
  "data": {
    "1": {
      "name": "Porcentaje de Cobertura Forestal",
      "histogram_fields": null,
      "plot_config": {...},
      "layer_id_field": "cve_mun",
      "custom_colors": null,
      "info_text": "<p>...</p>"
    }
  }
}
```

### `POST /api/v2/dashboard/indicators/{id}/build-data/` 🔒

Genera los datos estadísticos del indicador consultando la base de datos de GeoNode. Usar solo en el panel de administración.

```json
{
  "field_id": "cve_mun",
  "field_one": "pct_cobertura",
  "field_two": "",
  "method": "naturalb",
  "categories": 5,
  "manual_bins": ""
}
```

**Métodos de clasificación (`method`):**

| Valor | Descripción |
|---|---|
| `quantil` | Quintiles — misma cantidad de elementos por categoría |
| `naturalb` | Natural Breaks (Jenks) — minimiza varianza interna |
| `sameintervals` | Intervalos iguales — rango dividido uniformemente |
| `manual` | Manual — el usuario define los bins (en `manual_bins`) |

**Respuesta:**

```json
{
  "plot_data": [
    { "sortPosition": 1, "label": "0   -   20", "value": 698 }
  ],
  "theming_data": {
    "01001": { "value": "60   -   80" },
    "02003": { "value": "0   -   20" }
  }
}
```

### `POST /api/v2/dashboard/indicators/{id}/save-data/` 🔒

Guarda la configuración procesada del indicador. Se usa después de `build-data` para persistir los valores con colores asignados.

**Para indicador estándar:**

```json
{
  "field_id": "cve_mun",
  "single_field": true,
  "field_one": "pct_cobertura",
  "field_two": "",
  "field_popup": ["cve_mun", "nom_mun"],
  "category_method": "naturalb",
  "field_category": 5,
  "colors": "verdes_4",
  "use_custom_color": false,
  "custom_colors": "",
  "plot_values": [...],
  "map_values": {...},
  "plot_config": { "title": "..." },
  "use_filter": false,
  "filters": {}
}
```

**Para histograma:**

```json
{
  "field_id": "cve_mun",
  "field_name": "nom_mun",
  "high_values": 10,
  "histogram_fields": ["campo1", "campo2", "campo3"],
  "colors": "azules",
  "use_custom_color": false,
  "custom_colors": "",
  "plot_config": {...},
  "use_filter": false,
  "general_values": false,
  "filters": {}
}
```

**Respuesta:** `{ "indicator": 1 }`

### `POST /api/v2/dashboard/indicators/{id}/clone/` 🔒

Clona un indicador con campos diferentes.

```json
{
  "field_one": "nuevo_campo",
  "field_two": "",
  "name": "Indicador Clonado",
  "clone_boxes": true
}
```

**Respuesta:** `{ "ind_clone": 5 }`

---

## 7. Infoboxes

Los infoboxes son recuadros de resumen que muestran un valor agregado de un campo.

### `GET /api/v2/dashboard/infoboxes/`

```json
{
  "results": [
    {
      "id": 1,
      "indicator": 1,
      "field": "pct_cobertura",
      "is_percentage": true,
      "field_percentage_total": null,
      "name": "Cobertura Promedio",
      "icon": "fas fa-tree",
      "icon_custom": null,
      "color": "#006837",
      "size": "1",
      "edge_style": "8",
      "edge_color": "#000000",
      "text_color": "#ffffff",
      "stack_order": 1
    }
  ]
}
```

**Valores de `size`:** `"1"` Normal · `"2"` Grande · `"3"` Extra grande
**Valores de `edge_style`:** `"1"` Izq · `"2"` Der · `"3"` Sup · `"4"` Inf · `"5"` Paralelos H · `"6"` Paralelos V · `"7"` Completo · `"8"` Sin bordes

### `POST /api/v2/dashboard/infoboxes/bulk-add/{indicator_id}/` 🔒

Crea múltiples infoboxes para un indicador:

```json
[
  {
    "field": "pct_cobertura",
    "is_percentage": true,
    "name": "Cobertura Prom.",
    "icon": "fas fa-tree",
    "color": "#006837",
    "size": "1",
    "text_color": "#ffffff",
    "stack_order": 1
  }
]
```

---

## 8. Logos de Sitio

Endpoints para subir y gestionar logos del header.

### `POST /api/v2/dashboard/site-logos/` 🔒

Multipart form data:

```
POST /api/v2/dashboard/site-logos/
Content-Type: multipart/form-data

site=1
icon=<archivo_imagen>
icon_link=https://centrogeo.org.mx
```

---

## 9. Configuración de Sitio

### `GET /api/v2/dashboard/site-configs/{site_id}/`

```json
{
  "id": 1,
  "site": 1,
  "show_header": true,
  "show_footer": true,
  "header_background_color": "#073B4B",
  "header_text_color": "#FFFFFF",
  "header_font_size": 28,
  "site_font_style": "Montserrat",
  "site_text_color": null,
  "site_interface_text_color": "#2D3748",
  "site_background_color": null,
  "site_interface_background_color": "#F5F7FA",
  "site_font_size": 14,
  "indicator_box_title": "Selecciona un indicador"
}
```

> Usar `site_id` en la URL (no el id de la configuración).

### `PATCH /api/v2/dashboard/site-configs/{site_id}/` 🔒

Actualiza parcialmente la configuración.

---

## 10. Flujo de carga de un dashboard completo

```
┌────────────────────────────────────────────────────────┐
│  1. GET /api/v2/dashboard/sites/?url={slug}            │
│     → Obtener el site_id del slug de la URL            │
├────────────────────────────────────────────────────────┤
│  2. GET /api/v2/dashboard/sites/{site_id}/             │
│     → Obtener título, subtítulo, logos y config visual │
├────────────────────────────────────────────────────────┤
│  3. GET /api/v2/dashboard/groups/?site={site_id}       │
│     → Obtener grupos de indicadores para el menú       │
├────────────────────────────────────────────────────────┤
│  4. GET /api/v2/dashboard/groups/{group_id}/select-data│
│     → Obtener subgrupos e indicadores disponibles      │
├────────────────────────────────────────────────────────┤
│  5. GET /api/v2/dashboard/indicators/{id}/view-data/   │
│     → Cargar plot_values y map_values del indicador    │
└────────────────────────────────────────────────────────┘
```

### Implementación en Nuxt 3 (composable)

```ts
// composables/useDashboard.ts
export function useDashboard(siteSlug: string) {
  const site = ref(null)
  const groups = ref([])
  const activeGroup = ref(null)
  const selectData = ref(null)
  const indicatorData = ref(null)
  const loading = ref(false)

  const BASE = '/api/v2/dashboard'

  async function init() {
    loading.value = true
    // 1. Buscar el site por URL slug
    const sitesRes = await $fetch(`${BASE}/sites/`)
    site.value = sitesRes.results.find(s => s.url === siteSlug)
    if (!site.value) throw new Error(`Site "${siteSlug}" no encontrado`)

    // 2. Detalle con logos y config
    site.value = await $fetch(`${BASE}/sites/${site.value.id}/`)

    // 3. Grupos de indicadores
    const groupsRes = await $fetch(`${BASE}/groups/`)
    groups.value = groupsRes.results.filter(g => g.site === site.value.id)
    loading.value = false
  }

  async function selectGroup(groupId: number) {
    selectData.value = await $fetch(`${BASE}/groups/${groupId}/select-data/`)
    activeGroup.value = groupId
  }

  async function loadIndicator(indicatorId: number) {
    loading.value = true
    const res = await $fetch(`${BASE}/indicators/${indicatorId}/view-data/`)
    indicatorData.value = res.data
    loading.value = false
  }

  async function loadInfo(indicatorId: number) {
    return $fetch(`${BASE}/indicators/${indicatorId}/info/`)
  }

  return { site, groups, selectData, indicatorData, loading, init, selectGroup, loadIndicator, loadInfo }
}
```

### Tematización de capa GeoNode con Leaflet

```js
// Aplicar map_values a una capa WMS como GeoJSON overlay
function applyTheming(geojsonLayer, mapValues) {
  geojsonLayer.eachLayer(feature => {
    const id = feature.feature.properties.cve_mun  // campo id de la capa
    const style = mapValues[id]
    if (style) {
      feature.setStyle({
        fillColor: style.color,
        fillOpacity: 0.75,
        weight: 0.5,
        color: '#ffffff',
      })
    }
  })
}

// Popup con field_popup
function bindPopup(feature, layer, indicator) {
  const props = feature.properties
  const fields = indicator.field_popup || []
  const html = fields.map(f => `<b>${f}:</b> ${props[f] ?? 'N/D'}`).join('<br>')
  layer.bindPopup(html)
}
```

### Gráfica de barras con Chart.js

```js
// Renderizar plot_values en Chart.js
function buildBarChart(canvasId, plotValues) {
  const sorted = [...plotValues].sort((a, b) => a.sortPosition - b.sortPosition)

  new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: {
      labels: sorted.map(d => d.label),
      datasets: [{
        data: sorted.map(d => d.value),
        backgroundColor: sorted.map(d => d.color),
        borderWidth: 0,
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } }
    }
  })
}
```

### Pie chart

```js
function buildPieChart(canvasId, plotValues) {
  new Chart(document.getElementById(canvasId), {
    type: 'pie',
    data: {
      labels: plotValues.map(d => d.label),
      datasets: [{
        data: plotValues.map(d => d.value),
        backgroundColor: plotValues.map(d => d.color),
      }]
    }
  })
}
```

---

## 11. Paletas de color disponibles

Pasar el nombre como string en el campo `colors` del indicador:

| Nombre | Descripción |
|---|---|
| `azules`, `azules_2`, `azules_3`, `azules_4`, `azules_5` | Degradados de azul (frío) |
| `cafes`, `cafes_2`, `cafes_3` | Degradados café/naranja |
| `cafes_verdes` | Divergente café ↔ verde |
| `grises` | Escala de grises |
| `morados`, `morados_2` | Degradados de morado |
| `naranjas` | Degradado naranja-rojo |
| `naranja_azul` | Divergente naranja ↔ azul |
| `rosa_verde` | Divergente rosa ↔ verde |
| `rosas` | Degradado de rosas |
| `semaforo` | Verde-amarillo-rojo (3 tonos, claro→oscuro) |
| `semaforo_2` | Verde-amarillo-rojo (intenso) |
| `semaforo_3` | Solo 3 colores: verde, amarillo, rojo |
| `semaforo_4` | Semáforo invertido (rojo→verde) |
| `semaforo_5` | Rojo→verde (intenso, invertido) |
| `semaforo_6` | Rojo, amarillo, verde (3 colores) |
| `semaforo_7` | Rojo→verde con 5 pasos |
| `semaforo_8` | Verde→rojo con 5 pasos |
| `varios`, `varios_2`, `varios_3` | Colores cualitativos para categorías |
| `verdes`, `verdes_2`, `verdes_3`, `verdes_4`, `verdes_5`, `verdes_6` | Degradados de verde |

> **Colores custom:** Pasar `use_custom_colors: true` y `custom_colors: "#hex1,#hex2,#hex3"` (separados por coma). El número de colores debe ser `≥` número de categorías.

---

## 12. Ejemplos de dashboards creados

Tres dashboards de ejemplo están disponibles en el servidor `http://10.2.102.133`:

### IDEGeo — Infraestructura de Datos Geoespaciales

| Recurso | Valor |
|---|---|
| Site ID | 1 |
| URL slug | `idegeo` |
| Tema visual | Header azul petróleo `#073B4B`, fuente Montserrat |

**Grupos:**
- **Territorio** → Subgrupos: Cobertura Forestal, Uso de Suelo
- **Población** → Subgrupos: Densidad y Distribución, Migración
- **Infraestructura**

**Indicadores:**
- `id=1` Porcentaje de Cobertura Forestal (`bar`, 5 categorías, paleta `verdes_4`, con `plot_values` pre-calculados)
- `id=2` Densidad Poblacional (`horizontal_bar`, sin `plot_values` — requiere `build-data`)

```bash
curl http://10.2.102.133/api/v2/dashboard/sites/1/
curl http://10.2.102.133/api/v2/dashboard/indicators/1/view-data/
```

---

### SIGIC Ambiental

| Recurso | Valor |
|---|---|
| Site ID | 2 |
| URL slug | `ambiental` |
| Tema visual | Header verde oscuro `#1B5E20`, fuente Nunito |

**Grupos:**
- **Calidad del Aire** → Subgrupo: Partículas Finas PM2.5
- **Recursos Hídricos**
- **Biodiversidad** → Subgrupo: Áreas Naturales Protegidas

**Indicadores:**
- `id=3` Concentración PM2.5 (`bar`, 6 categorías, paleta `semaforo_2`, con colores tipo semáforo de calidad del aire)

```bash
curl http://10.2.102.133/api/v2/dashboard/indicators/3/view-data/
```

**Respuesta plot_values (ejemplo):**
```json
[
  {"sortPosition":1,"label":"0 - 5 (Bueno)","value":12,"color":"#cbf7cb"},
  {"sortPosition":2,"label":"5 - 15 (Moderado)","value":28,"color":"#57dda6"},
  {"sortPosition":6,"label":"> 45 (Crítico)","value":2,"color":"#ed1f07"}
]
```

---

### Dashboard Socioeconómico

| Recurso | Valor |
|---|---|
| Site ID | 3 |
| URL slug | `socioeconomico` |
| Tema visual | Header morado `#4A1942`, fuente Poppins |

**Grupos:**
- **Pobreza y Marginación** → Subgrupos: Índice de Marginación, Desarrollo Humano
- **Economía Regional**

**Indicadores:**
- `id=4` Índice de Marginación Municipal (`pie`, 5 categorías, paleta `semaforo_7`, con datos CONAPO 2020)

```bash
curl http://10.2.102.133/api/v2/dashboard/indicators/4/view-data/
curl http://10.2.102.133/api/v2/dashboard/groups/7/select-data/
```

---

## Notas para el equipo frontend

1. **Sin capa asignada:** Si `layer` es `null`, el indicador no tiene tematización de mapa. Mostrar solo la gráfica.

2. **Indicador sin `plot_values`:** Si `plot_values` es `null` o vacío, el indicador aún no fue procesado. El admin debe usar `build-data` + `save-data` para calcularlo.

3. **Histogramas:** Si `is_histogram === true`, los datos están en `histogram_fields` (arreglo de nombres de campos temporales). El renderizado es diferente al estándar.

4. **Filtros:** Si `use_filter === true`, el objeto `filters` contiene la configuración de filtros aplicables a la gráfica. Implementación pendiente de spec.

5. **info_text:** Todos los modelos tienen `info_text` con HTML. Renderizar con `v-html` o equivalente. Implementar sanitización si el contenido viene de usuarios no confiables.

6. **stack_order:** El orden de visualización de grupos, subgrupos e indicadores está controlado por `stack_order`. Los endpoints devuelven los objetos ya ordenados por este campo.
