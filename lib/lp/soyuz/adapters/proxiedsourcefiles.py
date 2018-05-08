# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Proxied source files."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ProxiedSourceLibraryFileAlias',
    ]

from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.client import url_path_quote
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.url import urlappend


class ProxiedSourceLibraryFileAlias(ProxiedLibraryFileAlias):
    """A `ProxiedLibraryFileAlias` variant that traverses via +sourcefiles.

    This can be used to construct unambiguous source file URLs even for
    imports from upstream archives without robust historical filename
    uniqueness checks.
    """

    @property
    def http_url(self):
        if self.context.deleted:
            return None

        url = canonical_url(self.parent.archive, request=self.request)
        return urlappend(url, '/'.join([
            '+sourcefiles', self.parent.source_package_name,
            self.parent.source_package_version,
            url_path_quote(self.context.filename.encode('utf-8'))]))
