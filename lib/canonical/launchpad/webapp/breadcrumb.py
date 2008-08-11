# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Classes for creating navigation breadcrumbs."""

__metaclass__ = type

__all__ = [
    'Breadcrumb'
    ]


from zope.interface import implements

from canonical.launchpad.webapp.interfaces import IBreadcrumb


class Breadcrumb:
    implements(IBreadcrumb)

    def __init__(self, url, text):
        self.url = url
        self.text = text

    def __repr__(self):
        return "<%s url='%s' text='%s'>" % (
            self.__class__.__name__, self.url, self.text)


