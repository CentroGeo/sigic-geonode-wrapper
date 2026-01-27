from itertools import chain

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse

from idegeo_base.models import SiteStyle
from idegeo_base.forms import InterfaceForm
from idegeo_content_handler.views import handler_home
from idegeo_content_handler.views import handler_home
from idegeo_content_handler.models import Header, Style, Menu


def index(request):
    obj = SiteStyle.objects.all()
    styles = ""
    for i in obj:
        styles = i

    home = None
    header = None
    style = None
    topics = None
    sections = None
    items_list = None
    second_menu = None
    if str(type(styles)) == "<class 'idegeo.base.models.SiteStyle'>":
        if styles.cms:
            return handler_home(request, styles.cmsHome.url_name)

        if styles.cmsPublic and styles.cmsMenu:
            home = styles.cmsMenu
            try:
                header = Header.objects.get(home=styles.cmsMenu)
            except Header.DoesNotExist:
                pass
            try:
                style = Style.objects.get(header=header)
            except Style.DoesNotExist:
                pass
            topics = (
                Menu.objects.filter(parent_menu=None)
                .filter(home=styles.cmsMenu)
                .filter(active=True)
                .filter(is_section=False)
                .order_by("stack_order")
            )
            sections = (
                Menu.objects.filter(parent_menu=None)
                .filter(home=styles.cmsMenu)
                .filter(active=True)
                .filter(is_section=True)
                .order_by("stack_order")
            )
            second_menu = topics.filter(menu_side='2')
            items_list = list(chain(topics))
    return render(
        request,
        "public_index.html",
        {
            "SiteStyle": styles,
            "topics": topics,
            "items_list": items_list,
            "style": style,
            "header": header,
            "home": home,
            "sections": sections,
            "second_menu": second_menu
        }
    )


def interface_create(request):
    if request.method == "POST":
        form = InterfaceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("home"))
    else:
        form = InterfaceForm()
    return render(
        request,
        "interface_form.html",
        {"form": form, "center": [24, -101], "zoom": 5, "basemap": "osm"},
    )


def config_interface(request, id):
    obj = get_object_or_404(SiteStyle, id=id)
    form = InterfaceForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("../../")

    # Validacion para la primera corrida despues de la implementacion.
    if not obj.vw_center:
        obj.vw_center = [24, -101]
    if not obj.vw_zoom:
        obj.vw_zoom = 5
    if not obj.basemap:
        obj.basemap = "osm"

    return render(
        request,
        "interface_form.html",
        {
            "form": form,
            "obj": obj,
            "center": obj.vw_center,
            "zoom": obj.vw_zoom,
            "basemap": obj.basemap,
        },
    )
