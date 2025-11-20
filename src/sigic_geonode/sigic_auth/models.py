# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

# src/sigic_geonode/permissions/models.py

import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class SigicGroup(models.Model):
    """
    Grupo funcional dentro del sistema SIGIC.
    No es un "grupo" de Django ni un "group" de Keycloak.
    Es un contenedor lógico multi-organización.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class SigicRole(models.Model):
    """
    Roles globales: view, edit, admin, etc.
    No están ligados a grupos; son capacidades puras.
    """

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class UserGroupRole(models.Model):
    """
    Relación contextual que define el permiso real:
    El usuario U tiene el rol R dentro del grupo G.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(SigicGroup, on_delete=models.CASCADE)
    role = models.ForeignKey(SigicRole, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "group", "role")
        verbose_name = "User group role"
        verbose_name_plural = "User group roles"

    def __str__(self):
        return f"{self.user} → {self.role.name} @ {self.group.name}"


class UserInvitation(models.Model):
    """
    Invitación para un usuario a un grupo con cierto rol.
    Se maneja enteramente en SIGIC, NO en Keycloak.
    """

    email = models.EmailField()
    group = models.ForeignKey(SigicGroup, on_delete=models.CASCADE)
    roles = models.ManyToManyField(SigicRole)

    token = models.CharField(max_length=64, unique=True, editable=False)
    accepted = models.BooleanField(default=False)
    issued_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Invitation to {self.email} for {self.group.name}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=72)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
