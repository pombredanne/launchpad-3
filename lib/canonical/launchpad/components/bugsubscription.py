# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from sets import Set

from sqlobject.sqlbuilder import AND

from zope.interface import implements

from canonical.lp import dbschema
from canonical.launchpad.database import BugSubscription, EmailAddress, \
     SourcePackage
from canonical.launchpad.interfaces import IBugSubscriptionSet

class BugSubscriptionSetAdapter:
    """Adapter a bug into a set of subscriptions to the bug."""

    implements(IBugSubscriptionSet)

    def __init__(self, bug):
        self.bug = bug

    def getCcEmailAddresses(self):
        emails = Set()
        for subscription in self.bug.subscriptions:
            if subscription.subscription == dbschema.BugSubscription.CC:
                best_email = _get_best_email_address(subscription.person)
                if best_email:
                    emails.add(best_email)

        if not self.bug.private:
            # Collect implicit subscriptions. This only happens on
            # public bugs.
            for task in self.bug.bugtasks:
                best_email = _get_best_email_address(task.assignee)
                if best_email:
                    emails.add(best_email)

                if task.product:
                    best_email = _get_best_email_address(task.product.owner)
                else:
                    if task.sourcepackagename:
                        if task.distribution:
                            distribution = task.distribution
                        else:
                            distribution = task.distrorelease.distribution
                        # XXX: Brad Bollenbach, 2005-03-04: I'm not going
                        # to bother implementing an ISourcePackage.get,
                        # because whomever implements the
                        # Nukesourcepackage spec is going to break this
                        # code either way. Once Nukesourcepackage is
                        # implemented, the code below should be replaced
                        # with a proper implementation that uses something
                        # like an IMaintainershipSet.get
                        sourcepackages = SourcePackage.selectBy(
                            sourcepackagenameID = task.sourcepackagename.id,
                            distroID = distribution.id)
                        if sourcepackages.count():
                            best_email = _get_best_email_address(
                                sourcepackages[0].maintainer)
                if best_email:
                    emails.add(best_email)

        best_owner_email = _get_best_email_address(self.bug.owner)
        if best_owner_email:
            emails.add(best_owner_email)
        emails = list(emails)
        emails.sort()
        return emails

    def subscribePerson(self, person):
        """See canonical.launchpad.interfaces.bugsubscription.IBugSubscriptionSet."""
        subscriber_ids = [
            subscription.person.id for subscription in self.bug.subscriptions]
        
        if person.id not in subscriber_ids:
            return BugSubscription(
                bug=self.bug.id,
                person=person.id,
                subscription=dbschema.BugSubscription.CC)

    def unsubscribePerson(self, person):
        """See canonical.launchpad.interfaces.bugsubscription.IBugSubscriptionSet."""
        for subscription in BugSubscription.selectBy(
            bugID=self.bug.id, personID=person.id):
            BugSubscription.delete(subscription)

# XXX, Brad Bollenbach, 2004-12-07: move this into an adapter for IPerson
def _get_best_email_address(person):
    if person:
        # Should never be more than 1, but just in case
        preferred_email_addresses = list(EmailAddress.selectBy(
            personID=person.id,
            status=dbschema.EmailAddressStatus.PREFERRED
            ))
        if len(preferred_email_addresses) > 0:
            return preferred_email_addresses[0].email
        return None

        # valid_email_addresses = list(EmailAddress.selectBy(
        #     personID=person.id,
        #     status=dbschema.EmailAddressStatus.VALIDATED
        #     ))

        # best_email = None
        # if valid_email_addresses:
        #     best_email = valid_email_addresses[0].email

        # return best_email

    return None

