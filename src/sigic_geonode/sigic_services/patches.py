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

# sigic_services/patches.py

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from geonode.services import forms as service_forms
from geonode.services import views as service_views
from geonode.services.models import Service
from geonode.services.serviceprocessors import get_service_handler
from geonode.services import enumerations

import logging
logger = logging.getLogger(__name__)

"""
Monkey patch helpers to allow registering the same remote service base URL per owner.

### Quick enable from a GeoNode project wrapper
Add the provided app to ``INSTALLED_APPS`` so it runs at startup::

    INSTALLED_APPS += [
        "geonode.monkey_patches.owner_scoped_services_app",
    ]

The app simply calls ``apply_owner_scoped_service_registration`` during ``AppConfig.ready``.
You can also call the function manually if you prefer finer control::

    from geonode.monkey_patches.owner_scoped_services import apply_owner_scoped_service_registration
    apply_owner_scoped_service_registration()

This adjusts the in-memory model metadata and overrides the service registration
form/view to scope URL uniqueness checks to the requesting user. No core edits are
required; import and call ``apply_owner_scoped_service_registration`` early during
startup.
"""


class OwnerScopedCreateServiceForm(service_forms.CreateServiceForm):
    """Service registration form that enforces base URL uniqueness per owner."""

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner

    def clean_url(self):
        proposed_url = self.cleaned_data["url"]
        filter_kwargs = {"base_url": proposed_url}
        if self.owner is not None:
            filter_kwargs["owner"] = self.owner
        exists_for_owner = Service.objects.filter(**filter_kwargs).exists()
        if exists_for_owner:
            raise ValidationError(_("Service %(url)s is already registered"), params={"url": proposed_url})
        return proposed_url

    def clean(self):
        super().clean()
        url = self.cleaned_data.get("url")
        service_type = self.cleaned_data.get("type")
        if url is not None and service_type is not None:
            try:
                service_handler = get_service_handler(base_url=url, service_type=service_type)
            except Exception as exc:
                raise ValidationError(_("Could not connect to the service at %(url)s"), params={"url": url}) from exc
            if not service_handler.probe():
                raise ValidationError(_("Could not connect to the service at %(url)s"), params={"url": url})
            if service_type not in (enumerations.AUTO, enumerations.OWS):
                if service_handler.service_type != service_type:
                    raise ValidationError(
                        _("Found service of type %(found_type)s instead of %(service_type)s"),
                        params={"found_type": service_handler.service_type, "service_type": service_type},
                    )
            self.cleaned_data["service_handler"] = service_handler
            self.cleaned_data["type"] = service_handler.service_type


def _patch_service_model_constraint():
    """Make ``base_url`` unique per owner at the model metadata level."""

    base_url_field = Service._meta.get_field("base_url")
    if base_url_field.unique:
        base_url_field._unique = False

    constraint_name = "service_owner_base_url_unique"
    has_constraint = any(getattr(c, "name", "") == constraint_name for c in Service._meta.constraints)
    if not has_constraint:
        Service._meta.constraints.append(
            models.UniqueConstraint(fields=["owner", "base_url"], name=constraint_name)
        )


def _patched_register_service_view():
    """Register service view that feeds the current user into the patched form."""

    @login_required
    def register_service(request):
        service_register_template = "services/service_register.html"
        if request.method == "POST":
            form = OwnerScopedCreateServiceForm(request.POST, owner=request.user)
            if form.is_valid():
                service_handler = form.cleaned_data["service_handler"]
                service = service_handler.create_geonode_service(owner=request.user)
                service.full_clean()
                service.save()
                service.keywords.add(*service_handler.get_keywords())

                if service_handler.indexing_method == enumerations.CASCADED:
                    service_handler.create_cascaded_store(service)
                service_handler.geonode_service_id = service.id
                request.session[service_handler.url] = service_handler
                service_views.logger.debug("Added handler to the session")
                service_views.messages.add_message(
                    request, service_views.messages.SUCCESS, _("Service registered successfully")
                )
                return service_views.HttpResponseRedirect(
                    service_views.reverse("harvest_resources", kwargs={"service_id": service.id})
                )
            return service_views.render(request, service_register_template, {"form": form})

        form = OwnerScopedCreateServiceForm(owner=request.user)
        return service_views.render(request, service_register_template, {"form": form})

    return register_service


def apply_owner_scoped_service_registration():
    """Apply monkey patches so services can share URLs across different owners."""

    _patch_service_model_constraint()
    service_forms.CreateServiceForm = OwnerScopedCreateServiceForm
    service_views.register_service = _patched_register_service_view()
