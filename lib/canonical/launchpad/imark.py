# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')



class IBugTrackerSet(Interface):
    """An interface for the BugTrackerSet. This models a set of BugTracker's
    (either the full set in the db or a subset). Each BugTracker is a
    distinct instance of a bug tracking tool. For example,
    bugzilla.mozilla.org is distinct from bugzilla.gnome.org.
    """
    def __getitem__(name):
        """Get a BugTracker by its name in the database. NB! We do not want to
        expose the BugTracker.id to the world so we use its name.
        """

    def __iter__():
        """Iterate through BugTrackers."""



class ISourceSource(Interface):
    """A SourceSource job. This is a holdall for data about the upstream
    revision control system of an open source product, and whether or not
    we are able to syncronise our Arch repositories with that upstream
    revision control system. It allows for access to objects that model
    the SourceSource table."""
    #
    # XXX Mark Shuttleworth 03/10/04 Robert Collins please give a better
    #     description of each field below.
    #
    name = Attribute("The sourcesource unix name, a one-word lowercase \
        unique name for this sourcesource.")
    title = Attribute("The Title of this SourceSource")
    description = Attribute("A description of this SourceSource")
    cvsroot = Attribute("The CVSRoot of this SourceSource")
    cvsmodule = Attribute("The CVS Module of this SourceSource")
    cvstarfile = Attribute("The TAR file name of the CVS repo tarball")
    branchfrom = Attribute("Branch From...")
    svnrepository = Attribute("Subversion repository, if this code is in\
    subversion")
    archarchive = Attribute("the target archive")
    category = Attribute("the arch category to use")
    branchto = Attribute("branchto.. don't know what that is")
    archversion = Attribute("the arch version to use when importing this \
    code to arch")
    archsourcegpgkeyid = Attribute("arch gpgkeyid not sure what this is for")
    archsourcename = Attribute("arch source name... not sure again")
    archsourceurl = Attribute("arch source url, again not sure")
    product=Attribute ("a product backlink for this sourcesource")
    
    def autosync():
        """enable this sourcesource for automatic syncronisation"""
    
    def autosyncing():
        """is the sourcesource enabled for automatic syncronisation?"""
    
    def canChangeProduct():
        """is this sync allowed to have its product changed?"""
    
    def changeProduct(product):
        """change the product this sync belongs to to be 'product'"""
    
    def enable():
        """enable this sync"""
    def enabled():
        """is the sync enabled?"""
    def update(**kwargs):
        """update a Sync, possibly reparenting"""



