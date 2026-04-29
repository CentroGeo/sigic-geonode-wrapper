# API de Escenarios - Guía de Integración Frontend

## Descripción General

La API de escenarios permite crear y gestionar narrativas interactivas con mapas. La estructura jerárquica es:

```
Scenario (escenario)
  └── Scene (escena) [1..n]
        ├── SceneLayer (capa) [0..n]
        └── SceneMarker (marcador) [0..n]
```

**Base URL:** `/api/v2/`

---

## Autenticación

Todos los endpoints de escritura requieren autenticación. Métodos soportados:

- **Session Auth:** Cookie de sesión Django (para frontend integrado)
- **Basic Auth:** `Authorization: Basic base64(user:pass)`
- **OAuth2:** `Authorization: Bearer {token}`
- **Keycloak JWT:** Token JWT de Keycloak

Los endpoints de lectura son públicos para escenarios con `is_public: true`.

---

## Modelos de Datos

### Scenario

```typescript
interface Scenario {
  id: number;
  name: string;
  created_at: string;              // ISO 8601
  owner: { pk: number; username: string };
  url_id: string | null;           // slug único para URLs amigables
  is_public: boolean;
  card_image: string | null;       // URL de imagen de portada
  description: string | null;
  scenes_layout_styles: {
    text_panel: number;            // % ancho panel texto (0-100)
    map_panel: number;             // % ancho panel mapa (0-100)
    timeline_position: string;     // "bottom" | "top" | "left" | "right"
  };
  scene_count: number;             // solo en listado
  scenes?: SceneBasic[];           // solo en detalle
}

interface SceneBasic {
  id: number;
  name: string;
  stack_order: number;
}
```

### Scene

```typescript
interface Scene {
  id: number;
  name: string;
  scenario: number;                // ID del escenario padre
  map_center_lat: number | null;
  map_center_long: number | null;
  zoom: number | null;
  text_position: "left" | "right";
  text_content: string | null;     // HTML
  styles: {
    text_panel: number;            // % ancho panel texto
    map_panel: number;             // % ancho panel mapa
  };
  stack_order: number;             // orden en la narrativa (1, 2, 3...)
  layers: SceneLayer[];
  markers: SceneMarker[];
}
```

### SceneLayer

```typescript
interface SceneLayer {
  id: number;
  scene: number;
  geonode_id: number;              // ID del Dataset en GeoNode (requerido)
  name: string;                    // typename, ej: "geonode:municipios"
  dataset_title: string | null;    // título legible del Dataset
  style: string | null;            // nombre del estilo SLD
  style_title: string | null;      // título del estilo
  visible: boolean;
  opacity: number;                 // 0.0 - 1.0
  stack_order: number;             // orden de capas (mayor = arriba)
}
```

### SceneMarker

```typescript
interface SceneMarker {
  id: number;
  scene: number;
  lat: string;                     // decimal string
  lng: string;                     // decimal string
  title: string | null;
  content: string | null;          // HTML para popup
  icon: string;                    // clase FontAwesome, ej: "fas fa-map-marker-alt"
  color: string;                   // hex, ej: "#ec4899"
  image_url: string | null;
  options: Record<string, any>;    // opciones adicionales
}
```

---

## Endpoints

### Escenarios

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/scenarios/` | Listar escenarios (paginado) |
| POST | `/api/v2/scenarios/` | Crear escenario |
| GET | `/api/v2/scenarios/{id}/` | Detalle con escenas |
| PUT/PATCH | `/api/v2/scenarios/{id}/` | Actualizar escenario |
| DELETE | `/api/v2/scenarios/{id}/` | Eliminar escenario |
| POST | `/api/v2/scenarios/{id}/upload-image/` | Subir imagen de portada |
| GET | `/api/v2/scenarios/{id}/scenes/` | Listar escenas completas |

#### Listar escenarios

```http
GET /api/v2/scenarios/?page=1&page_size=10
```

**Respuesta:**
```json
{
  "links": { "next": "...", "previous": null },
  "total": 25,
  "page": 1,
  "page_size": 10,
  "results": [{ "id": 1, "name": "...", ... }]
}
```

#### Crear escenario

```http
POST /api/v2/scenarios/
Content-Type: application/json

