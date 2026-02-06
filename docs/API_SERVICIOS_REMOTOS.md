# API de Servicios Remotos (Harvesters)

Documentación para implementar la gestión de servicios remotos desde el frontend.

## Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/services/` | Lista servicios del usuario |
| POST | `/api/v2/services/` | Registra nuevo servicio |
| GET | `/api/v2/services/{id}/` | Detalle de un servicio |
| GET | `/api/v2/harvesters/` | Lista harvesters (extendido) |
| GET | `/api/v2/harvesters/{id}/` | Detalle de harvester |
| GET | `/api/v2/sigic-remote-datasets/` | Datasets de servicios remotos |

---

## Autenticación

Todos los endpoints requieren autenticación. Opciones soportadas:

```javascript
// Opción 1: Bearer Token (Keycloak JWT)
headers: {
  'Authorization': 'Bearer <token>'
}

// Opción 2: Basic Auth
headers: {
  'Authorization': 'Basic ' + btoa('usuario:password')
}
```

---

## 1. Registrar Servicio Remoto

### POST /api/v2/services/

Crea un nuevo servicio remoto asociado al usuario autenticado.

#### Request

```javascript
const response = await fetch('/api/v2/services/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    url: 'https://example.com/geoserver/ows',
    type: 'WMS',  // Opcional, default: AUTO
    description: 'Descripción del servicio'  // Opcional
  })
});
```

#### Parámetros

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `url` | string | Sí | URL del servicio remoto |
| `type` | string | No | Tipo de servicio (ver tabla abajo) |
| `description` | string | No | Descripción del servicio (máx 2000 chars) |

#### Tipos de Servicio Soportados

| Valor | Descripción |
|-------|-------------|
| `AUTO` | Detección automática (default) |
| `OWS` | OGC Web Services genérico |
| `WMS` | Web Map Service |
| `GN_WMS` | GeoNode Web Map Service |
| `REST_MAP` | ArcGIS REST MapServer |
| `REST_IMG` | ArcGIS REST ImageServer |
| `FILE` | Archivo (csv, json, geojson, xls, xlsx) |

#### Response Exitoso (201)

```json
{
  "id": 4,
  "uuid": "c9390524-9c3c-4c76-9ac5-97a37b632dd6",
  "url": "https://example.com/geoserver/ows",
  "name": "examplecomgeoserverows",
  "title": "GeoServer OWS",
  "description": "Descripción del servicio",
  "type": "WMS",
  "harvester_id": 3,
  "owner": {
    "pk": 1000,
    "username": "usuario"
  },
  "created": "2026-01-14T23:38:26.176354Z"
}
```

#### Errores Comunes

**URL duplicada (400)**
```json
{
  "error": "Ya existe un servicio con esta URL para tu usuario.",
  "existing_service_id": 123
}
```

**Servicio no accesible (400)**
```json
{
  "error": "No se pudo conectar al servicio o el tipo no es válido. Verifique la URL y el tipo de servicio."
}
```

---

## 2. Listar Servicios

### GET /api/v2/services/

Lista todos los servicios del usuario autenticado.

#### Request

```javascript
const response = await fetch('/api/v2/services/', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const data = await response.json();
```

#### Response

```json
{
  "count": 2,
  "results": [
    {
      "id": 4,
      "uuid": "c9390524-9c3c-4c76-9ac5-97a37b632dd6",
      "url": "https://example.com/geoserver/ows",
      "name": "examplecomgeoserverows",
      "title": "GeoServer OWS",
      "description": "Mi servicio WMS",
      "type": "WMS",
      "harvester_id": 3,
      "owner": {"pk": 1000, "username": "usuario"},
      "created": "2026-01-14T23:38:26.176354Z"
    }
  ]
}
```

---

## 3. Detalle de Servicio

### GET /api/v2/services/{id}/

Obtiene el detalle de un servicio incluyendo información del harvester.

#### Request

