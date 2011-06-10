# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for creating navigation breadcrumbs."""

__metaclass__ = type

__all__ = [
    'Breadcrumb',
    'DisplaynameBreadcrumb',
    'NameBreadcrumb',
    'TitleBreadcrumb',
    ]


from zope.interface import implements

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import (
    IBreadcrumb,
    ICanonicalUrlData,
    )


class Breadcrumb:
    """See `IBreadcrumb`.

    This class is intended for use as an adapter.
    """
    implements(IBreadcrumb)

    text = None
    _url = None

    def __init__(self, context):
        self.context = context

    @property
    def rootsite(self):
        """The rootsite of this breadcrumb's URL.

        If the `ICanonicalUrlData` for our context defines a rootsite, we
        return that, otherwise we return 'mainsite'.
        """
        url_data = ICanonicalUrlData(self.context)
        if url_data.rootsite:
            return url_data.rootsite
        else:
            return 'mainsite'

    @property
    def url(self):
        if self._url is None:
            return canonical_url(self.context, rootsite=self.rootsite)
        else:
            return self._url

    def __repr__(self):
        # XXX: salgado, 2009-10-14, http://bugs.python.org/issue5876: In
        # python 2.5, the return value of __repr__() may be forced into a
        # type(str), so we can't include unicode here.
        text = self.text.encode('raw-unicode-escape')
        return "<%s url='%s' text='%s'>" % (
            self.__class__.__name__, self.url, text)


class NameBreadcrumb(Breadcrumb):
    """An `IBreadcrumb` that uses the context's name as its text."""

    @property
    def text(self):
        return self.context.name


class DisplaynameBreadcrumb(Breadcrumb):
    """An `IBreadcrumb` that uses the context's displayname as its text."""

    @property
    def text(self):
        return self.context.displayname


class TitleBreadcrumb(Breadcrumb):
    """An `IBreadcrumb` that uses the context's title as its text."""

    @property
    def text(self):
        return self.context.title
