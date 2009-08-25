# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for creating navigation breadcrumbs."""

__metaclass__ = type

__all__ = [
    'Breadcrumb',
    ]


from zope.traversing.interfaces import IPathAdapter
from zope.component import queryAdapter
from zope.interface import implements

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import IBreadcrumb


class Breadcrumb:
    """See `IBreadcrumb`.

    This class is intended for use as an adapter.
    """
    implements(IBreadcrumb)

    rootsite = 'mainsite'
    text = None

    def __init__(self, context):
        self.context = context

    @property
    def url(self):
        return canonical_url(self.context, rootsite=self.rootsite)

    @property
    def icon(self):
        """See `IBreadcrumb`."""
        # Get the <img> tag from the path adapter.
        return queryAdapter(
            self.context, IPathAdapter, name='image').icon()

    def __repr__(self):
        if self.icon is not None:
            icon_repr = " icon='%s'" % self.icon
        else:
            icon_repr = ""

        return "<%s url='%s' text='%s'%s>" % (
            self.__class__.__name__, self.url, self.text, icon_repr)
