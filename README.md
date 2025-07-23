# Geonode Wrapper

Proyecto envoltorio de GeoNode. 

Este es un proyecto Django con soporte para GeoNode incluido como biblioteca.

Contiene un Dockerfile y un docker-compose para facilitar el despliegue de un servidor GeoNode en una VM.

## Tabla de Contenidos

-  [Inicio rápido con Docker](#quick-docker-start)
-  [Crear un proyecto personalizado](#create-a-custom-project)
-  [Iniciar tu servidor usando Docker](#start-your-server-using-docker)
-  [Ejecutar la instancia en un sitio público](#run-the-instance-on-a-public-site)
-  [Detener las imágenes Docker](#stop-the-docker-images)
-  [Respaldo y restauración desde imágenes Docker](#backup-and-restore-the-docker-images)
-  [Consejos: configuración de `requirements.txt`](#hints-configuring-requirementstxt)
- [Guía para levantar GeoNode SIGIC localmente](#guía-para-levantar-geonode-sigic-localmente)


## Inicio rápido con Docker


  ```bash
    python3.10 -m venv ~/.venvs/project_name
    source ~/.venvs/sigic_geonode/bin/activate

    pip install Django==4.2.9

    mkdir ~/project_name

    GN_VERSION=main # Define la rama o etiqueta desde la que deseas generar el proyecto
    django-admin startproject --template=http://gitlab.geoint.mx/sigic/geonode-compose/-/archive/$GN_VERSION/geonode-compose-main.zip -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile project_name ~/project_name

    cd ~/project_name
    python create-envfile.py 
  ```
`create-envfile.py` acepta los siguientes argumentos:

- `--https`: Habilita SSL. Está deshabilitado por defecto.
- `--env_type`: Define el tipo de entorno:
   - `prod`: Se desactiva`DEBUG` y se solicita un certificado `SSL` válido al servidor ACME de Let's Encrypt.
   - `test`: Se desactiva `DEBUG` y se genera un certificado `SSL` de prueba para uso local.
   - `dev`: Se activa `DEBUG` y no se genera ningún certificado `SSL`.
- `hostname`:  URL que alojará GeoNode (por defecto: `localhost`).
- `email`: Correo electrónico del administrador. Se requiere una dirección válida y una configuración `SMTP` funcional si `--env_type` está configurado como `prod`, ya que Let's Encrypt utiliza este correo para emitir el certificado `SSL`.
- `--geonodepwd`: Contraseña del administrador de GeoNode. Si se deja en blanco, se genera un valor aleatorio.
- `--geoserverpwd`: Contraseña del administrador de GeoServer. Si se deja en blanco, se genera un valor aleatorio.
- `--pgpwd`: Contraseña del usuario administrador de PostgreSQL. Si se deja en blanco, se genera un valor aleatorio.
- `--dbpwd`: Contraseña del usuario de la base de datos principal de GeoNode. Si se deja en blanco, se genera un valor aleatorio.
- `--geodbpwd`: Contraseña del usuario de la base de datos de datos geoespaciales. Si se deja en blanco, se genera un valor aleatorio.
- `--clientid`: ID de cliente OAuth2 de GeoServer para GeoNode. Si se deja en blanco, se genera un valor aleatorio.
- `--clientsecret`: El `secret` del cliente OAuth2 de GeoServer para GeoNode. Si se deja en blanco, se genera un valor aleatorio.


```bash
  docker compose build
  docker compose up -d
```

### Iniciar tu servidor usando Docker

Necesitas Docker 1.12 o superior. Obtén la última versión oficial estable para tu plataforma.
Once you have the project configured run the following command from the root folder of the project.

1. Ejecuta `docker-compose` para iniciar el servicio

    ```bash
    docker-compose build --no-cache
    docker-compose up -d
    ```

    ```bash
    set COMPOSE_CONVERT_WINDOWS_PATHS=1
    ```

    antes de ejecutar  `docker-compose up`

2. Accede al sitio en http://localhost/

## Ejecutar la instancia en un sitio público

### Startup the image

```bash
docker-compose up --build -d
```

### Detener las imágenes Docker

```bash
docker-compose stop
```

### Eliminar completamente las imágenes Docker

**ADVERTENCIA**: Esto eliminará todos los contenedores e imágenes creados hasta el momento.

**NOTA**: Los contenedores deben estar detenidos antes de poder eliminarlos.

```bash
docker system prune -a
```

## Respaldo y restauración desde imágenes Docker

### Ejecutar un respaldo

```bash
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./sigic_geonode/br/backup.sh $BKP_FOLDER_NAME
```

- BKP_FOLDER_NAME:
  Valor por defecto = backup_restore
  Nombre de la carpeta de respaldo compartida.
  TLos scripts asumen que está ubicada en "root"  por ejemplo:  /$BKP_FOLDER_NAME/

- SOURCE_URL:
  URL del servidor de origen, el que genera el archivo  `backup`.

- TARGET_URL:
  URL del servidor de destino, el que debe sincronizarse.

Ejemplo:

```bash
docker exec -it django4sigic_geonode sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./sigic_geonode/br/backup.sh $BKP_FOLDER_NAME'
```

### Ejecutar una restauración

```bash
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./sigic_geonode/br/restore.sh $BKP_FOLDER_NAME
```

- BKP_FOLDER_NAME:
  Valor por defecto = backup_restore
  Nombre de la carpeta de respaldo compartida.
  Los scripts asumen que está ubicada en "root", por ejemplo: /$BKP_FOLDER_NAME/

- SOURCE_URL:
  URL del servidor de origen, el que genera el archivo de `backup`.

- TARGET_URL:
  URL del servidor de destino, el que debe sincronizarse.

Ejemplo:

```bash
docker exec -it django4sigic_geonode sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./sigic_geonode/br/restore.sh $BKP_FOLDER_NAME'
```

## Aumentar conexiones máximas de PostgreSQL

En caso de que necesites aumentar el número máximo de conexiones de PostgreSQL, puedes modificar la variable  **POSTGRESQL_MAX_CONNECTIONS** en el archivo **.env** de la siguiente manera:

```
POSTGRESQL_MAX_CONNECTIONS=200
```

En este caso, PostgreSQL se ejecutará aceptando un máximo de 200 conexiones simultáneas.




## Guía  para levantar GeoNode SIGIC localmente


### Pre-requisitos

Asegúrate de tener instalado en tu máquina virtual :

- Python 3.10
- Git
- Docker
- Docker Compose v2

### ESCENARIO A: Instalación inicial

#### 1. Clonar el repositorio oficial

```bash 
git clone https://gitlab.centrogeo.edu.mx/sigic/geonode-compose.git
cd geonode-compose

```
#### 2. Crear y editar el archivo .env

```
python3 create-envfile.py —env_type=dev —hostname=ip/host/dominio

```

El comando `create-envfile.py` debe adaptarse a la configuración específica de cada entorno.  
Por ejemplo, si estás trabajando en una máquina virtual local o en una red privada, puedes usar la IP de la VM como `--hostname`, o bien un nombre de dominio si ya cuentas con uno asignado públicamente.

`--env_type:`
Define el tipo de entorno SSL:

`dev:` DEBUGSSL está habilitado, pero no se genera ningún certificado.

`--hostname:`
La URL donde se servirá GeoNode. Por defecto es localhost.

```
nano .env
```
En el archivo `.env`, configura las variables para que tengan las siguientes caracteristicas:

```
SOCIALACCOUNT_OIDC_PROVIDER_ENABLED=True
SOCIALACCOUNT_ADAPTER=sigic_geonode.auth.account_adapters.SigicOpenIDConnectAdapter
SOCIALACCOUNT_PROVIDER_NAME=SIGICSSO

SOCIALACCOUNT_OIDC_ACCESS_TOKEN_URL=https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/token
SOCIALACCOUNT_OIDC_AUTHORIZE_URL=https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/auth
SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER=https://iam.dev.geoint.mx/realms/sigic
SOCIALACCOUNT_OIDC_PROFILE_URL=https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/userinfo

GITLAB_USER=tu_usuario_gitlab
GITLAB_USERPAT=tu_token_personal
GITLAB_IP=10.2.7.26

```
>`SOCIALACCOUNT_OIDC_PROVIDER_ENABLED` debe configurarse en `true` o `false` dependiendo de si se quiere habilitar la autenticación con OIDC (mediante Keycloak). Si no se va utilizar OIDC, puedes establecerla en `false`.

>`GITLAB_USER` y `GITLAB_USERPAT` son necesarias para autenticarte correctamente y permitir el acceso a los repositorios privados en GitLab. En caso de no contar con un token de acceso personal (Personal Access Token) de GitLab.


####  3. Da permisos a scripts

Utilice el siguiente comando en la terminal:
```
chmod +x fix_network.sh
```

Este comando modifica los permisos del archivo, otorgándole al usuario actual la capacidad de ejecutarlo. Sin este paso, intentar ejecutar el script podría resultar en un error de `“permiso denegado”`.

#### 4. Crear la red Docker externa
Debido a características particulares de la infraestructura de red disponible es necesario crear manualmente una red Docker externa con ciertas modificaciones.

> ⚠️ En condiciones normales no se requeriría este paso, pero en este entorno es obligatorio para que los contenedores se comuniquen correctamente entre sí.

Utiliza el script incluido en el repositorio:

```
sudo sh fix_network.sh
```
Este comando crea la red llamada sigic-network con los parámetros específicos necesarios (driver bridge, MTU reducido), los cuales evitan problemas de conectividad entre contenedores y con servicios externos como GeoServer o PostgreSQL.

####  5. Construye los servicios

Para este paso, se utiliza el script incluido en el repositorio que automatiza tanto la construcción como el levantamiento de los servicios necesarios para GeoNode:

```
sudo sh docker-build.sh

```

> Importante: Durante el primer arranque de los contenedores, es posible que alguno de ellos (especialmente django4sigic_geonode) muestre un estado de error o aparezca como `unhealthy`. Esto es un comportamiento normal, ya que algunos servicios requieren más tiempo para inicializar correctamente o dependen de que otros contenedores estén completamente listos.
>
En este caso, simplemente espere unos minutos y vuelva a ejecutar el comando


####  6. Accede a GeoNode

Abre tu navegador e ingresa:

```
http://<TU_IP>:8000
```

Puedes conocer tu IP con:

```
ip a
```

Busca la IP de la interfaz `eth0`.

__________________________________________________________________

### ESCENARIO B: Actualizacion

Sigue estos pasos para *actualizar el código y reconstruir solo si es necesario*.


#### Paso 1: Ir al directorio del proyecto

```
cd ~/geonode-compose
```

#### Paso 2: Verifica si tienes cambios locales (opcional)

```
git status
```

* Si tienes cambios no confirmados, guarda con:

```
git stash
```

#### Paso 3: Hacer git pull para obtener la actualizacion del repositorio

```
git pull
```
Este paso es *obligatorio antes de reconstruir*.
El proyecto se actualiza con frecuencia, y si no haces pull, pueden fallar dependencias.


#### Paso 4: Ejecutar el script de red por seguridad

```
sudo sh fix_network.sh
```

> Asegúrate de que la red sigic-network siga existiendo y esté configurada correctamente.


#### Paso 5: Reconstruir los servicios (si hay cambios)

Para este paso, se utiliza el script incluido en el repositorio que automatiza tanto la construcción como el levantamiento de los servicios necesarios para GeoNode:


```
sudo sh docker-build.sh
```

Este comando se debe ejecutar tanto al instalar por primera vez como al actualizar el proyecto después de un git pull.

> Asegúrate de haber ejecutado previamente sh fix_network.sh y de tener el archivo .env correctamente configurado.

### Resumen de comandos

#### Primer uso

```
git clone https://gitlab.centrogeo.edu.mx/sigic/geonode-compose.git
cd geonode-compose
cp .env.sample .env
nano .env  # corrige valores
sudo sh fix_network.sh
sudo sh docker-build.sh
```

#### Actualización

```
cd geonode-compose
git stash  # opcional si tienes cambios
git pull
sudo sh fix_network.sh
sudo sh docker-build.sh

```

## Verificación de los servicios

```
docker ps
```

Verifica si los contenedores están corriendo correctamente.


### Logs de servicios

```
docker compose logs -f
```

### Verifica conectividad a GitLab

Antes de levantar los contenedores, asegúrate de que tu máquina puede acceder al GitLab que contiene los repos privados (por ejemplo: `gitlab.centrogeo.edu.mx`).

```
ping gitlab.centrogeo.edu.mx
```

* Si responde, tienes conectividad básica.
* Si dice `Name or service not known` o `Destination Host Unreachable`, hay un problema de DNS o red.


### Verifica con `curl`

```
curl -I https://gitlab.centrogeo.edu.mx
```

Deberías ver una respuesta `HTTP/2 200` o algo similar.


### Verifica interfaces de red con `ip link`

Esto te permite confirmar que las interfaces como `docker0` o `br-...` están activas (`UP`), especialmente si tuviste problemas de conexión entre contenedores.

```
ip link
```

Verás algo así:

```
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
3: docker0: <NO-CARRIER,BROADCAST,MULTICAST,DOWN> ...
4: br-xxxxxx: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
```


*  Las interfaces que usas deben aparecer como `UP`.
*  Si están `DOWN`, reinicia Docker:

```
sudo systemctl restart docker
```

Y/o recrea la red personalizada:

```bash
docker network rm sigic-network
docker network create \
  --driver=bridge \
  --opt com.docker.network.driver.mtu=1360 \
  sigic-network
```