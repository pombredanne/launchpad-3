# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from sets import Set

from sqlobject.sqlbuilder import AND

from zope.interface import implements

from canonical.lp.dbschema import BugSubscription, EmailAddressStatus
from canonical.launchpad.database import EmailAddress
from canonical.launchpad.interfaces import IBugSubscriptionSet

class IBugSubscriptionSetAdapter:
    """Adapter a bug into a set of subscriptions to the bug."""

    implements(IBugSubscriptionSet)

    def __init__(self, bug):
        self.bug = bug

    def getCcEmailAddresses(self):
        emails = Set()
        for subscription in self.bug.subscriptions:
            if BugSubscription.items[subscription.subscription].value == BugSubscription.CC.value:
                best_email = _get_best_email_address(subscription.person)
                if best_email:
                    emails.add(best_email)

        for prod_ass in self.bug.productassignments:
            best_email = _get_best_email_address(prod_ass.assignee)
            if best_email:
                emails.add(best_email)
            best_email = _get_best_email_address(prod_ass.product.owner)
            if best_email:
                emails.add(best_email)

        for pack_ass in self.bug.packageassignments:
            best_email = _get_best_email_address(pack_ass.assignee)
            if best_email:
                emails.add(best_email)
            best_email = _get_best_email_address(pack_ass.sourcepackage.maintainer)
            if best_email:
                emails.add(best_email)

        emails = list(emails)
        emails.sort()
        return emails

# XXX, Brad Bollenbach, 2004-12-07: move this into an adapter for IPerson
def _get_best_email_address(person):
    if person:
        valid_email_addresses = EmailAddress.select(AND(
            EmailAddress.q.personID == person.id,
            EmailAddress.q.status == EmailAddressStatus.VALIDATED.value))
        new_email_addresses = EmailAddress.select(AND(
            EmailAddress.q.personID == person.id,
            EmailAddress.q.status == EmailAddressStatus.NEW.value))
        best_email = None

        if valid_email_addresses:
            best_email = valid_email_addresses[0].email
        elif new_email_addresses:
            best_email = new_email_addresses[0].email

        return best_email
