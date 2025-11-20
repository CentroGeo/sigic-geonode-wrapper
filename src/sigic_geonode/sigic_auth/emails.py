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

# src/sigic_geonode/sigic_auth/emails.py

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_invitation_email(invitation):
    site = settings.SITEURL  # termina en "/"
    accept_url = f"{site}api/v2/auth/invitations/accept/{invitation.token}/"

    subject = "Invitación al sistema SIGIC"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [invitation.email]

    text_body = f"""
Te han invitado a unirte al grupo "{invitation.group.name}" en SIGIC.

Para aceptar la invitación, abre este enlace:
{accept_url}

La invitación expirará en 72 horas.
"""

    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
  <h2>Invitación a SIGIC</h2>
  <p>Has sido invitado a unirte al grupo <strong>{invitation.group.name}</strong>.</p>

  <p>Para continuar, haz clic en el siguiente botón:</p>

  <p>
    <a href="{accept_url}"
       style="padding: 10px 18px; background-color: #0284c7; color: white; text-decoration: none; border-radius: 6px;">
      Aceptar invitación
    </a>
  </p>

  <p>Este enlace expirará en <strong>72 horas</strong>.</p>
</body>
</html>
"""

    msg = EmailMultiAlternatives(subject, text_body, from_email, to)
    msg.attach_alternative(html_body, "text/html")
    msg.send()
