
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.fields import Title, Summary, Description

__all__ = [
    'IMaintainership',
    'IMaintainershipSet'
    ]

class IMaintainership(Interface):
    """
    Maintainership is responsibility for a particular source package
    (identified by name) in a distribution.
    """
    
    distribution = Choice(title=_('Distribution'), required=False,
                     vocabulary='Distribution', 
                     description=_("""The distribution in which this
                     maintainership applies."""))
    
    sourcepackagename = TextLine(title=_('Source Package Name'),
        description=_("""The name of the source package being maintained by
        this maintainer."""))

    maintainer = Choice(title=_('Maintainer'), required=True,
                   vocabulary='ValidPerson',
                   description=_("""The person who is the maintainer of this
                   source package in this distribution."""))


class IMaintainershipSet(Interface):
    """The collection of maintainerships in Launchpad for a distribution.
    Note that this may be instantiated with a distribution, and the set
    then includes all of those maintainerships."""

    title = Attribute("""Title for Maintainerships page in Launchpad""")

    def __init__(distribution=None):
        """Instantiate a MaintainershipSet, restricting it optionally to the
        distribution passed as a parameter.""" 

    def __iter__():
        """Return an iterator over all the maintainerships in this
        distribution."""

    def get(distribution, sourcepackagename):
        """Return the maintainer of this sourcepackagename in this
        distribution, if none is found then return None"""

    def getByPersonID(personID, distribution=None):
        """Get the list of Maintainerships for a person, optionally
        restricting to the passed distribution (overriding the instantiated
        set distribution)."""

