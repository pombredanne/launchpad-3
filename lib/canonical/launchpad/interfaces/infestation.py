from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.vocabularies.dbschema import InfestationStatusVocabulary

__all__ = ['IBugProductInfestationContainer',
           'IBugPackageInfestationContainer',
           'IBugProductInfestation',
           'IBugPackageInfestation']


class IBugProductInfestation(Interface):
    """Represents a report that a bug does or does not affect the source
    package to which this infestation points. The extent of the
    "infestation" is given by the infestationstatus field, which takes on
    values documented in dbschema.BugInfestationStatus."""

    id = Int(title=_("Bug Product Infestation ID"), required=True, readonly=True)
    bug = Int(title=_('Bug ID'))
    explicit = Bool(title=_('Explicitly Created by a Human'))
    productrelease = Choice(title=_('Product Release'),
                            vocabulary='ProductRelease')
    infestationstatus = Choice(title=_('Infestation Status'),
                         vocabulary=InfestationStatusVocabulary)
    datecreated = Datetime(title=_('Date Created'))
    creator = Int(title=_('Creator'))
    dateverified = Datetime(title=_('Date Verified'))
    verifiedby = Int(title=_('Verified By'))
    lastmodified = Datetime(title=_('Last Modified'))
    lastmodifiedby = Int(title=_('Last Modified By'))


class IBugPackageInfestation(Interface):
    """Represents a report that a bug does or does not affect the source
    package to which this infestation points. The extent of the
    "infestation" is given by the infestationstatus field, which takes on
    values documented in dbschema.BugInfestationStatus."""

    id = Int(title=_("Bug Package Infestation ID"), required=True, readonly=True)
    bug = Int(title=_('Bug ID'))
    sourcepackagerelease = Choice(title=_('Package Release'),
                                  vocabulary='PackageRelease')
    explicit = Bool(title=_('Explicitly Created by a Human'))
    infestationstatus = Choice(title=_('Infestation Status'),
                         vocabulary=InfestationStatusVocabulary)
    datecreated = Datetime(title=_('Date Created'))
    creator = Int(title=_('Creator'))
    dateverified = Datetime(title=_('Date Verified'))
    verifiedby = Int(title=_('Verified By'))
    lastmodified = Datetime(title=_('Last Modified'))
    lastmodifiedby = Int(title=_('Last Modified By'))


class IBugProductInfestationContainer(Interface):
    """A container for IBugProductInfestations."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugProductInfestation."""

    def __iter__():
        """Iterate through BugProductInfestations for a given bug."""

class IBugPackageInfestationContainer(Interface):
    """A container for IBugPackageInfestations."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugPackageInfestation."""

    def __iter__():
        """Iterate through BugPackageInfestations for a given bug."""

