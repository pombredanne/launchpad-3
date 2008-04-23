# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser views for handling mailing lists."""

__metaclass__ = type
__all__ = [
    'HeldMessageView',
    'MailingListsReviewView',
    ]


from cgi import escape
from email import message_from_string
from email.Header import decode_header, make_header
from itertools import repeat
from textwrap import TextWrapper
from urllib import quote

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
        self.widget_name = 'field.' + quote(self.message_id)
        self.message = naked_message
        self.subject = self.message.subject
        self.date = self.message.datecreated
        self.message.raw.open()
        try:
            self.message_object = message_from_string(self.message.raw.read())
        finally:
            self.message.raw.close()
        self._process_text()

    def _process_text(self):
        """Sanitize the message text and split it into summary and details.
        """
        # Try to find a reasonable way to split the text of the message for
        # presentation as both a summary and a revealed detail.  This is
        # fraught with potential ugliness, so let's just do an 80% solution
        # that's safe and easy.  First, we escape the text so that there's no
        # chance of cross-site scripting, then split into lines.
        text_lines = escape(self.message.text_contents).splitlines()
        # Strip off any leadning whitespace-only lines.
        text_lines.reverse()
        while len(text_lines) > 0:
            first_line = text_lines.pop()
            if len(first_line.strip()) > 0:
                text_lines.append(first_line)
                break
        text_lines.reverse()
        # If there are no non-blank lines, then we're done.
        if len(text_lines) == 0:
            summary = u''
            details = u''
        # If the first line is of a completely arbitrarily chosen reasonable
        # length, then we'll just use that as the summary.
        elif len(text_lines[0]) < 60:
            summary = text_lines[0]
            details = u'\n'.join(text_lines[1:])
        # It could be the case that the text is actually flowed using RFC
        # 3676 format="flowed" parameters.  In that case, just split the line
        # at the first whitespace after, again, our arbitrarily chosen limit.
        else:
            first_line = text_lines.pop(0)
            wrapper = TextWrapper(width=60)
            filled_lines = wrapper.fill(first_line).splitlines()
            summary = filled_lines[0]
            text_lines.insert(0, u''.join(filled_lines[1:]))
            details = u'\n'.join(text_lines)
        # Now, ideally we'd like to wrap this all in <pre> tags so as to
        # preserve things like newlines in the original message body, but this
        # doesn't work very well with the JavaScript folding ellipsis
        # control.  The next best, and easiest thing, is simply to replace all
        # empty blank lines in the details text with a <p> tag to give some
        # separation in the paragraphs.  No more than 20 lines in total
        # though, and here we don't worry about format="flowed".
        #
        # Again, 80% is good enough.
        paragraphs = []
        current_paragraph = []
        for lineno, line in enumerate(details.splitlines()):
            if lineno > 20:
                break
            if len(line.strip()) == 0:
                paragraphs.append(u'\n'.join(current_paragraph))
                paragraphs.append('\n<p>\n')
                current_paragraph = []
            else:
                current_paragraph.append(line)
        paragraphs.append(u''.join(current_paragraph))
        self.body_summary = summary
        self.body_details = u''.join(paragraphs)

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
