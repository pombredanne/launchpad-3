""" Interfaces for CodeOfConduct (CoC) and related classes.
    
    https://wiki.launchpad.canonical.com/CodeOfConduct
    
    Copyright 2004 Canonical Ltd.  All rights reserved.
"""

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, Text, TextLine, Bool


class ICodeOfConduct(Interface):
    """Pristine Code of Conduct content."""

    version = Attribute("CoC Release Version")
    title = Attribute("CoC Release Title")
    content = Attribute("CoC File Content")
    current = Attribute("True if the release is the current one")
    

class ISignedCodeOfConduct(Interface):
    """The Signed Code of Conduct."""

    id = Int(title=_("Signed CoC ID"), required=True, readonly=True)

    person = Int(title=_("Owner"), required=True, readonly=False)
    
    signedcode = TextLine(title=_("Signed Code"), 
                          description=_("GPG Signed Code"),
                          required=False)

    signingkey = Int(title=_("Signing key ID"), 
                     description=_("GPG Key ID."),
                     required=False,
                     readonly=False)

    datecreated = Datetime(title=_("Date Created"),
                           required=True,
                           readonly=True)

    recipient = Int(title=_("Recipient"), required=False, readonly=False)
    
    admincomment = Text(
        title=_("Admin Comment"), 
        description=_("Admin comment, to e.g. describe the reasons why "
                      "this registration was approved or rejected."),
        required=False)

    active = Bool(title=_("Active"), 
                  description=_("Whether or not this Signed CoC"
                                "is considered active."),
                  required=False)


# Interfaces for containers
class ICodeOfConductSet(Interface):
    """Unsigned (original) Codes of Conduct container."""

    def __getitem__(version):
        """Get a original CoC Release by its version."""

    def __iter__():
        """Iterate through the original CoC releases in this set."""


class ISignedCodeOfConductSet(Interface):
    """A container for Signed CoC."""

    def __getitem__(user):
        """Get a Signed CoC."""

    def __iter__():
        """Iterate through the Signed CoC in this set."""


class ICodeOfConductConf(Interface):
    """Component to store the CoC Configuration."""

    path = Attribute("CoCs FS path")
    prefix = Attribute("CoC Title Prefix")
    current = Attribute("Current CoC release")
