from zope.interface import Interface, Attribute

class IRosettaApplication(Interface):
    """Rosetta application class."""


class IProjects(Interface):
    """The collection of projects."""

    def __iter__():
        """Iterate over all the projects."""

    def __getitem__(name):
        """Get a project by its name."""

    def new(name, title, url, description, owner):
        """Creates a new project with the given name.

        Returns that project.
        """


class IProject(Interface):
    """A Project.  For example 'mozilla'."""

    name = Attribute("The project's name. (unique within IProjects)")

    title = Attribute("The project's title.")

    url = Attribute("The URL of the project's website.")

    description = Attribute("The project's description.")

    owner = Attribute("The Person who owns this project.")

    def poTemplates():
        """Returns an iterator over this project's PO templates."""

    def products():
        """Returns an iterator over this projects products."""

    def poTemplate(name):
        """Returns the PO template with the given name."""


class IProduct(Interface):
    """A Product.  For example 'firefox' in the 'mozilla' project."""

    name = Attribute("The product's name, unique within a project.")

    title = Attribute("The product's title.")

    description = Attribute("The product's description")

    project = Attribute("The product's project.")

    def poTemplates():
        """Returns an iterator over this product's PO templates."""

    def newPOTemplate(name, title):
        """Creates a new PO template.

        Returns the newly created template.
        """


class IPOTemplate(Interface):
    """A PO template. For example 'nautilus/po/nautilus.pot'."""

    name = Attribute("The PO template's name.  For example 'nautilus'.")

    title = Attribute("The PO template's title.")

    description = Attribute("The PO template's title.")

    product = Attribute("The PO template's product.")

    path = Attribute("The path to the template in the source.")

    owner = Attribute("The owner of the template.")

    isCurrent = Attribute("Whether this template is current or not.")

    # XXX: branch, changeset

    # XXX: copyright, license: where do we get this information?

    def __len__():
        """Returns the number of current IPOMessageSet in this template."""

    def __iter__():
        """Iterate over current IPOMessageSets in this template."""

    def __getitem__(msgid):
        """Get the current IPOMessageSet for this template that has the
        given primary message ID."""

    def languages():
        """Iterate over languages that this template's messages are
        translated into.
        """

    def poFiles():
        """Iterate over the PO files that exist for this language."""

    def poFile(language_code):
        """Get the PO file of the given language.

        Raises KeyError if there is no such POFile."""

    # TODO provide a way to look through non-current message ids.


class IEditPOTemplate(IPOTemplate):
    """Edit interface for an IPOTemplate."""

    def expireAllMessages():
        """Mark our of our message sets as not current (sequence=0)"""

    def newMessageSet(text):
        """Add a message set to this template.  Primary message ID
        is 'text'."""

    def createPOFile(language, variant):
        """Create and return a new po file in the given language.

        Raises an KeyError if a po file of that language already exists.
        """

class IPOFile(Interface):
    """A PO File."""

    poTemplate = Attribute("This PO file's template.")

    language = Attribute("Language of this PO file.")

    title = Attribute("The PO file's title.")

    description = Attribute("PO file description.")

    topComment = Attribute("The main comment for this .po file")

    header = Attribute("The header of this .po file")

    headerFuzzy = Attribute("If the header is fuzzy or not")

    def __len__():
        """Returns the number of current IPOMessageSets in this PO file."""

    def translatedCount():
        """
        Returns the number of message sets which this PO file has current
        translations for.
        """

    def translated():
        """
        Iterate over translated message sets in this PO file.
        """

    def untranslatedCount():
        """
        Return the number of messages which this PO file has no translation
        for.
        """

    def untranslated():
        """
        Iterate over untranslated message sets in this PO file.
        """

    # Invariant: translatedCount() + untranslatedCount() = __len__()
    # XXX: add a test for this

    def __iter__():
        """Iterate over IPOMessageSets in this PO file."""

    def __getitem__(IPOMessageSet):
        """Returns the IPOMessageSet with the corresponding translations, if
        it exists. The parameter should probably come from a template. We
        think."""


class IEditPOFile(IPOFile):
    """Edit interface for a PO File."""

    def expireAllMessages():
        """Mark our of our message sets as not current (sequence=0)"""

    def newTranslation(IPOTSighting_or_msgid):
        """Create and return a new IPOTranslation.

        Use either the IPOTSighting or, if this message doesn't already
        occur in the POTFile, use the msgid.
        """


