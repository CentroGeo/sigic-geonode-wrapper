// ==============================================================================
//  SIGIC – Sistema Integral de Gestión e Información Científica
//
//  Autor: César Benjamín (cesarbenjamin.net)
//  Derechos patrimoniales: CentroGeo (2025)
//
//  Nota:
//    Este código fue desarrollado para el proyecto SIGIC de
//    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
//    pertenece a CentroGeo conforme a obra por encargo.
//
//  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
// ==============================================================================


// ==============================================
//  SIGIC Mapper: Inserta roles por grupo en token
// ==============================================
//
// Este mapper llama al backend SIGIC:
//
//   GET /api/auth/group-roles/
//
// usando el mismo access token del usuario.
//
// Devuelve algo como:
//
//  {
//    "groups": {
//       "baches": ["view", "edit"],
//       "accidentes": ["admin"]
//    }
//  }
//
// Y lo mete en el token como:
//
//   sigic_groups_roles: { ... }
//
// ==============================================

var Http = Java.type("java.net.HttpURLConnection");
var URL = Java.type("java.net.URL");
var InputStreamReader = Java.type("java.io.InputStreamReader");
var BufferedReader = Java.type("java.io.BufferedReader");
var StringBuilder = Java.type("java.lang.StringBuilder");

(function() {

    // URL de SIGIC – viene desde Keycloak client config
    var site = keycloakSession.getContext().getRealm().getAttribute("sigic_site_url");
    if (!site) {
        // fallback por si olvidan configurarlo
        site = "https://sigic.dev.geoint.mx/";
    }

    var endpoint = site + "api/auth/group-roles/";

    try {
        var url = new URL(endpoint);
        var conn = url.openConnection();
        conn.setRequestMethod("GET");

        // Token del usuario
        var token = keycloakSession.getContext().getRequestHeaders().getRequestHeader("Authorization");
        if (token && token.size() > 0) {
            conn.setRequestProperty("Authorization", token.get(0));
        }

        conn.connect();

        var status = conn.getResponseCode();

        if (status != 200) {
            // Si falla, no rompe la autenticación
            return {};
        }

        var reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        var out = new StringBuilder();
        var line;

        while ((line = reader.readLine()) != null) {
            out.append(line);
        }

        reader.close();

        var json = JSON.parse(out.toString());

        // Tomamos solo el objeto "groups"
        return json.groups || {};

    } catch (e) {
        // Si hay error, no bloquea el login
        return {};
    }

})();


/*
PASO 4 — Agregar el Client Scope a tu cliente

Tu cliente (ej. sigic-nuxt, sigic-geonode) necesita este scope.

Ve a:

Clients → tu-cliente → Client Scopes

En Assigned Default Client Scopes agrega:

sigic-roles

Con eso el token siempre incluirá el mapper.

PASO 5 — Configurar variable sigic_site_url en el realm

Para que el script no tenga hardcode:

Keycloak → Realm Settings

Pestaña: Attributes

New attribute:

Name: sigic_site_url
Value: <settings.SITEURL>  (p.ej. https://sigic.dev.geoint.mx/)

ASO 6 — PROBAR EL TOKEN

Haz login desde SIGIC o desde Keycloak.

Luego usa:

https://jwt.io

echo "<TOKEN>" | jq -R 'split(".") | .[1] | @base64d | fromjson'

"sigic_groups_roles": {
  "baches": ["view", "edit"],
  "accidentes": ["admin"]
}

PASO 7 — Comportamiento final

El mapper usa el mismo access token que Keycloak genera.

Llama al endpoint /api/auth/group-roles/.

SIGIC lee al usuario desde ese token.

Devuelve la estructura roles/grupos.

Keycloak mete eso en el token final.

Esto permite:

✔ Nuxt pueda leer roles por grupo sin llamar al backend
✔ GeoNode pueda filtrar recursos por roles del token
✔ Un NGINX / Traefik / OpenResty pueda hacer authz solo con claims
✔ Tu IA pueda tomar decisiones basadas en roles
✔ No tocar la BD en cada request
*/
