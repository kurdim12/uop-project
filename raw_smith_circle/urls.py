"""
Root URL configuration for Raw Smith Circle.

Routes:
- /            -> circle app (pages)
- /api/        -> circle REST API
- /admin/      -> Django admin
- /sitemap.xml -> sitemap framework (bonus)
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from circle.sitemaps import StaticViewSitemap

sitemaps = {"static": StaticViewSitemap()}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("circle.api_urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("circle.urls")),
]

# Custom branded error handlers (resolved from circle/templates/).
handler404 = "circle.views.error_404"
handler500 = "circle.views.error_500"
