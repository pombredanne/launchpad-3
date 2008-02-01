# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad email addresses."""

__metaclass__ = type
__all__ = [
    'EmailAddressEntry',
    'EmailAddressCollection',
    'IEmailAddressEntry',
    ]

from zope.component import adapts, getUtility
from zope.schema import Object, TextLine

from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest import Collection, Entry
from canonical.launchpad.interfaces import IEmailAddress, IPerson
from canonical.lp import decorates


class IEmailAddressEntry(IEntry):
    """The part of an email address that we expose through the web service."""

    email = TextLine(title=_(u'Email Address'), required=True, readonly=False)
    owner = Object(schema=IPerson)


class EmailAddressEntry(Entry):
    """An email address."""

    adapts(IEmailAddress)
    decorates(IEmailAddressEntry)
    schema = IEmailAddressEntry

    parent_collection_name = 'emailaddresses'

    def fragment(self):
        """See `IEntry`."""
        return self.context.email

    @property
    def owner(self):
        """See `IEmailAddressEntry`."""
        return self.context.person


class EmailAddressCollection(Collection):
    """A collection of email addresses."""

    def lookupEntry(self, email):
        """Find an EmailAddress by email."""
        return self.context.getByEmail(email)

    def find(self):
        """Return all the email addresses on the site."""
        return None

