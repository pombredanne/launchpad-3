
from zope.interface import Interface, Attribute

class IRosettaStats(Interface):
    """Rosetta-related statistics."""

    def messageCount():
        """Returns the number of Current IPOMessageSets in all templates
        inside this project."""

    def currentCount(language=None):
        """Returns the number of msgsets matched to a potemplate for this
        project that have a non-fuzzy translation in its PO file for this
        language when we last parsed it."""

    def updatesCount(language=None):
        """Returns the number of msgsets for this project where we have a
        newer translation in rosetta than the one in the PO file for this
        language, when we last parsed it."""

    def rosettaCount(language=None):
        """Returns the number of msgsets where we have a translation in rosetta
        but there was no translation in the PO file for this language when we
        last parsed it."""


class IPOTemplate(IRosettaStats):
    """A PO template. For example 'nautilus/po/nautilus.pot'."""

    product = Attribute("The PO template's product.")

    priority = Attribute("The PO template priority.")

    branch = Attribute("The branch where this PO template is.")

    changeset = Attribute("The changeset where this PO template is.")

    name = Attribute("The PO template's name.  For example 'nautilus'.")

    title = Attribute("The PO template's title.")

    description = Attribute("The PO template's description.")

    copyright = Attribute("The copyright information for this PO template.")

    license = Attribute("The license that applies to this PO template.")

    datecreated = Attribute("When this template was created.")

    path = Attribute("The path to the template in the source.")

    iscurrent = Attribute("Whether this template is current or not.")

    owner = Attribute("The owner of the template.")

    rawfile = Attribute("The pot file itself in raw mode.")
   
    rawimporter = Attribute("The person that attached the rawfile.")
    
    daterawimport = Attribute("The date when the rawfile was attached.")

    rawimportstatus = Attribute("""The status of the import: 0 pending import, 1
        imported, 2 failed.""")


    # A "current" messageset is one that was in the latest version of
    # the POTemplate parsed and recorded in the database. Current
    # MessageSets are indicated by having 'sequence > 0'

    def __len__():
        """Returns the number of Current IPOMessageSets in this template."""

    def __iter__():
        """Return an iterator over Current IPOMessageSets in this template."""

    def messageSet(key, onlyCurrent=False):
        """Extract one or several POTMessageSets from this template.

        If the key is a string or a unicode object, returns the
        IPOMsgSet in this template that has a primary message ID
        with the given text.

        If the key is a slice, returns the message IDs by sequence within the
        given slice.

        If onlyCurrent is True, then get only current message sets.
        """

    def __getitem__(key):
        """Same as messageSet(), with onlyCurrent=True
        """

    def filterMessageSets(current, translated, languages, slice):
        '''
        Return message sets from this PO template, filtered by various
        properties.

        current:
            Whether the message sets need be complete or not.
        translated:
            Wether the messages sets need be translated in the specified
            languages or not.
        languages:
            The languages used for testing translatedness.
        slice:
            The range of results to be selected, or None, for all results.
        '''

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


class IPOTMsgSet(Interface):
    """A collection of message IDs."""

    id = Attribute("""An identifier for this POTMsgSet""")

    # The primary message ID is the same as the message ID with plural
    # form 0 -- i.e. it's redundant. However, it acts as a cached value.

    primemsgid_ = Attribute("The primary msgid for this set.")

    sequence = Attribute("The ordering of this set within its file.")

    potemplate = Attribute("The template this set is associated with.")

    commenttext = Attribute("The manual comments this set has.")

    filereferences = Attribute("The files where this set appears.")

    sourcecomment = Attribute("The source code comments this set has.")

    flagscomment = Attribute("The flags this set has.")

    def flags():
        """Return a list of flags on this set."""

    def messageIDs():
        """Return an iterator over this set's message IDs."""

    def getMessageIDSighting(pluralForm):
        """Return the message ID sighting that is current and has the
        plural form provided."""

    def translationsForLanguage(language):
        """Return an iterator over translation strings for this set in the
        given language.

        XXX: This is quite UI-oriented. Refactor?
        """


class IEditPOTMsgSet(IPOTMsgSet):
    """Interface for editing a MessageSet."""

    def makeMessageIDSighting(text, pluralForm, update=False):
        """Return a new message ID sighting that points back to us.
        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is "touched" and returned.  If it
        is not, then a KeyError is raised."""


class IPOMsgIDSighting(Interface):
    """A message ID from a template."""

    potmsgset = Attribute("The message set for this sighting.")

    pomsgid_ = Attribute("The msgid that is beeing sighted.")

    datefirstseen = Attribute("First time we saw the msgid.")

    datelastseen = Attribute("Last time we saw the msgid.")

    inlastrevision = Attribute("""True if this sighting is currently in last 
        imported template or POFile, otherwise false.""")

    pluralform = Attribute("0 if it's singular and 1 if it's plural")


