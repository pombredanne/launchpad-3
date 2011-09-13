# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handle incoming Blueprints email."""

__metaclass__ = type
__all__ = [
    "BlueprintHandler",
    ]

import re
from urlparse import urlunparse

from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.webapp import urlparse
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.services.mail.helpers import get_main_body
from lp.services.mail.interfaces import IMailHandler
from lp.services.mail.sendmail import sendmail


MOIN_URL_RE = re.compile(r'(https?://[^ \r\n]+)')


def get_spec_url_from_moin_mail(moin_text):
    """Extract a specification URL from Moin change notification."""
    if not isinstance(moin_text, basestring):
        return None
    match = MOIN_URL_RE.search(moin_text)
    if match:
        return match.group(1)
    else:
        return None


class BlueprintHandler:
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

    def get_spec_url_from_email(self, signed_msg):
        """Return the first url found in the email body."""
        mail_body = get_main_body(signed_msg)
        return get_spec_url_from_moin_mail(mail_body)

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

        spec_url = self.get_spec_url_from_email(signed_msg)
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
