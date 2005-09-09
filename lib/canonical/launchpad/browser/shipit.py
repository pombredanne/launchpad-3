# Copyright 2005 Canonical Ltd

__metaclass__ = type

__all__ = ['StandardShipItRequestAddView', 'ShippingRequestAdminView',
           'ShippingRequestsView']

from zope.event import notify
from zope.component import getUtility
from zope.app.form.browser.add import AddView
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.helpers import intOrZero
from canonical.launchpad.interfaces import (
    IStandardShipItRequestSet, IShippingRequestSet, ILaunchBag,
    ShippingRequestStatus)


class ShippingRequestsView:
    """The view to list ShippingRequests that match a given criteria."""

    submitted = False
    results = None
    selectedStatus = 'unapproved'
    selectedType = 'custom'

    def standardShipItRequests(self):
        """Return a list with all standard ShipIt Requests."""
        return getUtility(IStandardShipItRequestSet).getAll()

    def processForm(self):
        """Process the form, if it was submitted."""
        if self.request.method != 'POST':
            return

        self.submitted = True
        form = self.request.form
        status = form.get('statusfilter')
        self.selectedStatus = status
        if status == 'unapproved':
            status = ShippingRequestStatus.UNAPPROVED
        elif status == 'approved':
            status = ShippingRequestStatus.APPROVED
        else:
            status = ShippingRequestStatus.ALL

        requestset = getUtility(IShippingRequestSet)
        type = form.get('typefilter')
        self.selectedType = type
        if type == 'custom':
            results = requestset.searchCustomRequests(status=status)
        elif type == 'standard':
            results = requestset.searchStandardRequests(status=status)
        else:
            # Must cast self.selectedType to an int so we can compare with the
            # value of standardrequest.id in the template to see if it must be
            # the selected option or not.
            self.selectedType = int(self.selectedType)
            type = getUtility(IStandardShipItRequestSet).get(type)
            results = requestset.searchStandardRequests(
                status=status, standard_type=type)

        self.results = results


class StandardShipItRequestAddView(AddView):
    """The view to add a new Standard ShipIt Request."""

    def nextURL(self):
        return '.'

    def createAndAdd(self, data):
        quantityx86 = data.get('quantityx86')
        quantityamd64 = data.get('quantityamd64')
        quantityppc = data.get('quantityppc')
        description = data.get('description')
        isdefault = data.get('isdefault')
        request = getUtility(IStandardShipItRequestSet).new(
            quantityx86, quantityamd64, quantityppc, description, isdefault)
        notify(ObjectCreatedEvent(request))


class ShippingRequestAdminView:
    """The view for ShipIt admins to approve/reject requests."""

    def processForm(self):
        user = getUtility(ILaunchBag).user
        context = self.context
        form = self.request.form
        request = self.request
        if 'CANCEL' in request:
            if not context.cancelled:
                context.cancel(user)
            else:
                # XXX: Must give some kind of warning in this case.
                # GuilhermeSalgado - 2005-09-02
                pass
        elif 'REACTIVATE' in request:
            if context.cancelled:
                context.reactivate()
            else:
                # XXX: Must give some kind of warning in this case.
                # GuilhermeSalgado - 2005-09-02
                pass
        elif 'CHANGE' in request:
            if not context.approved:
                # XXX: Must give some kind of warning in this case.
                # GuilhermeSalgado - 2005-09-02
                return
            context.quantityx86approved = intOrZero(form.get('quantityx86'))
            context.quantityamd64approved = intOrZero(form.get('quantityamd64'))
            context.quantityppcapproved = intOrZero(form.get('quantityppc'))

            if context.quantityx86approved < 0:
                context.quantityx86approved = 0
            if context.quantityppcapproved < 0:
                context.quantityppcapproved = 0
            if context.quantityamd64approved < 0:
                context.quantityamd64approved = 0
        elif 'APPROVE' in request:
            if context.approved:
                context.approve(user)
            else:
                # XXX: Must give some kind of warning in this case.
                # GuilhermeSalgado - 2005-09-02
                pass
        else:
            # User tried to poison the form. Let's simply ignore
            pass

        flush_database_updates()

