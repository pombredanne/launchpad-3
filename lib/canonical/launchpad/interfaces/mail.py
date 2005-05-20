# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Interfaces specific to mail handling."""

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute
from zope.schema import ASCII

class ISignedMessage(Interface):
    """A message that's possibly signed with a GPG key.
    
    If the message wasn't signed, all attributes will be None.
    """

    def __getitem__(name):
        """Returns the message header with the given name."""
        
    signedMessage = Attribute("The part that was signed, represented"
                              " as an email.Message.")

    signedContent = ASCII(title=_("Signed Content"),
                          description=_("The text that was signed."))

    signature = ASCII(title=_("Signature"),
                      description=_("The GPG signature used to sign"
                                    " the email"))
