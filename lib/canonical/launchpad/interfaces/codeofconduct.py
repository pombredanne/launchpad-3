""" Interfaces for CodeOfConduct (CoC) and related classes.
    
    https://wiki.launchpad.canonical.com/CodeOfConduct
    
    Copyright 2004 Canonical Ltd.  All rights reserved.
"""

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, Text, TextLine, Bool, Choice


class ICodeOfConduct(Interface):
    """Pristine Code of Conduct content."""

    version = Attribute("CoC Release Version")
    title = Attribute("CoC Release Title")
    content = Attribute("CoC File Content")
    current = Attribute("True if the release is the current one")
    

class ISignedCodeOfConduct(Interface):
    """The Signed Code of Conduct."""

    id = Int(title=_("Signed CoC ID"),
             required=True,
             readonly=True
             )

    person = Choice(title=_('Owner'), required=True, vocabulary='ValidPerson',
                    description=_("""Signature owner, it must be a valid
                    Person inside Launchpad context."""))
    
    signedcode = Text(title=_("Signed Code"), 
                      description=_("GPG Signed Code of Conduct.")
                      )

    signingkey = Choice(title=_('Signing GPG Key'), 
                        description=_("""GPG key ID used to sign the document,
                        it must be a valid inside Launchpad context."""),
                        vocabulary='ValidGPGKey',
                        required=True
                        )
    
    datecreated = Datetime(title=_("Date Created"),
                           description=_("Original Request Timestamp")
                           )
    
    recipient = Int(title=_("Recipient"),
                    description=_("Person Authorizing.")
                    )
    
    admincomment = Text(
        title=_("Admin Comment"), 
        description=_("Admin comment, to e.g. describe the reasons why "
                      "this registration was approved or rejected.")
        )

    active = Bool(title=_("Active"), 
                  description=_("Whether or not this Signed CoC"
                                "is considered active.")
                  )


    displayname = Attribute("Fancy Title for CoC.")

    # title is required for the Launchpad Page Layout main template
    title = Attribute("Page title")


# Interfaces for containers
class ICodeOfConductSet(Interface):
    """Unsigned (original) Codes of Conduct container."""

    # title is required for the Launchpad Page Layout main template
    title = Attribute("Page title")

    def __getitem__(version):
        """Get a original CoC Release by its version."""

    def __iter__():
        """Iterate through the original CoC releases in this set."""


class ISignedCodeOfConductSet(Interface):
    """A container for Signed CoC."""

    # title is required for the Launchpad Page Layout main template
    title = Attribute("Page title")

    def __getitem__(id):
        """Get a Signed CoC by id."""

    def __iter__():
        """Iterate through the Signed CoC in this set."""

    def verifyAndStore(person, signingkey, signedcode):
        """Verify and Store a Signed CoC."""

    def searchByDisplayname(displayname, searchfor=None):
        """Search SignedCoC by Owner.displayname"""

    def searchByUser(user_id):
        """Search SignedCoC by Owner.id"""

    def deactivateSignature(sign_id):
        """Deactivate a Signed CoC."""

    def acknowledgeSignature(person, recipient):
        """Acknowledge a paper submitted Signed CoC."""

    def verifySignature(person, signingkey, signedcode):
        """Verify a proposed Signed CoC and return True if some
        error was found.
        """


class ICodeOfConductConf(Interface):
    """Component to store the CoC Configuration."""

    path = Attribute("CoCs FS path")
    prefix = Attribute("CoC Title Prefix")
    current = Attribute("Current CoC release")
