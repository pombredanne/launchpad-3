# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


from canonical.launchpad.interfaces.schema import ILabel
from canonical.launchpad.interfaces.project import IProject

class ICategory(ILabel):
    """An Effort Category."""

    def poTemplates():
        """Returns an iterator over this category's PO templates."""

    def poTemplate(name):
        """Returns the PO template with the given name."""

    def messageCount():
        """Returns the number of Current IPOMessageSets in all templates
        inside this category."""

    def currentCount(language):
        """Returns the number of msgsets matched to a potemplate for this
        category that have a non-fuzzy translation in its PO file for this
        language when we last parsed it."""

    def updatesCount(language):
        """Returns the number of msgsets for this category where we have a
        newer translation in rosetta than the one in the PO file for this
        language, when we last parsed it."""

    def rosettaCount(language):
        """Returns the number of msgsets where we have a translation in rosetta
        but there was no translation in the PO file for this language when we
        last parsed it."""


class ITranslationEfforts(Interface):
    """The collection of translation efforts."""

    def __iter__():
        """Return an iterator over all translation efforts."""

    def __getitem__(name):
        """Get a translation effort by its name."""

    def new(name, title, description, owner, project):
        """Creates a new translation effort with the given name.

        Returns that translation effort.

        Raises an KeyError if a translation effort with that name already exists.
        """

    def search(query):
        """Search for translation efforts matching a certain strings."""


class ITranslationEffort(Interface):
    """A translation effort.  For example 'gtp'."""

    name = Attribute("""The translation effort's name. (unique within
        ITranslationEfforts)""")

    title = Attribute("The translation effort's title.")

    shortDescription = Attribute("""The translation effort's short
        description.""")

    description = Attribute("The translation effort's description.")

    owner = Attribute("The Person who owns this translation effort.")

    project = Attribute("""The Project associated with this translation
        effort.""")

    categoriesSchema = Attribute("""The schema that defines the valid
        categories we have for this effort.""")

    def category(name):
        """Returns the category with the given name."""

    def categories():
        """Returns an iterator over this translation effort's categories."""

    def messageCount():
        """Returns the number of Current IPOMessageSets in all templates
        inside this translation effort."""

    def currentCount(language):
        """Returns the number of msgsets matched to a potemplate for this
        translation effort that have a non-fuzzy translation in its PO file
        for this language when we last parsed it."""

    def updatesCount(language):
        """Returns the number of msgsets for this translation effort where
        we have a newer translation in rosetta than the one in the PO file
        for this language, when we last parsed it."""

    def rosettaCount(language):
        """Returns the number of msgsets where we have a translation in rosetta
        but there was no translation in the PO file for this language when we
        last parsed it."""


# XXX: I think we could hide this object from the Interface
class ITranslationEffortPOTemplate(Interface):
    """The object that relates a POTemplate with a Translation Effort."""

    poTemplate = Attribute("The POTemplate we are refering.")

    category = Attribute("The Category where we have the poTemplate.")

    priority = Attribute("The priority for this poTemplate")

    translationEffort = Attribute("The category's translation effort.")
