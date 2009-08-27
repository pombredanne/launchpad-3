# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The watermark TALES path adapter."""

__metaclass__ = type
__all__ = [
    'WatermarkTalesAdapter',
    ]


import cgi

from zope.component import queryAdapter
from zope.interface import implements
from zope.traversing.interfaces import (
    IPathAdapter, ITraversable, TraversalError)

from canonical.lazr.canonicalurl import nearest_provides_or_adapted

from lp.app.interfaces.rootcontext import IRootContext


class WatermarkTalesAdapter:
    """Adapter for any object to get the watermark heading and image."""

    implements(ITraversable)

    def __init__(self, context):
        self._context = context

    @property
    def root_context(self):
        return nearest_provides_or_adapted(self._context, IRootContext)

    def heading(self):
        """Return the heading text for the root context.

        If the context itself provides IRootContext then we return an H1,
        otherwise it is a H2.
        """
        if IRootContext.providedBy(self._context):
            heading = 'h1'
        else:
            heading = 'h2'

        root = self.root_context
        if root is None:
            title = 'Launchpad.net'
        else:
            title = root.title

        return "<%(heading)s>%(title)s</%(heading)s>" % {
            'heading': heading,
            'title': cgi.escape(title)
            }

    def logo(self):
        """Return the logo image for the root context."""
        adapter = queryAdapter(self.root_context, IPathAdapter, 'image')
        return adapter.logo()

    def traverse(self, name, furtherPath):
        if name == "heading":
            return self.heading()
        elif name == "logo":
            return self.logo()
        else:
            raise TraversalError, name