{
  "name": "Mi escenario",
  "url_id": "mi-escenario",
  "is_public": false,
  "description": "Descripción opcional"
}
```

**Nota:** `scenes_layout_styles` se auto-genera con valores por defecto si no se proporciona.

#### Subir imagen de portada

```http
POST /api/v2/scenarios/{id}/upload-image/
Content-Type: multipart/form-data

card_image: [archivo]
```

---

### Escenas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/scenes/{id}/` | Detalle con layers y markers |
| POST | `/api/v2/scenes/` | Crear escena |
| PUT/PATCH | `/api/v2/scenes/{id}/` | Actualizar escena |
| DELETE | `/api/v2/scenes/{id}/` | Eliminar escena |
| POST | `/api/v2/scenes/bulk-reorder/` | Reordenar escenas |
| GET | `/api/v2/scenes/{id}/layers/` | Listar capas de una escena |

#### Crear escena

```http
POST /api/v2/scenes/
Content-Type: application/json

{
  "name": "Introducción",
  "scenario": 1,
  "map_center_lat": 19.4326,
  "map_center_long": -99.1332,
  "zoom": 10,
  "text_position": "left",
  "text_content": "<h2>Título</h2><p>Contenido HTML...</p>",
  "styles": { "text_panel": 40, "map_panel": 60 }
}
```

**Nota:** `stack_order` se auto-incrementa al crear.

#### Reordenar escenas

```http
POST /api/v2/scenes/bulk-reorder/
Content-Type: application/json

[
  { "id": 3, "stack_order": 1 },
  { "id": 1, "stack_order": 2 },
  { "id": 2, "stack_order": 3 }
]
```

---

### Capas (SceneLayer)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/scene-layers/{id}/` | Detalle de capa |
| GET | `/api/v2/scene-layers/by-scene/{scene_id}/` | Capas de una escena |
| POST | `/api/v2/scene-layers/` | Crear capa |
| POST | `/api/v2/scene-layers/bulk-add/{scene_id}/` | Crear múltiples capas |
| PUT/PATCH | `/api/v2/scene-layers/{id}/` | Actualizar capa |
| PUT/PATCH | `/api/v2/scene-layers/{id}/update-style/` | Solo actualizar estilo |
| POST | `/api/v2/scene-layers/bulk-reorder/` | Reordenar capas |
| DELETE | `/api/v2/scene-layers/{id}/` | Eliminar capa |
| POST | `/api/v2/scene-layers/bulk-delete/{scene_id}/` | Eliminar múltiples |

#### Crear capa

```http
POST /api/v2/scene-layers/
Content-Type: application/json

{
  "scene": 1,
  "geonode_id": 14,
  "style": "estilo_rojo",
  "style_title": "Estilo Rojo",
  "visible": true,
  "opacity": 0.8
}
```

**Importante:**
- `geonode_id` es **requerido** y debe corresponder a un Dataset existente en GeoNode de tipo capa (vector o raster)
- `name` se **auto-rellena** con el `alternate` del Dataset (ej: `geonode:municipios`)
- Si el Dataset no existe o no es de tipo capa, retorna error 400

**Respuesta exitosa:**
```json
{
  "scene": 1,
  "geonode_id": 14,
  "name": "geonode:planeas_centrales_electricas_0522_xy_p",
  "style": "estilo_rojo",
  "style_title": "Estilo Rojo",
  "visible": true,
  "opacity": 0.8
}
```

**Error - Dataset no existe:**
```json
{
  "success": false,
  "errors": ["No existe un dataset en GeoNode con id 9999."],
  "code": "invalid"
}
```

#### Crear múltiples capas

```http
POST /api/v2/scene-layers/bulk-add/{scene_id}/
Content-Type: application/json

[
  { "geonode_id": 14, "opacity": 0.9 },
  { "geonode_id": 15, "opacity": 0.7, "style": "lineas_azules" }
]
```

**Nota:** No es necesario incluir `scene` en cada objeto; se toma del URL.

#### Actualizar solo estilo

```http
PATCH /api/v2/scene-layers/{id}/update-style/
Content-Type: application/json

{
  "style": "nuevo_estilo",
  "style_title": "Nuevo Estilo"
}
```

---

