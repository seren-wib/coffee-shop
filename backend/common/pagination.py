"""Page size 20, fixed (SDD 7.4, FR-1)."""

from urllib.parse import urlsplit, urlunsplit

from rest_framework.pagination import PageNumberPagination


def _path_only(url):
    # Links carry no scheme or host, so internal addresses behind the proxy never leak.
    if url is None:
        return None
    parts = urlsplit(url)
    return urlunsplit(("", "", parts.path, parts.query, ""))


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = None
    max_page_size = 20

    def get_next_link(self):
        return _path_only(super().get_next_link())

    def get_previous_link(self):
        return _path_only(super().get_previous_link())