class IPOMessageSet(Interface):
    """A collection of message IDs and possibly translations."""

    id = Attribute("""A unique ID for the message set.""")

    id = Attribute("""An identifier for this POMessageSet""")

    poTemplate = Attribute("""The template this set is associated with.""")

    poFile = Attribute("""The PO file this set is associated with, if it's
        associated with a PO file. For sets from PO templates, this is
        None.""")

    # Invariant: poTemplate == None || poFile == None
    # Invariant: poTemplate != None || poFile != None

    # Rephrased:
    # Invariant: ((poTemplate == None) && (poFile != None)) ||
    #            ((poTemplate != None) && (poFile == None))

    # XXX: test that

    primeMessageID_ = Attribute("The primary message ID of this set.")

    sequence = Attribute("The ordering of this set within its file.")

    isComplete = Attribute("For PO file message sets, whether the "
        "translation is complete or not. (I.e. all message IDs have "
        "a translation.")

    obsolete = Attribute("""
        Whether this set was marked as obsolete in the PO file it came from.

        Applies only to sets from PO files.
        """)

    fuzzy = Attribute("""
        Whether this set was marked as fuzzy in the PO file it came from.

        Applies only to sets from PO files.
        """)

    commentText = Attribute("""
        Text of translator comment from the PO file.

        Applies only to sets from PO files.
        """)

    fileReferences = Attribute("""
        References to source files for a message ID.

        Applies only to sets from PO templates.
        """)

    sourceComment = Attribute("""
        Comment from the source code for a message ID.

        Applies only to sets from PO templates.
        """)

    flagsComment = Attribute("""
        Flags for this set.
        """)

    def messageIDs():
        """Iterate over this set's message IDs."""

    def getMessageIDSighting(plural_form):
        """Return the message ID sighting that is current and has the
        plural form provided."""

    # The primary message ID is the same as the message ID with plural
    # form 0 -- i.e. it's redundant. However, it acts as a cached value.

    def translations():
        """Iterate over this set's translations."""

    def getTranslationSighting(plural_form):
        """Return the translation sighting that is current and has the
        plural form provided."""

    def translationSightings():
        """Iterate over current translation sightings."""


class IEditPOMessageSet(IPOMessageSet):
    """Interface for editing a MessageSet."""

    def makeMessageIDSighting(text, plural_form):
        """Return a new message ID sighting that points back to us."""

    def makeTranslationSighting(text, plural_form):
        """Return a new translation sighting that points back to us."""


class IPOMessageIDSighting(Interface):
    """A message ID from a template."""

    poMessageSet = Attribute("")

    poMessageID_ = Attribute("")

    firstSeen = Attribute("")

    lastSeen = Attribute("")

    inPOFile = Attribute("True if this sighting is currently in the PO file, "
        "otherwise false.")

    pluralForm = Attribute("")


class IEditPOMessageIDSighting(IPOMessageIDSighting):
    """Interface for editing a MessageIDSighting."""

    def touch():
        """Update timestamp of this sighting and mark it as inPOFile."""


class IPOMessageID(Interface):
    """A PO message ID."""

    # this is called "msgid" in the DB
    text = Attribute("")


class IPOTranslationSighting(Interface):
    """A sighting of a translation in a PO file."""

    poMessageSet = Attribute("")

    poTranslation = Attribute("")

    # XXX: license

    firstSeen = Attribute("")

    lastTouched = Attribute("")

    inPOFile = Attribute("")

    origin = Attribute("Where the sighting originally came from.")

    pluralForm = Attribute("")

    deprecated = Attribute("")

    # XXX: rename this to 'owner'?
    person = Attribute("")


class IPOTranslation(Interface):
    """A translation in a PO file."""

    # this is called "translation" in the DB
    text = Attribute("")


class IBranch(Interface):
    """A soyuz branch."""

    title = Attribute("The branch's title.")

    description = Attribute("The branch's descrition.")


# sketch of various interfaces

class IPerson(Interface):
    """A person in the system."""

    presentationName = Attribute("""The name of this person.""")

    isMaintainer = Attribute("""Is this person a project maintainer.""")

    isTranslator = Attribute("""Is this person a translator.""")

    isContributor = Attribute("""Is this person a contributor.""")

    # Invariant: isMaintainer implies isContributor

    def maintainedProjects():
        """iterate over projects this person maintains"""

    # Invariant: len(list(maintainedProjects())) > 0 implies isMaintainer

    def translatedProjects():
        """iterate over projects this person translates

        Results are sorted most-recently translated first.
        """

    # Invariant: len(list(translatedProjects())) > 0 implies isTranslator

    def languages():
        """The languages a person has expressed interest in."""


class ILanguage(Interface):
    """A lanaguage."""

    code = Attribute("""The ISO 639 code for this language.""")

    englishName = Attribute("The English name of this language.")

    nativeName = Attribute("The name of this language in the language itself.")


class ILanguages(Interface):
    """The collection of languages."""

    def __getitem__(code):
        """Get a language by its code."""

    def keys():
        """Iterate over the language codes."""


class IPOExport(Interface):
    """Interface to export .po/.pot files"""

    def export(language):
        """Exports the .po file for the specific language"""

