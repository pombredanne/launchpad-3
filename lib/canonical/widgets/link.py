# Copyright 2004 Canonical Ltd.  All rights reserved.

#
# Code to create a widget that encodes the value of the request context into
# the form.
#

__metaclass__ = type

from zope.interface import implements, Interface
from canonical.widgets.owner import RequestWidget
from zope.component import getUtility, queryAdapter
from zope.app.traversing.interfaces import IPathAdapter

class ILinkWidget(Interface):
    """testing testing one two three."""

from zope.app.form.browser import DisplayWidget

class LinkWidget(DisplayWidget):

    implements(ILinkWidget)

    def __init__(self, context, request, ignored):
        super(DisplayWidget, self).__init__(context, request)
        self.required = False

    def __call__(self):
        adapter = queryAdapter(b, IPathAdapter, 'fmt')
        return adapter.link('')