class IPOMsgID(Interface):
    """A PO message ID."""

    msgid = Attribute("A msgid string.")


class IPOFile(IRosettaStats):
    """A PO File."""

    potemplate = Attribute("This PO file's template.")

    language = Attribute("Language of this PO file.")

    title = Attribute("The PO file's title.")

    description = Attribute("PO file description.")

    topcomment = Attribute("The main comment for this .po file.")

    header = Attribute("The header of this .po file.")

    fuzzyheader = Attribute("Whether the header is fuzzy or not.")

    lasttranslator = Attribute("The las person that do a translation here.")

    license = Attribute("The license under this translation is done.")

    lastparsed = Attribute("Last time this pofile was parsed.")

    owner = Attribute("The owner for this pofile.")

    pluralforms = Attribute("The number of plural forms this PO file has.")

    variant = Attribute("The language variant for this PO file.")

    filename = Attribute("The name of the file that was imported")

    rawfile = Attribute("The pot file itself in raw mode.")
   
    rawimporter = Attribute("The person that attached the rawfile.")
    
    daterawimport = Attribute("The date when the rawfile was attached.")

    rawimportstatus = Attribute("""The status of the import: 0 pending import, 1
        imported, 2 failed.""")

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

    def messageSet(key, onlyCurrent=False):
        """Extract one or several POMessageSets from this template.

        If the key is a string or a unicode object, returns the
        IPOMsgSet in this template that has a primary message ID
        with the given text.

        If the key is a slice, returns the message IDs by sequence within the
        given slice.

        If onlyCurrent is True, then get only current message sets.
        """

    def __getitem__(msgid):
        """Same as messageSet(), with onlyCurrent=True.
        """

    def messageSetsNotInTemplate():
        """
        Return an iterator over message sets in this PO file that do not
        correspond to a message set in the template; eg, the template
        message set has sequence=0.
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

    def createMessageSetFromMessageSet(potmsgset):
        """Creates in the database a new message set.

        Returns the newly created message set.
        """

    def createMessageSetFromText(text):
        """Creates in the database a new message set.

        Similar to createMessageSetFromMessageSet, but takes a text object
        (unicode or string) rather than a POT message Set.

        Returns the newly created message set.
        """


class IPOMsgSet(Interface):
    sequence = Attribute("The ordering of this set within its file.")

    pofile = Attribute("The PO file this set is associated with.")

    iscomplete = Attribute("""Whether the translation is complete or not. 
        (I.e. all message IDs have a translation.""")

    obsolete = Attribute("""Whether this set was marked as obsolete in the 
        PO file it came from.""")

    fuzzy = Attribute("""Whether this set was marked as fuzzy in the PO file 
        it came from.""")

    commenttext = Attribute("Text of translator comment from the PO file.")

    potmsgset = Attribute("The msgid set that is translating this set.")

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


class IEditPOMsgSet(IPOMsgSet):
    """Interface for editing a POMsgSet."""

    fuzzy = Attribute("""Whether this set was marked as fuzzy in the PO file 
        it came from.""")

    def makeTranslationSighting(person, text, pluralForm, update=False, fromPOFile=False):
        """Return a new translation sighting that points back to us.
        If one already exists, behaviour depends on 'update'; if update
        is allowed, the existing one is "touched" and returned.  If it
        is not, then a KeyError is raised.
        fromPOFile should be true when the sighting is coming from a POFile
        in the upstream source - so that the inLatestRevision field is
        set accordingly."""


class IPOTranslationSighting(Interface):
    """A sighting of a translation in a PO file."""

    pomsgset = Attribute("The PO message set for which is this sighting.")

    potranslation = Attribute("The translation that is sighted.")

    license = Attribute("The license that has this sight.")

    datefirstseen = Attribute("The first time we saw this translation.")

    datelastactive = Attribute("Last time we saw this translation.")

    inlastrevision = Attribute("""True if this sighting is currently in last
        imported POFile, otherwise false.""")

    pluralform = Attribute("The # of pluralform that we are sighting.")

    active = Attribute("If this is the latest translation we should use.")

    origin = Attribute("Where the sighting originally came from.")

    person = Attribute("The owner of this sighting.")


class IPOTranslation(Interface):
    """A translation in a PO file."""

    translation = Attribute("A translation string.")


class IPOExport(Interface):
    """Interface to export .po/.pot files"""

    def export(language):
        """Exports the .po file for the specific language"""
