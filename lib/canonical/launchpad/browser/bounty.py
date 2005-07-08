# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BountyView', 'BountySetAddView']

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent

from zope.app.form.browser.add import AddView
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import SequenceWidget, ObjectWidget

import zope.security.interfaces

from canonical.launchpad.interfaces import IBounty, IBountySet, IPerson
from canonical.launchpad.database import Bounty
from canonical.lp.dbschema import BountySubscription

ow = CustomWidgetFactory(ObjectWidget, Bounty)
sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)

class BountySubscriberPortletMixin:

    def getWatches(self):
        return [s for s in self.context.subscriptions
                if s.subscription == BountySubscription.WATCH]

    def getCCs(self):
        return [s for s in self.context.subscriptions
                if s.subscription == BountySubscription.CC]

    def getIgnores(self):
        return [s for s in self.context.subscriptions
                if s.subscription == BountySubscription.IGNORE]




class BountyView(BountySubscriberPortletMixin):

    __used_for__ = IBounty

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.subscription = None
        self.notices = []

        # figure out who the user is for this transaction
        self.user = IPerson(self.request.principal, None)

        # establish if a subscription form was posted
        formsub = request.form.get('Subscribe', None)
        if formsub is not None:
            newsub = request.form.get('subscription', None)
            if newsub == 'watch':
                self.context.subscribe(self.user, BountySubscription.WATCH)
            elif newsub == 'email':
                self.context.subscribe(self.user, BountySubscription.CC)
            elif newsub == 'ignore':
                self.context.subscribe(self.user, BountySubscription.IGNORE)
            elif newsub == 'none':
                self.context.unsubscribe(self.user)
            self.notices.append("Your subscription to this bounty has been "
                "updated.")

        # establish if this user has a subscription to the bounty
        if self.user is not None:
            for subscription in self.context.subscriptions:
                if subscription.person.id == self.user.id:
                    self.subscription = subscription.subscription
                    break

    def subselector(self):
        html = '<select name="subscription">\n'
        html += '<option value="watch"'
        if self.subscription == BountySubscription.WATCH:
            html += ' selected'
        html += '>Watch</option>\n'
        html += '<option value="email"'
        if self.subscription == BountySubscription.CC:
            html += ' selected'
        html += '>Email</option>\n'
        html += '<option value="none"'
        if self.subscription is None:
            html += ' selected'
        html += '>None</option>\n'
        html += '</select>\n'
        return html
        

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
