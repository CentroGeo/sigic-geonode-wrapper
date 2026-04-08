# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from django.contrib import admin

from .models import (
    Indicator,
    IndicatorFieldBoxInfo,
    IndicatorGroup,
    Site,
    SiteConfiguration,
    SiteLogos,
    SubGroup,
)


class SiteLogosInline(admin.TabularInline):
    model = SiteLogos
    extra = 0


class SiteConfigurationInline(admin.StackedInline):
    model = SiteConfiguration
    extra = 0


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ["name", "title", "url"]
    search_fields = ["name", "title", "url"]
    inlines = [SiteLogosInline, SiteConfigurationInline]


@admin.register(SiteLogos)
class SiteLogosAdmin(admin.ModelAdmin):
    list_display = ["site", "icon_link", "stack_order"]
    list_filter = ["site"]


@admin.register(IndicatorGroup)
class IndicatorGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "site", "stack_order"]
    list_filter = ["site"]
    search_fields = ["name"]


@admin.register(SubGroup)
class SubGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "group", "stack_order"]
    list_filter = ["group__site", "group"]
    search_fields = ["name"]


class IndicatorFieldBoxInfoInline(admin.TabularInline):
    model = IndicatorFieldBoxInfo
    extra = 0


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ["name", "site", "group", "subgroup", "plot_type", "stack_order"]
    list_filter = ["site", "group", "subgroup", "is_histogram"]
    search_fields = ["name"]
    inlines = [IndicatorFieldBoxInfoInline]


@admin.register(IndicatorFieldBoxInfo)
class IndicatorFieldBoxInfoAdmin(admin.ModelAdmin):
    list_display = ["name", "indicator", "field", "stack_order"]
    list_filter = ["indicator__site"]
    search_fields = ["name", "field"]


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ["site", "show_header", "show_footer", "site_font_style"]
