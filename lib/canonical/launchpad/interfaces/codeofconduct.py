
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute, classImplements

from zope.schema import Choice, Datetime, Int, Text, TextLine, Bool
from zope.schema.interfaces import IText, ITextLine

from canonical.launchpad.fields import Summary, Title, TimeInterval
from canonical.launchpad.validators.name import valid_name


class ICodeOfConduct(Interface):
    """Pristine Code of Conduct content."""

    version = Attribute("CoC Release Version")
    title = Attribute("CoC Release Title")
    content = Attribute("CoC File Content")
    current = Attribute("True if the release is the current one")
    
class ISignedCodeOfConduct(Interface):
    """The Signed Code of Conduct."""

    id = Int(title=_('Signed CoC ID'), required=True, readonly=True)

    person = Int(title=_("Owner"), required=True, readonly=False)
    
    signedcode = TextLine(title=_('Signed Code'), required=False,
                          description=_("""GPG Signed Code"""))

    signingkey = Int(title=_("Signing key ID"), required=False,
                     description=_('GPG Key ID.'), readonly=False)

    datecreated = Datetime(title=_('Date Created'), required=True,
                           readonly=True)

    recipient = Int(title=_("Recipient"), required=False, readonly=False)
    
    admincomment = TextLine(title=_('Admin Comment'), required=False,
                    description=_("""Admin comment describing the reasons
                    for Approve or not of this registry."""))

    active = Bool(title=_('Active'), required=False,
                  description=_("""Whether or not this Signed CoC
                  is considered active."""))



# Interfaces for containers
class ICodeOfConductSet(Interface):
    """Pristine Code of Conduct container."""

    def __getitem__(user):
        """Get a Pristine CoC Release."""

    def __iter__():
        """Iterate through the Pristine CoC release in this set."""


class ISignedCodeOfConductSet(Interface):
    """A container for Signed CoC."""

    def __getitem__(user):
        """Get a Signed CoC."""

    def __iter__():
        """Iterate through the Signed CoC in this set."""

class ICodeOfConductConf(Interface):
    """Component to store the CoC Conf."""

    path = Attribute("CoCs FS path")
    prefix = Attribute("CoC Title Prefix")
    current = Attribute("Current CoC release")
