# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser views for handling mailing lists."""

__metaclass__ = type
__all__ = [
    'HeldMessageView',
    'MailingListsReviewView',
    ]


from email import message_from_string
from email.Header import decode_header, make_header
from itertools import repeat

from zope.component import getUtility
from zope.interface import Attribute, Interface

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IMessageSet, MailingListStatus, NotFoundError)
from canonical.launchpad.webapp import (
    LaunchpadFormView, action, canonical_url)
from canonical.launchpad.webapp.interfaces import UnexpectedFormData
from canonical.launchpad.webapp.menu import structured


class ReviewForm(Interface):
    """An empty marker schema for the review form."""


class MailingListsReviewView(LaunchpadFormView):
    """Present review page for mailing list creation requests."""

    schema = ReviewForm

    @cachedproperty
    def registered_lists(self):
        """Return a concrete list of mailing lists pending approval.

        The context's property of the same name returns a query, which for
        purposes of rendering in the view needs to be turned into a concrete,
        sorted list object.

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
                'field.%s' % mailing_list.team.name)
            # This essentially acts like a switch statement or if/elifs.  It
            # looks the action up in a map of allowed actions, watching out
            # for bogus input.
            try:
                status = dict(
                    approve=MailingListStatus.APPROVED,
                    decline=MailingListStatus.DECLINED,
                    hold=None,
                    )[action]
            except KeyError:
                raise UnexpectedFormData(
                    'Invalid review action for mailing list %s: %s' %
                    (mailing_list.team.displayname, action))
            if status is not None:
                mailing_list.review(self.user, status)
                self.request.response.addInfoNotification(
                    structured(
                        '<a href="%s">%s</a> mailing list was %s',
                            canonical_url(mailing_list.team),
                            mailing_list.team.displayname,
                            status.title.lower()))
        # Redirect to prevent double posts (and not require
        # flush_database_updates() :)
        self.next_url = canonical_url(self.context)


class IHeldMessageView(Interface):
    """A simple view schema for held messages."""

    message_id = Attribute('The Message-ID header')
    subject = Attribute("The Subject header")
    author = Attribute('The message originator (i.e. author)')
    date = Attribute("The Date header.")
    body_summary = Attribute('A summary of the message.')
    body_details = Attribute('The message details.')


class HeldMessageView:
    """A little helper view for for held messages."""

    schema = IHeldMessageView

    def __init__(self, context, request):
        self.context = context
        self.request = request
        messages = getUtility(IMessageSet).get(self.context.message_id)
        assert len(messages) == 1, (
            'Too many messages with Message-ID: %s' %
            self.context.message_id)
        from zope.security.proxy import removeSecurityProxy
        naked_message = removeSecurityProxy(messages[0])
        self.message_id = self.context.message_id
        self.message = naked_message
        self.subject = self.message.subject
        self.date = self.message.datecreated
        self.message.raw.open()
        try:
            self.message_object = message_from_string(self.message.raw.read())
        finally:
            self.message.raw.close()

    @property
    def author(self):
        """Return the sender, but as a link to their person page."""
        originators = self.message_object.get_all('from', [])
        originators.extend(self.message_object.get_all('reply-to', []))
        if len(originators) == 0:
            return 'n/a'
        unicode_parts = []
        for bytes, charset in decode_header(originators[0]):
            if charset is None:
                charset = 'us-ascii'
            unicode_parts.append(
                bytes.decode(charset, 'replace').encode('utf-8'))
        header = make_header(zip(unicode_parts, repeat('utf-8')))
        return '<a href="%s">%s</a>' % (
            canonical_url(self.message.owner), header)

    @property
    def body_summary(self):
        """Return the first line of the message's plain text body."""
        return self.message.text_contents.splitlines()[0]

    @property
    def body_details(self):
        """Return more lines of the message's plain text body."""
        return u'\n'.join(self.message.text_contents.splitlines()[1:20])
