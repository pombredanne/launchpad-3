# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['MailingListsReviewView']

from zope.interface import Interface

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.webapp import (
    LaunchpadFormView, action, canonical_url)
from canonical.launchpad.interfaces import MailingListStatus


class ReviewSchema(Interface):
    """An empty marker schema for the review form."""


class MailingListsReviewView(LaunchpadFormView):
    """Present review page for mailing list creation requests."""

    schema = ReviewSchema

    @cachedproperty
    def registered_lists(self):
        """Return a concrete list of mailing lists pending approval.

        The context's property of the same name returns a query, which for
        purposes of rendering in the view needs to be turned into a concrete
        list object.

        :return: list of IMailingList objects pending review.
        """
        # Use a lambda here for succinctness.  Sure, we could have defined a
        # nested function that did the same thing.  Won't it be nice when in
        # Python 2.6, operator.attrgetter() will chase chained property
        # references?
        return sorted(self.context.registered_lists,
                      key=lambda mlist: mlist.team.name)

    @action(_('Submit'), name='submit')
    def submit_action(self, action, data):
        """Process the mailing list review form."""
        for mailing_list in self.registered_lists:
            # Find out which disposition the administrator chose for this
            # mailing list.  If there is no data in the form for this mailing
            # list, just treat it as having been deferred.
            action = self.request.form_ng.getOne(
                'action_%s' % mailing_list.team.name)
            status = None
            if action == 'approve':
                status = MailingListStatus.APPROVED
            elif action == 'decline':
                status = MailingListStatus.DECLINED
            elif action == 'hold':
                # There's nothing to do.
                pass
            else:
                raise AssertionError('Invalid review action: %s' % action)
            if status is not None:
                mailing_list.review(self.user, status)
                self.request.response.addInfoNotification(
                    '%s mailing list was %s' % (
                        mailing_list.team.displayname, status.title.lower()))
        # Redirect to prevent double posts (and not require
        # flush_database_updates() :)
        self.next_url = canonical_url(self.context)
