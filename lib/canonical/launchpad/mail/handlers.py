# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import re
from urlparse import urlunparse

from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces.mail import IMailHandler
from canonical.launchpad.interfaces.message import IMessageSet
from canonical.launchpad.mail.specexploder import get_spec_url_from_moin_mail
from canonical.launchpad.webapp import urlparse
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.answers.interfaces.questioncollection import IQuestionSet
from lp.answers.interfaces.questionenums import QuestionStatus
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.bugs.mail.handler import MaloneHandler
from lp.code.mail.codehandler import CodeHandler
from lp.services.mail.sendmail import sendmail


class AnswerTrackerHandler:
    """Handles emails sent to the Answer Tracker."""

    implements(IMailHandler)

    allow_unknown_users = False

    # XXX flacoste 2007-04-23: The 'ticket' part is there for backward
    # compatibility with the old notification address. We probably want to
    # remove it in the future.
    _question_address = re.compile(r'^(ticket|question)(?P<id>\d+)@.*')

    def process(self, signed_msg, to_addr, filealias=None, log=None):
        """See IMailHandler."""
        match = self._question_address.match(to_addr)
        if not match:
            return False

        question_id = int(match.group('id'))
        question = getUtility(IQuestionSet).get(question_id)
        if question is None:
            # No such question, don't process the email.
            return False

        messageset = getUtility(IMessageSet)
        message = messageset.fromEmail(
            signed_msg.parsed_string,
            owner=getUtility(ILaunchBag).user,
            filealias=filealias,
            parsed_message=signed_msg)

        if message.owner == question.owner:
            self.processOwnerMessage(question, message)
        else:
            self.processUserMessage(question, message)
        return True

    def processOwnerMessage(self, question, message):
        """Choose the right workflow action for a message coming from
        the question owner.

        When the question status is OPEN or NEEDINFO,
        the message is a GIVEINFO action; when the status is ANSWERED
        or EXPIRED, we interpret the message as a reopenening request;
        otherwise it's a comment.
        """
        if question.status in [
            QuestionStatus.OPEN, QuestionStatus.NEEDSINFO]:
            question.giveInfo(message)
        elif question.status in [
            QuestionStatus.ANSWERED, QuestionStatus.EXPIRED]:
            question.reopen(message)
        else:
            question.addComment(message.owner, message)

    def processUserMessage(self, question, message):
        """Choose the right workflow action for a message coming from a user
        that is not the question owner.

        When the question status is OPEN, NEEDSINFO, or ANSWERED, we interpret
        the message as containing an answer. (If it was really a request for
        more information, the owner will still be able to answer it while
        reopening the request.)

        In the other status, the message is a comment without status change.
        """
        if question.status in [
            QuestionStatus.OPEN, QuestionStatus.NEEDSINFO,
        QuestionStatus.ANSWERED]:
            question.giveAnswer(message.owner, message)
        else:
            # In the other states, only a comment can be added.
            question.addComment(message.owner, message)


class SpecificationHandler:
    """Handles emails sent to specs.launchpad.net."""

    implements(IMailHandler)

    allow_unknown_users = True

    _spec_changes_address = re.compile(r'^notifications@.*')

    # The list of hosts where the Ubuntu wiki is located. We could do a
    # more general solution, but this kind of setup is unusual, and it
    # will be mainly the Ubuntu and Launchpad wikis that will use this
    # notification forwarder.
    UBUNTU_WIKI_HOSTS = [
        'wiki.ubuntu.com', 'wiki.edubuntu.org', 'wiki.kubuntu.org']

    def _getSpecByURL(self, url):
        """Returns a spec that is associated with the URL.

        It takes into account that the same Ubuntu wiki is on three
        different hosts.
        """
        scheme, host, path, params, query, fragment = urlparse(url)
        if host in self.UBUNTU_WIKI_HOSTS:
            for ubuntu_wiki_host in self.UBUNTU_WIKI_HOSTS:
                possible_url = urlunparse(
                    (scheme, ubuntu_wiki_host, path, params, query,
                     fragment))
                spec = getUtility(ISpecificationSet).getByURL(possible_url)
                if spec is not None:
                    return spec
        else:
            return getUtility(ISpecificationSet).getByURL(url)

    def process(self, signed_msg, to_addr, filealias=None, log=None):
        """See IMailHandler."""
        match = self._spec_changes_address.match(to_addr)
        if not match:
            # We handle only spec-changes at the moment.
            return False
        our_address = "notifications@%s" % config.launchpad.specs_domain
        # Check for emails that we sent.
        xloop = signed_msg['X-Loop']
        if xloop and our_address in signed_msg.get_all('X-Loop'):
            if log and filealias:
                log.warning(
                    'Got back a notification we sent: %s' %
                    filealias.http_url)
            return True
        # Check for emails that Launchpad sent us.
        if signed_msg['Sender'] == config.canonical.bounce_address:
            if log and filealias:
                log.warning('We received an email from Launchpad: %s'
                            % filealias.http_url)
            return True
        # When sending the email, the sender will be set so that it's
        # clear that we're the one sending the email, not the original
        # sender.
        del signed_msg['Sender']

        mail_body = signed_msg.get_payload(decode=True)
        spec_url = get_spec_url_from_moin_mail(mail_body)
        if spec_url is not None:
            if log is not None:
                log.debug('Found a spec URL: %s' % spec_url)
            spec = self._getSpecByURL(spec_url)
            if spec is not None:
                if log is not None:
                    log.debug('Found a corresponding spec: %s' % spec.name)
                # Add an X-Loop header, in order to prevent mail loop.
                signed_msg.add_header('X-Loop', our_address)
                notification_addresses = spec.notificationRecipientAddresses()
                if log is not None:
                    log.debug(
                        'Sending notification to: %s' %
                            ', '.join(notification_addresses))
                sendmail(signed_msg, to_addrs=notification_addresses)

            elif log is not None:
                log.debug(
                    "Didn't find a corresponding spec for %s" % spec_url)
        elif log is not None:
            log.debug("Didn't find a specification URL")
        return True


class MailHandlers:
    """All the registered mail handlers."""

    def __init__(self):
        self._handlers = {
            config.launchpad.bugs_domain: MaloneHandler(),
            config.launchpad.specs_domain: SpecificationHandler(),
            config.answertracker.email_domain: AnswerTrackerHandler(),
            # XXX flacoste 2007-04-23 Backward compatibility for old domain.
            # We probably want to remove it in the future.
            'support.launchpad.net': AnswerTrackerHandler(),
            config.launchpad.code_domain: CodeHandler(),
            }

    def get(self, domain):
        """Return the handler for the given email domain.

        Return None if no such handler exists.

            >>> handlers = MailHandlers()
            >>> handlers.get('bugs.launchpad.net') #doctest: +ELLIPSIS
            <...MaloneHandler...>
            >>> handlers.get('no.such.domain') is None
            True
        """
        return self._handlers.get(domain)

    def add(self, domain, handler):
        """Adds a handler for a domain.

            >>> handlers = MailHandlers()
            >>> handlers.get('some.domain') is None
            True
            >>> handler = object()
            >>> handlers.add('some.domain', handler)
            >>> handlers.get('some.domain') is handler
            True

        If there already is a handler for the domain, the old one will
        get overwritten:

            >>> new_handler = object()
            >>> handlers.add('some.domain', new_handler)
            >>> handlers.get('some.domain') is new_handler
            True
        """
        self._handlers[domain] = handler


mail_handlers = MailHandlers()
