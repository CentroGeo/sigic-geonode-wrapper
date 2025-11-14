from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from geonode.layers.models import Dataset, Style

from .utils import set_default_style

try:
    admin.site.unregister(Dataset)
except NotRegistered:
    pass

try:
    admin.site.unregister(Style)
except NotRegistered:
    pass


@admin.register(Style)
class CustomLayerStyleAdmin(admin.ModelAdmin):
    """
    Admin personalizado para gestionar estilos SLD directamente.
    """

    list_display = (
        "name",
        "dataset",
        "is_default",
        "sld_url",
        "created",
        "last_modified",
    )
    list_filter = ("is_default", "dataset")
    search_fields = ("name", "dataset__alternate", "sld_url")
    readonly_fields = ("sld_url",)

    actions = ["set_as_default"]

    @admin.action(description="Marcar como estilo predeterminado")
    def set_as_default(self, request, queryset):
        from .utils import set_default_style

        for style in queryset:
            try:
                set_default_style(style.dataset.alternate, style.name)
                self.message_user(
                    request,
                    f"El estilo '{style.name}' se estableció como predeterminado para '{style.dataset.alternate}'.",
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Error al actualizar '{style.name}': {e}",
                    level="error",
                )


class LayerStyleInline(admin.TabularInline):
    """
    Inline dentro del Dataset admin para gestionar los estilos SLD.
    """

    model = Style
    extra = 0
    readonly_fields = ("sld_url", "is_default", "preview_link", "set_default_button")
    fields = ("name", "is_default", "sld_url", "preview_link", "set_default_button")
    can_delete = False

    def preview_link(self, obj):
        if obj.sld_url:
            return format_html('<a href="{}" target="_blank">Ver SLD</a>', obj.sld_url)
        return "-"

    preview_link.short_description = "Vista previa"

    def set_default_button(self, obj):
        """
        Botón que dispara la acción para marcar el estilo como default.
        """
        if not obj.pk:
            return "-"
        if obj.is_default:
            return format_html("<b>✓ Predeterminado</b>")
        url = reverse("admin:set_default_style", args=[obj.dataset.pk, obj.pk])
        return format_html(
            '<a class="button" href="{}" '
            'style="padding:2px 6px;background:#3a7bd5;color:white;'
            'border-radius:4px;text-decoration:none;">Marcar como default</a>',
            url,
        )

    set_default_button.short_description = "Acción"


@admin.register(Dataset)
class CustomDatasetAdmin(admin.ModelAdmin):
    """
    Admin de Dataset extendido con inline de estilos.
    """

    inlines = [LayerStyleInline]
    list_display = ("alternate", "title", "owner", "date", "is_approved")
    search_fields = ("alternate", "title", "owner__username")
    list_filter = ("owner", "date")

    def get_urls(self):
        """
        Agrega una URL custom para procesar el clic del botón 'Marcar como default'.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:dataset_id>/styles/<int:style_id>/set-default/",
                self.admin_site.admin_view(self.set_default_action),
                name="set_default_style",
            ),
        ]
        return custom_urls + urls

    def set_default_action(self, request, dataset_id, style_id):
        """
        Acción que se ejecuta al presionar el botón 'Marcar como default'.
        """
        try:
            dataset = Dataset.objects.get(pk=dataset_id)
            style = Style.objects.get(pk=style_id, dataset=dataset)
            set_default_style(dataset.alternate, style.name)
            messages.success(
                request,
                f"El estilo '{style.name}' ahora es el predeterminado para '{dataset.alternate}'.",
            )
        except Exception as e:
            messages.error(request, f"Error al cambiar el estilo por defecto: {e}")
        return redirect(
            reverse("admin:geonode_layers_dataset_change", args=[dataset_id])
        )
