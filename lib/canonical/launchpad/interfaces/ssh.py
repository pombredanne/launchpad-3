# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class ISSHKey(Interface):
    """SSH public key"""
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    keytype = TextLine(title=_("Key type"), required=True)
    keytext = TextLine(title=_("Key text"), required=True)
    comment = TextLine(title=_("Comment describing this key"), required=True)
    keykind = Attribute(("The kind of this key, which is either ssh-dss or "
                         "ssh-rsa. This is what we have to show when "
                         "displaying an ssh key, so people can just copy and "
                         "paste it."))
    keytypename = Attribute("The name of the type of this key (DSA/RSA).")

    def destroySelf():
        """Remove this SSHKey from the database."""


class ISSHKeySet(Interface):
    """The set of SSHKeys."""

    def new(personID, keytype, keytext, comment):
        """Create a new SSHKey pointing to the given Person."""

    def get(id, default=None):
        """Return the SSHKey object for the given id.

        Return the given default if there's now object with the given id.
        """

