# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Tareas Celery para el módulo sigic_remote_services.

Incluye:
- reset_and_retry_harvester: función pura de negocio reutilizable
- check_stuck_harvesters: tarea periódica de recuperación automática
"""

import logging
import time

from django.conf import settings

from sigic_geonode.celeryapp import app

logger = logging.getLogger(__name__)

STUCK_STATUSES = {"updating-harvestable-resources", "performing-harvesting", "harvesting-resources"}
STUCK_CACHE_KEY_PREFIX = "sigic_harvester_first_seen_stuck_"


def reset_and_retry_harvester(harvester_pk: int) -> dict:
    """
    Resetea un harvester atascado a 'ready' y redispara la cosecha.

    Función pura reutilizable por el endpoint manual (views.py) y la tarea
    periódica (check_stuck_harvesters). No tiene dependencias HTTP.

    Retorna un dict con:
        reset (bool): si se ejecutó el reset de estado
        dispatched (bool): si la tarea de cosecha fue disparada
        error (str|None): código de error o None si todo fue exitoso
            'not_found'    — harvester no existe
            'wrong_status' — estado no es 'ready' tras el intento de reset
            str(excepción) — error al llamar apply_async
    """
    from geonode.harvesting.models import Harvester

    try:
        harvester = Harvester.objects.get(pk=harvester_pk)
    except Harvester.DoesNotExist:
        logger.error(f"[SIGIC] reset_and_retry_harvester: harvester {harvester_pk} no encontrado")
        return {"reset": False, "dispatched": False, "error": "not_found"}

    previous_status = harvester.status
    if harvester.status in STUCK_STATUSES:
        Harvester.objects.filter(pk=harvester_pk).update(status="ready")
        harvester.refresh_from_db()
        logger.info(
            f"[SIGIC] Harvester {harvester_pk} reseteado de '{previous_status}' a 'ready'"
        )

    if harvester.status != "ready":
        logger.warning(
            f"[SIGIC] Harvester {harvester_pk} en estado '{harvester.status}' "
            f"tras intento de reset: no se puede redisparar"
        )
        return {"reset": False, "dispatched": False, "error": "wrong_status"}

    try:
        harvester.initiate_update_harvestable_resources()
        logger.info(
            f"[SIGIC] Actualización de recursos harvestables iniciada para harvester {harvester_pk}"
        )
        return {"reset": True, "dispatched": True, "error": None}
    except Exception as e:
        logger.error(
            f"[SIGIC] Error al iniciar actualización de recursos para harvester {harvester_pk}: {e}"
        )
        return {"reset": True, "dispatched": False, "error": str(e)}


@app.task(
    bind=True,
    name="sigic_geonode.sigic_remote_services.check_stuck_harvesters",
    queue="default",
    max_retries=0,
)
def check_stuck_harvesters(self):
    """
    Detecta harvesters atascados y los resetea automáticamente.

    Usa un mecanismo de doble-gate con Django cache para evitar interrumpir
    cosechas legítimamente lentas:

    1. Primer ciclo que detecta el harvester en estado stuck:
       guarda el timestamp en cache (grace period iniciado).
    2. Ciclos siguientes: si (now - first_seen) > HARVESTER_STUCK_TIMEOUT_SECONDS
       se resetea el harvester y se redispara la cosecha.
    3. Tras reset exitoso: se limpia la clave de cache.
    4. Si el redisparo falla: se mantiene la clave de cache para reintentar
       en el próximo ciclo (el harvester ya quedó en 'ready').
    """
    from django.core.cache import cache
    from geonode.harvesting.models import Harvester

    timeout_seconds = getattr(settings, "HARVESTER_STUCK_TIMEOUT_SECONDS", 3600)

    stuck_harvesters = list(Harvester.objects.filter(status__in=STUCK_STATUSES))
    now = time.time()

    processed = 0
    reset_count = 0
    skip_count = 0
    error_count = 0

    for harvester in stuck_harvesters:
        processed += 1
        cache_key = f"{STUCK_CACHE_KEY_PREFIX}{harvester.pk}"
        first_seen = cache.get(cache_key)

        if first_seen is None:
            cache.set(cache_key, now, timeout=timeout_seconds * 3)
            logger.info(
                f"[SIGIC] Harvester {harvester.pk} detectado atascado en "
                f"'{harvester.status}' por primera vez. Grace period iniciado "
                f"({timeout_seconds}s)."
            )
            skip_count += 1
            continue

        elapsed = now - first_seen
        if elapsed < timeout_seconds:
            logger.debug(
                f"[SIGIC] Harvester {harvester.pk} atascado hace {elapsed:.0f}s "
                f"(umbral: {timeout_seconds}s). En grace period."
            )
            skip_count += 1
            continue

        logger.warning(
            f"[SIGIC] Harvester {harvester.pk} lleva {elapsed:.0f}s en estado "
            f"'{harvester.status}'. Ejecutando reset automático."
        )

        result = reset_and_retry_harvester(harvester.pk)

        if result["dispatched"]:
            cache.delete(cache_key)
            reset_count += 1
            logger.info(
                f"[SIGIC] Harvester {harvester.pk} recuperado automáticamente."
            )
        elif result["error"] == "wrong_status":
            # El estado cambió entre la query y el reset (race condition benigna)
            cache.delete(cache_key)
            skip_count += 1
        else:
            # Reset ejecutado pero redisparo falló — mantener cache key
            error_count += 1
            logger.error(
                f"[SIGIC] Harvester {harvester.pk}: reset OK pero redisparo falló. "
                f"Se reintentará en el próximo ciclo. Error: {result['error']}"
            )

    logger.info(
        f"[SIGIC] check_stuck_harvesters completado: "
        f"{processed} revisados, {reset_count} reseteados, "
        f"{skip_count} en grace period, {error_count} con error de redisparo."
    )