class IProject(Interface):
    """A Project."""

    id = Int(title=_('ID'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'))
    displayname = TextLine(title=_('Display Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    shortdesc = Text(title=_('Short Description'))
    homepageurl = TextLine(title=_('Homepage URL'))

    def bugtrackers():
        """Return the BugTrackers for this Project."""

    def products():
        """Return Products for this Project."""

    def getProduct(name):
        """Get a product with name `name`."""
    
    def rosettaProducts():
        """Iterates over Rosetta Products in this project.
        XXX Mark Shuttleworth 02/10/04 what is the difference
            between a Rosetta Product and a normal product?
            Can this duplication be cleaned up or the difference
            clarified and documented?"""

    # XXX: This will go away once we move to project->product->potemplate
    #      traversal rather than project->potemplate traversal.
    def poTemplate(name):
        """Returns the RosettaPOTemplate with the given name."""

    def shortDescription(aDesc=None):
        """return the projects shortdesc, setting it if aDesc is provided"""



class ISchemas(Interface):
    """The collection of schemas."""

    def __getitem__(name):
        """Get a schema by its name."""

    def keys():
        """Return an iterator over the schemas names."""


class ISchema(Interface):
    """A Schema."""

    owner = Attribute("The Person who owns this schema.")

    name = Attribute("The name of this schema.")

    title = Attribute("The title of this schema.")

    description = Attribute("The description of this schema.")

    def labels():
        """Return an iterator over all labels associated with this schema."""

    def label(name):
        """Returns the label with the given name."""


class ILabel(Interface):
    """A Label."""

    schema = Attribute("The Schema associated with this label.")

    name = Attribute("The name of this schema.")

    title = Attribute("The title of this schema.")

    description = Attribute("The description of this schema.")

    def persons():
        """Returns an iterator over all persons associated with this Label."""


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

class IEmailAddress(Interface):
    """The object that stores the IPerson's emails."""

    person = Attribute("The Person owner of this email.""")

    email = Attribute("The email address.""")

    status = Attribute("The status of this email address.""")

class IBranchFromRosetta(Interface):
    """A soyuz branch."""

    title = Attribute("The branch's title.")

    description = Attribute("The branch's descrition.")


# sketch of various interfaces

class IPersonFromRosetta(Interface):
    """A person in the system."""

    displayname = Attribute("""The full name of this person.""")

    givenName = Attribute("""The name of this person.""")

    familyName = Attribute("""The surname of this person.""")

    password = Attribute("""SSHA encrypted password.""")

    # XXX: These attributes disabled because there is no support for them in
    # the database schema.

    #isMaintainer = Attribute("""Is this person a project maintainer.""")

    #isTranslator = Attribute("""Is this person a translator.""")

    #isContributor = Attribute("""Is this person a contributor.""")

    # Invariant: isMaintainer implies isContributor

    def emails():
        """iterate over all emails associated with this person"""

    def maintainedProjects():
        """iterate over projects this person maintains"""

    # Invariant: len(list(maintainedProjects())) > 0 implies isMaintainer

    def translatedProjects():
        """iterate over projects this person translates

        Results are sorted most-recently translated first.
        """

    def translatedTemplates():
        """Templates this person has translated, most recent first."""

    # Invariant: len(list(translatedProjects())) > 0 implies isTranslator

    def languages():
        """The languages a person has expressed interest in."""

    def addLanguage(language):
        """Adds the language to its list of interested languages."""

    def removeLanguage(language):
        """Removes the language from the list on interested ones."""


class ILanguage(Interface):
    """A Language."""

    code = Attribute("""The ISO 639 code for this language.""")

    englishName = Attribute("The English name of this language.")

    nativeName = Attribute("The name of this language in the language itself.")

    pluralForms = Attribute("The number of plural forms this language has.")

    pluralExpression = Attribute("""The expression that relates a number of
        items to the appropriate plural form.""")

    # XXX: Review. Do you think this method is good for the interface?.
    def translateLabel():
        """The ILabel used to say that some is interested on ILanguage"""

    def translators():
        """The Persons that are interested on translate into this language."""


class ILanguages(Interface):
    """The collection of languages."""

    def __iter__():
        """Returns an iterator over all languages."""

    def __getitem__(code):
        """Get a language by its code."""

    def keys():
        """Return an iterator over the language codes."""


class IPOExport(Interface):
    """Interface to export .po/.pot files"""

    def export(language):
        """Exports the .po file for the specific language"""



class IPOTemplate(Interface):
    """A PO template. For example 'nautilus/po/nautilus.pot'."""

    name = Attribute("The PO template's name.  For example 'nautilus'.")

    title = Attribute("The PO template's title.")

    description = Attribute("The PO template's description.")

    product = Attribute("The PO template's product.")

    path = Attribute("The path to the template in the source.")

    owner = Attribute("The owner of the template.")

    isCurrent = Attribute("Whether this template is current or not.")

    dateCreated = Attribute("When this template was created.")

    dateCreated = Attribute("When this template was created.")

    # XXX: branch, changeset

    # XXX: copyright, license: where do we get this information?

    # A "current" messageset is one that was in the latest version of
    # the POTemplate parsed and recorded in the database. Current
    # MessageSets are indicated by having 'sequence > 0'

    def __len__():
        """Returns the number of Current IPOMessageSets in this template."""

    def __iter__():
        """Return an iterator over Current IPOMessageSets in this template."""

    def messageSet(key, onlyCurrent=False):
        """Extract one or several POMessageSets from this template.

        If the key is a string or a unicode object, returns the
        IPOTemplateMessageSet in this template that has a primary message ID
        with the given text.

        If the key is a slice, returns the message IDs by sequence within the
        given slice.

        If onlyCurrent is True, then get only current message sets.
        """

    def __getitem__(key):
        """Same as messageSet(), with onlyCurrent=True
        """

    def languages():
        """Return an iterator over languages that this template's messages are
        translated into.
        """

    def poFiles():
        """Return an iterator over the PO files that exist for this language."""

    def poFile(language_code, variant=None):
        """Get the PO file of the given language and (potentially)
        variant. If no variant is specified then the translation
        without a variant is given.

        Raises KeyError if there is no such POFile."""

    def newPOFile(language, person, variant=None):
        """Creates a new PO file of the given language and (potentially)
        variant.

        Raises KeyError if there is already such POFile."""

    def currentCount(language):
        """Returns the number of msgsets matched to a this potemplate that have
        a non-fuzzy translation in its PO file for this language when we last
        parsed it."""

    def updatesCount(language):
        """Returns the number of msgsets where we have a newer translation in
        rosetta than the one in the PO file for this language, when we last
        parsed it."""

    def rosettaCount(language):
        """Returns the number of msgsets where we have a translation in rosetta
        but there was no translation in the PO file for this language when we
        last parsed it."""

    def hasMessageID(msgid):
        """Check whether a message set with the given message ID exists within
        this template."""

    def hasPluralMessage():
        """Test whether this template has any message sets which are plural
        message sets."""

    # TODO provide a way to look through non-current message ids.


class IEditPOTemplate(IPOTemplate):
    """Edit interface for an IPOTemplate."""

    def expireAllMessages():
        """Mark all of our message sets as not current (sequence=0)"""

    #def makeMessageSet(messageid_text, pofile=None):
    #    """Add a message set to this template.  Primary message ID
    #    is 'messageid_text'.
    #    If one already exists, a KeyError is raised."""

    def newPOFile(person, language_code, variant=None):
        """Create and return a new po file in the given language. The
        variant is optional.

        Raises an KeyError if a po file of that language already exists.
        """

    def createMessageSetFromMessageID(msgid):
        """Creates in the database a new message set.

        As a side-effect, creates a message ID sighting in the database for the
        new set's prime message ID.

        Returns the newly created message set.
        """

    def createMessageSetFromText(text):
        """Creates in the database a new message set.

        Similar to createMessageSetFromMessageID, but takes a text object
        (unicode or string) rather than a message ID.

        Returns the newly created message set.
        """

class IPOFile(Interface):
    """A PO File."""

    poTemplate = Attribute("This PO file's template.")

    language = Attribute("Language of this PO file.")

    title = Attribute("The PO file's title.")

    description = Attribute("PO file description.")

    topComment = Attribute("The main comment for this .po file.")

    header = Attribute("The header of this .po file.")

    headerFuzzy = Attribute("Whether the header is fuzzy or not.")

    pluralForms = Attribute("The number of plural forms this PO file has.")

    variant = Attribute("The language variant for this PO file.")

    currentCount = Attribute("""
        The number of msgsets matched to the potemplate that have a
        non-fuzzy translation in the PO file when we last parsed it
        """)

    updatesCount = Attribute("""
        The number of msgsets where we have a newer translation in
        rosetta than the one in the PO file when we last parsed it
        """)

    rosettaCount = Attribute("""
        The number of msgsets where we have a translation in rosetta
        but there was no translation in the PO file when we last parsed it
        """)

    def __len__():
        """Returns the number of current IPOMessageSets in this PO file."""

    def translatedCount():
        """
        Returns the number of message sets which this PO file has current
        translations for.
        """

    def translated():
        """
        Return an iterator over translated message sets in this PO file.
        """

    def untranslatedCount():
        """
        Return the number of messages which this PO file has no translation
        for.
        """

    def untranslated():
        """
        Return an iterator over untranslated message sets in this PO file.
        """

    # Invariant: translatedCount() + untranslatedCount() = __len__()
    # XXX: add a test for this

    def __iter__():
        """Return an iterator over Current IPOMessageSets in this PO file."""

    def __getitem__(msgid):
        """Get the IPOMessageSet for this template that has the
        given primary message ID. Note that this will also find old
        (not current) MessageSets"""

    def messageSetsNotInTemplate():
        """
        Return an iterator over message sets in this PO file that do not
        correspond to a message set in the template; eg, the template
        message set is either absent or has sequence=0.
        """

    def hasMessageID(msgid):
        """Check whether a message set with the given message ID exists within
        this PO file."""

class IEditPOFile(IPOFile):
    """Edit interface for a PO File."""

    def expireAllMessages():
        """Mark our of our message sets as not current (sequence=0)"""

    def updateStatistics():
        """Update the statistics fields - rosettaCount, updatesCount and
        currentCount - from the messages currently known.
        Return a tuple (rosettaCount, updatesCount, currentCount)."""

    def createMessageSetFromMessageID(messageID):
        """See IEditPOTemplate."""

    def createMessageSetFromText(text):
        """See IEditPOTemplate."""

class IPOMessageSet(Interface):
    """A collection of message IDs and possibly translations."""

    id = Attribute("""An identifier for this POMessageSet""")

    poTemplate = Attribute("""The template this set is associated with.""")

    # The primary message ID is the same as the message ID with plural
    # form 0 -- i.e. it's redundant. However, it acts as a cached value.

    primeMessageID_ = Attribute("The primary message ID of this set.")

    sequence = Attribute("The ordering of this set within its file.")

    def flags():
        """Return a list of flags on this set."""

    def messageIDs():
        """Return an iterator over this set's message IDs."""

    def getMessageIDSighting(pluralForm):
        """Return the message ID sighting that is current and has the
        plural form provided."""


class IEditPOMessageSet(IPOMessageSet):
    """Interface for editing a MessageSet."""

    def makeMessageIDSighting(text, pluralForm, update=False):
        """Return a new message ID sighting that points back to us.
        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is "touched" and returned.  If it
        is not, then a KeyError is raised."""


class IPOTemplateMessageSet(IPOMessageSet):
    def translationsForLanguage(language):
        """Return an iterator over translation strings for this set in the
        given language.

        This method is applicable to PO template sets only.

        XXX: This is quite UI-oriented. Refactor?
        """


# No IEditPOTemplateMessageSet.


class IPOFileMessageSet(IPOMessageSet):
    poFile = Attribute("""The PO file this set is associated with, if it's
        associated with a PO file. For sets from PO templates, this is
        None.""")

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

    def templateMessageSet():
        """Return the corresponding IPOTemplateMessageSet."""

    def pluralForms():
        """Number of translations that have to point to this message set
        for it to be complete."""

    def translations():
        """Return an iterator over this set's translations."""

    def getTranslationSighting(pluralForm, allowOld=False):
        """Return the translation sighting that is current and has the
        plural form provided.  If allowOld is True, include non-current."""

    def translationSightings():
        """Return an iterator over current translation sightings."""


class IEditPOFileMessageSet(IPOFileMessageSet):
    """Interface for editing a MessageSet."""

    def makeTranslationSighting(person, text, pluralForm, update=False, fromPOFile=False):
        """Return a new translation sighting that points back to us.
        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is "touched" and returned.  If it
        is not, then a KeyError is raised.
        fromPOFile should be true when the sighting is coming from a POFile
        in the upstream source - so that the inLatestRevision field is
        set accordingly."""


class IEditPOTemplateOrPOFileMessageSet(IPOTemplateMessageSet,
        IEditPOFileMessageSet):
    pass


class IPOMessageIDSighting(Interface):
    """A message ID from a template."""

    poMessageSet = Attribute("")

    poMessageID_ = Attribute("")

    dateFirstSeen = Attribute("")

    dateLastSeen = Attribute("")

    inLastRevision = Attribute("True if this sighting is currently in the "
                               "upstream template or POFile, otherwise false.")

    pluralForm = Attribute("")


class IPOMessageID(Interface):
    """A PO message ID."""

    # this is called "msgid" in the DB
    msgid = Attribute("")


# no IEditPOMessageID - message IDs are read-only


class IPOTranslationSighting(Interface):
    """A sighting of a translation in a PO file."""

    poMessageSet = Attribute("")

    poTranslation = Attribute("")

    # XXX: license

    dateFirstSeen = Attribute("")

    dateLastActive = Attribute("")

    inLastRevision = Attribute("True if this sighting is currently in the "
                               "upstream POFile, otherwise false.")

    origin = Attribute("Where the sighting originally came from.")

    pluralForm = Attribute("")

    active = Attribute("")

    # XXX: rename this to 'owner'?
    person = Attribute("")


class IPOTranslation(Interface):
    """A translation in a PO file."""

    # this is called "translation" in the DB
    translation = Attribute("")


# no IEditPOTranslation - translations are read-only


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


class IEmailAddress(Interface):
    id = Int(
        title=_('ID'), required=True, readonly=True,
        )
    email = Text(
        title=_('Email Address'), required=True,
        )
    status = Int(
        title=_('Status'), required=True,
        )
    person = Int(
        title=_('Person'), required=True,
        )
    
class IPerson(Interface):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    displayname = TextLine(
            title=_('Display Name'), required=False, readonly=False,
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            )
    password = Password(
            title=_('Password'), required=False, readonly=False,
            )
    teamowner = Int(
            title=_('Team Owner'), required=False, readonly=False,
            )
    teamdescription = TextLine(
            title=_('Team Description'), required=False, readonly=False,
            )
    # TODO: This should be required in the DB, defaulting to something
    karma = Int(
            title=_('Karma'), required=False, readonly=True,
            )
    # TODO: This should be required in the DB, defaulting to something
    karmatimestamp = Datetime(
            title=_('Karma Timestamp'), required=False, readonly=True,
            )

class IDOAPApplication(Interface):
    """DOAP application class."""

# Interfaces for containers

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(querytext):
        """Search through Projects."""


class IFOAFApplication(Interface):
    """FOAF application class."""

# Interfaces for containers

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(querytext):
        """Search through Projects."""

class IProjectSet(Interface):
    """The collection of projects."""

    def __iter__():
        """Return an iterator over all the projects."""

    def __getitem__(name):
        """Get a project by its name."""

    # XXX needs displayname, shortdesc, NO url
    def new(name, title, url, description, owner):
        """Creates a new project with the given name.

        Returns that project.

        Raises an KeyError if a project with that name already exists.
        """

    def search(query):
        """Search for projects matching a certain strings."""


class IProduct(Interface):
    """A DOAP Product. DOAP describes the open source world as Projects
    and Products. Each Project may be responsible for several Products.
    For example, the Mozilla Project has Firefox, Thunderbird and The
    Mozilla App Suite as Products, among others."""
    
    project = Int(title=_('The Project that is responsible for this product.'))
    
    owner = Int(title=_('Owner'))

    name = TextLine(title=_('The short name of this product, which must be \
        unique among all the products from the same project.'))

    displayname = TextLine(title=_('The display name of this product, is \
        the name of this product as it would appear in a paragraph of text.'))

    title = TextLine(title=_('The product title. Should be just a few words.'))

    shortdesc = Text(title=_('A short description, should be a single \
        short paragraph.'))

    description = Text(title=_('The product description, may be several\
        paragraphs of text, giving the product highlights and details.'))

    homepageurl = TextLine(title=_('A Homepage URL for this product.'))

    manifest = TextLine(title=_('Manifest'))

    sourcesources = Attribute(_('Sources of source code. These are \
        pointers to the revision control system for that product, along \
        with status information about our ability to publish that \
        source in Arch.'))

    def bugs():
        """Return ProductBugAssignments for this Product."""

    def poTemplates():
        """Returns an iterator over this product's PO templates."""

    def poTemplate(name):
        """Returns the PO template with the given name."""

    def newPOTemplate(person, name, title):
        """Creates a new PO template.

        Returns the newly created template.

        Raises an KeyError if a PO template with that name already exists.
        """

    def messageCount():
        """Returns the number of Current IPOMessageSets in all templates
        inside this product."""

    def currentCount(language):
        """Returns the number of msgsets matched to a potemplate for this
        product that have a non-fuzzy translation in its PO file for this
        language when we last parsed it."""

    def updatesCount(language):
        """Returns the number of msgsets for this product where we have a
        newer translation in rosetta than the one in the PO file for this
        language, when we last parsed it."""

    def rosettaCount(language):
        """Returns the number of msgsets for all POTemplates in this Product
        where we have a translation in Rosetta but there was no translation
        in the PO file for this language when we last parsed it."""

