
from canonical.launchpad.database import Bounty

from canonical.launchpad.interfaces import IBountySet, IPerson

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent

from zope.app.form.browser.add import AddView
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import SequenceWidget, ObjectWidget

import zope.security.interfaces

ow = CustomWidgetFactory(ObjectWidget, Bounty)
sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)

__all__ = ['BountySetAddView']

class BountySetAddView(AddView):

    __used_for__ = IBountySet

    options_widget = sw
    
    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the bounty
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized, "Need an authenticated bounty owner"
        kw = {}
        for item in data.items():
            kw[str(item[0])] = item[1]
        kw['ownerID'] = owner.id
        # XXX Mark Shuttleworth need the fancy-person selector to select a
        # reviewer
        kw['reviewerID'] = owner.id
        bounty = Bounty(**kw)
        notify(ObjectCreatedEvent(bounty))
        self._nextURL = kw['name']
        return bounty

    def nextURL(self):
        return self._nextURL