```javascript
const response = await fetch('/api/v2/services/4/', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

#### Response

```json
{
  "id": 4,
  "uuid": "c9390524-9c3c-4c76-9ac5-97a37b632dd6",
  "url": "https://example.com/geoserver/ows",
  "name": "examplecomgeoserverows",
  "title": "GeoServer OWS",
  "description": "Mi servicio WMS",
  "type": "WMS",
  "harvester_id": 3,
  "owner": {"pk": 1000, "username": "usuario"},
  "created": "2026-01-14T23:38:26.176354Z",
  "harvester": {
    "id": 3,
    "name": "examplecomgeoserverows",
    "status": "ready",
    "remote_available": true,
    "num_harvestable_resources": 150,
    "last_updated": "2026-01-14T23:39:36.580308Z"
  }
}
```

---

## 4. Listar Harvesters

### GET /api/v2/harvesters/

Lista harvesters con campo `service_id` extendido.

#### Parámetros de Query

| Parámetro | Descripción |
|-----------|-------------|
| `owner_id` | Filtrar por ID del propietario |

#### Request

```javascript
const response = await fetch('/api/v2/harvesters/', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

#### Response

```json
{
  "total": 2,
  "page": 1,
  "page_size": 10,
  "harvesters": [
    {
      "id": 3,
      "name": "examplecomgeoserverows",
      "status": "ready",
      "remote_url": "https://example.com/geoserver/ows",
      "remote_available": true,
      "default_owner": 1000,
      "service_id": 4,
      "links": {
        "self": "/api/v2/harvesters/3/",
        "harvestable_resources": "/api/v2/harvesters/3/harvestable-resources/"
      }
    }
  ]
}
```

---

## 5. Detalle de Harvester

### GET /api/v2/harvesters/{id}/

#### Response

```json
{
  "harvester": {
    "id": 3,
    "name": "examplecomgeoserverows",
    "status": "ready",
    "remote_url": "https://example.com/geoserver/ows",
    "remote_available": true,
    "harvester_type": "geonode.harvesting.harvesters.wms.WmsHarvester",
    "num_harvestable_resources": 150,
    "service_id": 4,
    "service_description": "Mi servicio WMS"
  }
}
```

---

## 6. Datasets de Servicios Remotos

### GET /api/v2/sigic-remote-datasets/

Lista datasets con filtros por harvester o servicio.

#### Parámetros de Query

| Parámetro | Descripción |
|-----------|-------------|
| `harvester_id` | Filtrar por ID del harvester |
| `service_id` | Filtrar por ID del servicio |

#### Request

```javascript
// Filtrar por harvester
const response = await fetch('/api/v2/sigic-remote-datasets/?harvester_id=3', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

---

## Validación Previa (GetCapabilities)

Antes de registrar un servicio OWS, se recomienda validar la URL:

```javascript
async function validarServicioOWS(url) {
  try {
    // Construir URL de GetCapabilities
    const capabilitiesUrl = new URL(url);
    capabilitiesUrl.searchParams.set('service', 'WMS');
    capabilitiesUrl.searchParams.set('request', 'GetCapabilities');

    const response = await fetch(capabilitiesUrl.toString());

    if (!response.ok) {
      return { valid: false, error: `HTTP ${response.status}` };
    }

    const text = await response.text();

    // Verificar que sea XML válido de WMS
    if (text.includes('WMS_Capabilities') || text.includes('WMT_MS_Capabilities')) {
      return { valid: true, type: 'WMS' };
    }

    return { valid: false, error: 'Respuesta no es WMS válido' };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}
```

---

## Validación para Archivos

```javascript
const EXTENSIONES_PERMITIDAS = ['csv', 'json', 'geojson', 'xls', 'xlsx'];

function validarExtensionArchivo(url) {
  try {
    const path = new URL(url).pathname;
    const extension = path.split('.').pop().toLowerCase();
    return EXTENSIONES_PERMITIDAS.includes(extension);
  } catch {
    return false;
  }
}
```

---

## Flujo Completo de Registro

```javascript
async function registrarServicioRemoto(url, tipo, descripcion, token) {
  // 1. Validar según tipo
  if (tipo === 'FILE') {
    if (!validarExtensionArchivo(url)) {
      throw new Error('Extensión no soportada');
    }
  } else if (['WMS', 'OWS', 'AUTO'].includes(tipo)) {
    const validacion = await validarServicioOWS(url);
    if (!validacion.valid) {
      throw new Error(validacion.error);
    }
  }

  // 2. Registrar en backend
  const response = await fetch('/api/v2/services/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      url: url,
      type: tipo,
      description: descripcion
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Error al registrar servicio');
  }

  return response.json();
}

// Uso
try {
  const servicio = await registrarServicioRemoto(
    'https://stable.demo.geonode.org/geoserver/ows',
    'WMS',
    'GeoNode Demo Server',
    token
  );
  console.log('Servicio registrado:', servicio);
} catch (error) {
  console.error('Error:', error.message);
}
```

---

## Estados del Harvester

| Estado | Descripción |
|--------|-------------|
| `ready` | Listo para operar |
| `updating-harvestable-resources` | Actualizando lista de recursos |
| `performing-harvesting` | Importando recursos |
| `checking-availability` | Verificando disponibilidad |

---

## Notas Importantes

1. **URL única por usuario**: La misma URL puede registrarse por diferentes usuarios, pero no dos veces para el mismo usuario.

2. **Detección automática**: Si `type=AUTO`, el sistema intentará detectar el tipo de servicio automáticamente.

3. **Harvester asincrónico**: Después de registrar un servicio, el harvester comienza a descubrir recursos en segundo plano. El campo `num_harvestable_resources` se actualiza conforme se descubren.

4. **Permisos**: Los usuarios no superusuarios solo ven sus propios servicios y harvesters.