### Marcadores (SceneMarker)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/scene-markers/{id}/` | Detalle de marcador |
| GET | `/api/v2/scene-markers/by-scene/{scene_id}/` | Marcadores de una escena |
| POST | `/api/v2/scene-markers/` | Crear marcador |
| POST | `/api/v2/scene-markers/bulk-add/{scene_id}/` | Crear múltiples |
| PUT/PATCH | `/api/v2/scene-markers/{id}/` | Actualizar marcador |
| DELETE | `/api/v2/scene-markers/{id}/` | Eliminar marcador |
| POST | `/api/v2/scene-markers/bulk-delete/{scene_id}/` | Eliminar múltiples |

#### Crear marcador

```http
POST /api/v2/scene-markers/
Content-Type: application/json

{
  "scene": 1,
  "lat": 19.4326,
  "lng": -99.1332,
  "title": "Zócalo CDMX",
  "content": "<p>Centro histórico</p>",
  "icon": "fas fa-landmark",
  "color": "#2563eb"
}
```

#### Crear múltiples marcadores

```http
POST /api/v2/scene-markers/bulk-add/{scene_id}/
Content-Type: application/json

[
  { "lat": 19.43, "lng": -99.13, "title": "Punto A", "icon": "fas fa-star", "color": "#ef4444" },
  { "lat": 19.42, "lng": -99.17, "title": "Punto B", "icon": "fas fa-tree", "color": "#22c55e" }
]
```

---

### Subida de imágenes (general)

Para editores de texto enriquecido (CKEditor, TipTap, etc.):

```http
POST /api/v2/scenarios/upload/image
Content-Type: multipart/form-data

upload: [archivo]
```

**Respuesta:**
```json
{
  "url": "https://example.com/media/2026/02/a1b2c3d4_imagen.jpg"
}
```

**Restricciones:**
- Tamaño máximo: 5 MB
- Formatos: jpg, jpeg, png, gif, webp
- Imágenes >2048px se redimensionan automáticamente

---

## Flujo típico de integración

### 1. Listar escenarios públicos

```javascript
const response = await fetch('/api/v2/scenarios/');
const { results, total } = await response.json();
```

### 2. Cargar escenario completo para visualización

```javascript
// Obtener escenario con lista de escenas
const scenario = await fetch(`/api/v2/scenarios/${id}/`).then(r => r.json());

// Cargar cada escena con sus capas y marcadores
const scenes = await Promise.all(
  scenario.scenes.map(s =>
    fetch(`/api/v2/scenes/${s.id}/`).then(r => r.json())
  )
);
```

### 3. Renderizar capas en el mapa

```javascript
scene.layers.forEach(layer => {
  // layer.name contiene el typename para WMS
  // Ejemplo: "geonode:municipios"
  const wmsUrl = `https://geoserver.example.com/geoserver/wms`;

  map.addLayer({
    type: 'wms',
    url: wmsUrl,
    layers: layer.name,
    styles: layer.style || '',
    opacity: layer.opacity,
    visible: layer.visible
  });
});
```

### 4. Crear escenario nuevo (editor)

```javascript
// 1. Crear escenario
const scenario = await fetch('/api/v2/scenarios/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Nuevo escenario',
    is_public: false
  })
}).then(r => r.json());

// 2. Crear primera escena
const scene = await fetch('/api/v2/scenes/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Introducción',
    scenario: scenario.id,
    map_center_lat: 19.43,
    map_center_long: -99.13,
    zoom: 10,
    text_position: 'left'
  })
}).then(r => r.json());

// 3. Agregar capas (geonode_id viene del selector de datasets)
await fetch(`/api/v2/scene-layers/bulk-add/${scene.id}/`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify([
    { geonode_id: 14, opacity: 0.8 },
    { geonode_id: 15, opacity: 0.6 }
  ])
});
```

---

## Códigos de error comunes

| Código | Significado |
|--------|-------------|
| 400 | Datos inválidos (ver `errors` en respuesta) |
| 401 | No autenticado |
| 403 | No autorizado (no es propietario) |
| 404 | Recurso no encontrado |

**Formato de error:**
```json
{
  "success": false,
  "errors": ["Mensaje de error"],
  "code": "invalid"
}
```

---

## Documentación OpenAPI

La especificación completa está disponible en:

- **Swagger UI:** `/api/v2/swagger/`
- **ReDoc:** `/api/v2/redoc/`
- **JSON Schema:** `/api/v2/schema/`
