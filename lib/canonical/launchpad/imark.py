# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


from canonical.launchpad.interfaces.schema import ILabel
from canonical.launchpad.interfaces.project import IProject

class IPOExport(Interface):
    """Interface to export .po/.pot files"""

    def export(language):
        """Exports the .po file for the specific language"""


class IRosettaApplication(Interface):
    """Rosetta application class."""


class IRosettaStats(Interface):
    """Rosetta-related statistics."""

    def messageCount():
        """Returns the number of Current IPOMessageSets in all templates
        inside this project."""

    def currentCount(language):
        """Returns the number of msgsets matched to a potemplate for this
        project that have a non-fuzzy translation in its PO file for this
        language when we last parsed it."""

    def updatesCount(language):
        """Returns the number of msgsets for this project where we have a
        newer translation in rosetta than the one in the PO file for this
        language, when we last parsed it."""

    def rosettaCount(language):
        """Returns the number of msgsets where we have a translation in rosetta
        but there was no translation in the PO file for this language when we
        last parsed it."""


class IRosettaProject(IRosettaStats, IProject):
    """The rosetta interface to a project."""

    displayname = Attribute("The Project's name that will be showed.")

    def poTemplates():
        """Returns an iterator over this project's PO templates."""

    def product(name):
        """Return the product belonging to this project with the given
        name."""


class IDOAPApplication(Interface):
    """DOAP application class."""

class IFOAFApplication(Interface):
    """FOAF application class."""

