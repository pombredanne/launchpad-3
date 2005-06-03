# Copyright 2004 Canonical Ltd.  All rights reserved.

#
# Code to create a widget that encodes the value of the request context into
# the form.
#

__metaclass__ = type

from zope.interface import implements, Interface
from canonical.widgets.owner import RequestWidget

class IContextWidget(Interface):
    pass


class ContextWidget(RequestWidget):

    implements(IContextWidget)

    def getInputValue(self):
        return self.context.context.id

