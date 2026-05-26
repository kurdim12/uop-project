"""Sitemap definitions (bonus: served at /sitemap.xml)."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Sitemap for the public, crawlable pages of the site."""

    priority = 0.6
    changefreq = "weekly"
    protocol = "https"

    def items(self) -> list[str]:
        """Return the URL names included in the sitemap."""
        return ["home", "dashboard", "predict_tier", "predict_volume", "about"]

    def location(self, item: str) -> str:
        """Resolve a URL name to its path."""
        return reverse(f"circle:{item}")
