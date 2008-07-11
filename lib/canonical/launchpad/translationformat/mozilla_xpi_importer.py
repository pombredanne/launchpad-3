# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MozillaXpiImporter',
    ]

import textwrap
from os.path import splitext
from StringIO import StringIO
from old_xmlplus.parsers.xmlproc import dtdparser, xmldtd, utils
from zipfile import ZipFile
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatImporter, TranslationConstants, TranslationFileFormat,
    TranslationFormatInvalidInputError, TranslationFormatSyntaxError)
from canonical.launchpad.translationformat.translation_common_format import (
    TranslationFileData, TranslationMessageData)
from canonical.launchpad.translationformat.xpi_header import XpiHeader
from canonical.launchpad.translationformat.xpi_manifest import (
    make_jarpath, XpiManifest)
from canonical.librarian.interfaces import ILibrarianClient


def get_file_suffix(path_in_zip):
    """Given a full file path inside a zip archive, return filename suffix.

    :param path_in_zip: Full file path inside a zip archive, e.g.
        "foo/bar.dtd".
    :return: Filename suffix, or empty string if none found.  For example,
        "foo/bar.dtd" results in ".dtd".
    """
    root, ext = splitext(path_in_zip)
    return ext


def add_source_comment(message, comment):
    """Add the given comment inside message.source_comment."""
    if message.source_comment:
        message.source_comment += comment
    else:
        message.source_comment = comment

    if not message.source_comment.endswith('\n'):
        message.source_comment += '\n'


class MozillaZipFile:
    """Traversal of an XPI file, or a jar file inside an XPI file.

    To traverse and process an XPI file, derive a class from this one
    and replace any hooks that you may need.

    If an XPI manifest is provided, traversal will be restricted to
    directories it lists as containing localizable resources.
    """

    def __init__(self, filename, content, xpi_path='', manifest=None):
        """Open zip (or XPI, or jar) file and scan its contents.

        :param filename: Name of this zip (XPI/jar) file.
        :param content: The data making up this zip file.
        :param xpi_path: Full path of this file inside the XPI archive.
            Leave blank for the XPI file itself.
        :param manifest: `XpiManifest` representing the XPI archive's
            manifest file, if any.
        """
        self.filename = filename
        self.header = None
        self.last_translator = None
        self.manifest = manifest
        self.archive = ZipFile(StringIO(content), 'r')

        # Strip trailing newline to avoid doubling it.
        if xpi_path.endswith('/'):
            xpi_path = xpi_path[:-1]

        self._begin()

        # Process zipped files.  Sort by path to keep ordering deterministic.
        # Ordering matters in sequence numbering (which in turn shows up in
        # the UI), but also for consistency in duplicates resolution and for
        # automated testing.
        for entry in sorted(self.archive.namelist()):
            self._processEntry(entry, xpi_path)

        self._complete()

    def _begin(self):
        """Overridable hook: pre-traversal actions."""

    def _process(self, entry, locale_code, xpi_path, chrome_path):
        """Overridable hook: process a file entry.

        Called only for files that may be localizable.  If there is a
        manifest, that means the file must be in a location (or subtree)
        named by a "locale" entry.

        :param entry: Full name of file inside this zip archive,
            including path relative to the archive's root.
        :param locale_code: Code for locale this file belongs to, e.g.
            "en-US".
        :param xpi_path: Full path of this file inside the XPI archive,
            e.g. "jar:locale/en-US.jar!/data/messages.dtd".
        :param chrome_path: File's chrome path.  This is a kind of
            "normalized" path used in XPI to describe a virtual
            directory hierarchy.  The zip archive's actual layout (which
            the XPI paths describe) may be different.
        """

    def _descend(self, entry, content, xpi_path):
        """Overridable hook: descend into jar file.

        Default implementation recurses by creating a new instance of
        the same `MozillaZipFile` implementation.

        Any value returned by this method will be passed to a matching
        invocation of `_emerge`, which backtracks the recursion.

        :param entry: Full name of jar file inside this zip archive.
        :param content: Bytes of this jar file.
        :param xpi_path: Base XPI path for jar file.  Prefix this to an
            entry in the jar file to get the entry's full XPI path.

        :return: In the default implementation, an instance of the same
            class as self, but one that traverses the jar file.
        """
        return self.__class__(filename=entry, xpi_path=xpi_path,
            content=content, manifest=self.manifest)

    def _emerge(self, descend_result):
        """Overridable hook: return from descent into jar file.

        :param descend_result: return value from matching `_descend`().
        """

    def _complete(self):
        """Overridable hook: post-traveral actions."""

    def _processEntry(self, entry, xpi_path):
        """Read one zip archive entry, figure out what to do with it."""
        is_jar = entry.endswith('.jar')

        if is_jar:
            jarpath = make_jarpath(xpi_path, entry)
            if not self.manifest or self.manifest.containsLocales(jarpath):
                # If this is a jar file that may contain localizable
                # resources, don't process it in the normal way; descend into
                # it.
                content = self.archive.read(entry)
                self._emerge(self._descend(entry, content, jarpath))
                return

        xpi_path = "%s/%s" % (xpi_path, entry)
        if self.manifest is None:
            # No manifest, so we don't have chrome paths.  Process
            # everything just to be sure.
            chrome_path = None
            locale_code = None
        else:
            chrome_path, locale_code = self.manifest.getChromePathAndLocale(
                xpi_path)
            if chrome_path is None:
                # Not in a directory containing localizable resources.
                return

        self._process(entry, locale_code, xpi_path, chrome_path)


class MozillaZipParser(MozillaZipFile):
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It handles embedded dtd and properties files.
    """

    messages = None

    def _begin(self):
        """Overridable hook for `MozillaZipFile`."""
        self.messages = []

    def _complete(self):
        """Overridable hook for `MozillaZipFile`."""
        # Eliminate duplicate messages.
        seen_messages = set()
        deletions = []
        for index, message in enumerate(self.messages):
            identifier = (message.msgid_singular, message.context)
            if identifier in seen_messages:
                # This message is a duplicate.  Mark it for removal.
                deletions.append(index)
            else:
                seen_messages.add(identifier)
        for index in reversed(deletions):
            del self.messages[index]

        for message in self.messages:
            message.file_references = ', '.join(message.file_references_list)

    def _process(self, entry, locale_code, xpi_path, chrome_path):
        """Overridable hook for `MozillaZipFile`.
        
        This implementation is only interested in DTD and properties
        files.
        """
        suffix = get_file_suffix(entry)
        if suffix == '.dtd':
            parser = DtdFile
        elif suffix == '.properties':
            parser = PropertyFile
        else:
            # We're not interested in other file types here.
            return

        # Parse file, subsume its messages.
        content = self.archive.read(entry)
        parsed_file = parser(
            filename=xpi_path, chrome_path=chrome_path, content=content)
        if parsed_file is not None:
            self.extend(parsed_file.messages)

    def _emerge(self, descend_result):
        """Overridable hook for `MozillaZipFile`.

        This implementation complements `self.messages` with those found in
        the jar file we just parsed.
        """
        self.extend(descend_result.messages)

    def _isCommandKeyMessage(self, message):
        """Whether the message represents a command key shortcut."""
        return (
            self.filename is not None and
            self.filename.startswith('en-US.xpi') and
            message.translations and (
                message.msgid_singular.endswith('.commandkey') or
                message.msgid_singular.endswith('.key')))

    def _isAccessKeyMessage(self, message):
        """Whether the message represents an access key shortcut."""
        return (
            self.filename is not None and
            self.filename.startswith('en-US.xpi') and
            message.translations and (
                message.msgid_singular.endswith('.accesskey')))

    def extend(self, newdata):
        """Complement `self.messages` with messages found in contained file.


        """
        for message in newdata:
            # Special case accesskeys and commandkeys:
            # these are single letter messages, lets display
            # the value as a source comment.
            if self._isCommandKeyMessage(message):
                comment = u'\n'.join(textwrap.wrap(
                    u"Select the shortcut key that you want to use. It should"
                    u" be translated, but often shortcut keys (for example"
                    u" Ctrl + KEY) are not changed from the original. If a"
                    u" translation already exists, please don't change it if"
                    u" you are not sure about it. Please find the context of"
                    u" the key from the end of the 'Located in' text below."))
                add_source_comment(message, comment)
            elif self._isAccessKeyMessage(message):
                comment = u'\n'.join(textwrap.wrap(
                    u"Select the access key that you want to use. These have"
                    u" to be translated in a way that the selected"
                    u" character is present in the translated string of the"
                    u" label being referred to, for example 'i' in 'Edit'"
                    u" menu item in English. If a translation already"
                    u" exists, please don't change it if you are not sure"
                    u" about it. Please find the context of the key from the"
                    u" end of the 'Located in' text below."))
                add_source_comment(message, comment)
            self.messages.append(message)


class MozillaDtdConsumer (xmldtd.WFCDTD):
    """Mozilla DTD translatable message parser.

    msgids are stored as entities. This class extracts it along
    with translations, comments and source references.
    """
    def __init__(self, parser, filename, chrome_path, messages):
        self.started = False
        self.last_comment = None
        self.chrome_path = chrome_path
        self.messages = messages
        self.filename = filename
        xmldtd.WFCDTD.__init__(self, parser)

    def dtd_start(self):
        """See `xmldtd.WFCDTD`."""
        self.started = True

    def dtd_end(self):
        """See `xmldtd.WFCDTD`."""
        self.started = False

    def handle_comment(self, contents):
        """See `xmldtd.WFCDTD`."""
        if not self.started:
            return

        if self.last_comment is not None:
            self.last_comment += contents
        elif len(contents) > 0:
            self.last_comment = contents

        if self.last_comment and not self.last_comment.endswith('\n'):
            # Comments must end always with a new line.
            self.last_comment += '\n'

    def new_general_entity(self, name, value):
        """See `xmldtd.WFCDTD`."""
        if not self.started:
            return

        message = TranslationMessageData()
        message.msgid_singular = name
        # CarlosPerelloMarin 20070326: xmldtd parser does an inline
        # parsing which means that the content is all in a single line so we
        # don't have a way to show the line number with the source reference.
        message.file_references_list = ["%s(%s)" % (self.filename, name)]
        message.addTranslation(TranslationConstants.SINGULAR_FORM, value)
        message.singular_text = value
        message.context = self.chrome_path
        message.source_comment = self.last_comment
        self.messages.append(message)
        self.started += 1
        self.last_comment = None


class DtdFile:
    """Class for reading translatable messages from a .dtd file.

    It uses DTDParser which fills self.messages with parsed messages.
    """
    def __init__(self, filename, chrome_path, content):
        self.messages = []
        self.filename = filename
        self.chrome_path = chrome_path

        # .dtd files are supposed to be using UTF-8 encoding, if the file is
        # using another encoding, it's against the standard so we reject it
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise TranslationFormatInvalidInputError, (
                'Content is not valid UTF-8 text')

        parser = dtdparser.DTDParser()
        parser.set_error_handler(utils.ErrorCounter())
        dtd = MozillaDtdConsumer(parser, filename, chrome_path, self.messages)
        parser.set_dtd_consumer(dtd)
        parser.parse_string(content)


def valid_property_msgid(msgid):
    """Whether the given msgid follows the restrictions to be valid.

    Checks done are:
        - It cannot have white spaces.
    """
    return u' ' not in msgid


class PropertyFile:
    """Class for reading translatable messages from a .properties file.

    The file format is described at:
    http://www.mozilla.org/projects/l10n/mlp_chrome.html#text
    """

    license_block_text = u'END LICENSE BLOCK'

    def __init__(self, filename, chrome_path, content):
        """Constructs a dictionary from a .properties file.

        :arg filename: The file name where the content came from.
        :arg content: The file content that we want to parse.
        """
        self.filename = filename
        self.chrome_path = chrome_path
        self.messages = []

        # Parse the content.
        self.parse(content)

    def parse(self, content):
        """Parse given content as a property file.

        Once the parse is done, self.messages has a list of the available
        `ITranslationMessageData`s.
        """

        # .properties files are supposed to be unicode-escaped, but we know
        # that there are some .xpi language packs that instead, use UTF-8.
        # That's against the specification, but Mozilla applications accept
        # it anyway, so we try to support it too.
        # To do this support, we read the text as being in UTF-8
        # because unicode-escaped looks like ASCII files.
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise TranslationFormatInvalidInputError, (
                'Content is not valid unicode-escaped text')

        line_num = 0
        is_multi_line_comment = False
        last_comment = None
        last_comment_line_num = 0
        ignore_comment = False
        is_message = False
        translation = u''
        for line in content.splitlines():
            # Now, to "normalize" all to the same encoding, we encode to
            # unicode-escape first, and then decode it to unicode
            # XXX: Danilo 2006-08-01: we _might_ get performance
            # improvements if we reimplement this to work directly,
            # though, it will be hard to beat C-based de/encoder.
            # This call unescapes everything so we don't need to care about
            # quotes escaping.
            line = line.encode('unicode_escape').decode('unicode_escape')

            line_num += 1
            if not is_multi_line_comment:
                # Remove any white space before the useful data, like
                # ' # foo'.
                line = line.lstrip()
                if line.startswith(u'#'):
                    # It's a whole line comment.
                    ignore_comment = False
                    line = line[1:].strip()
                    if last_comment:
                        last_comment += line
                    elif len(line) > 0:
                        last_comment = line

                    if last_comment and not last_comment.endswith('\n'):
                        # Comments must end always with a new line.
                        last_comment += '\n'

                    last_comment_line_num = line_num
                    continue
                elif len(line) == 0:
                    # It's an empty line. Reset any previous comment we have.
                    last_comment = None
                    last_comment_line_num = 0
                    ignore_comment = False
            while line:
                if is_multi_line_comment:
                    if line.startswith(u'*/'):
                        # The comment ended, we jump the closing tag and
                        # continue with the parsing.
                        line = line[2:]
                        is_multi_line_comment = False
                        last_comment_line_num = line_num
                        if ignore_comment:
                            last_comment = None
                            ignore_comment = False

                        # Comments must end always with a new line.
                        last_comment += '\n'
                    elif line.startswith(self.license_block_text):
                        # It's a comment with a license notice, this
                        # comment can be ignored.
                        ignore_comment = True
                        # Jump the whole tag
                        line = line[len(self.license_block_text):]
                    else:
                        # Store the character.
                        if last_comment is None:
                            last_comment = line[0]
                        elif last_comment_line_num == line_num:
                            last_comment += line[0]
                        else:
                            last_comment = u'%s\n%s' % (last_comment, line[0])
                            last_comment_line_num = line_num
                        # Jump the processed char.
                        line = line[1:]
                    continue
                elif line.startswith(u'//'):
                    # It's an 'end of the line comment'
                    last_comment = '%s\n' % line[2:].strip()
                    last_comment_line_num = line_num
                    # Jump to next line
                    break
                elif line.startswith(u'/*'):
                    # It's a multi line comment
                    is_multi_line_comment = True
                    ignore_comment = False
                    last_comment_line_num = line_num
                    # Jump the comment starting tag
                    line = line[2:]
                    continue
                elif is_message:
                    # Store the char and continue.
                    translation += line[0]
                    line = line[1:]
                    continue
                elif u'=' in line:
                    # Looks like a message string.
                    (key, value) = line.split('=', 1)
                    # Remove leading and trailing white spaces.
                    key = key.strip()

                    if valid_property_msgid(key):
                        is_message = True
                        # Jump the msgid, control chars and leading white
                        # space.
                        line = value.lstrip()
                        continue
                    else:
                        raise TranslationFormatSyntaxError(
                            line_number=line_num,
                            message=u"invalid msgid: '%s'" % key)
                else:
                    # Got a line that is not a valid message nor a valid
                    # comment. Ignore it because main en-US.xpi catalog from
                    # Firefox has such line/error. We follow the 'be strict
                    # with what you export, be permisive with what you import'
                    # policy.
                    break
            if is_message:
                # We just parsed a message, so we need to add it to the list
                # of messages.
                if ignore_comment or last_comment_line_num < line_num - 1:
                    # We must ignore the comment or either the comment is not
                    # the last thing before this message or is not in the same
                    # line as this message.
                    last_comment = None
                    ignore_comment = False

                message = TranslationMessageData()
                message.msgid_singular = key
                message.context = self.chrome_path
                message.file_references_list = [
                    "%s:%d(%s)" % (self.filename, line_num, key)]
                value = translation.strip()
                message.addTranslation(
                    TranslationConstants.SINGULAR_FORM, value)
                message.singular_text = value
                message.source_comment = last_comment
                self.messages.append(message)

                # Reset status vars.
                last_comment = None
                last_comment_line_num = 0
                is_message = False
                translation = u''


class MozillaXpiImporter:
    """Support class to import Mozilla .xpi files."""

    implements(ITranslationFormatImporter)

    def __init__(self):
        self.basepath = None
        self.productseries = None
        self.distroseries = None
        self.sourcepackagename = None
        self.is_published = False
        self.content = None
        self._translation_file = None

    def getFormat(self, file_contents):
        """See `ITranslationFormatImporter`."""
        return TranslationFileFormat.XPI

    priority = 0

    # using "application/x-xpinstall" would trigger installation in
    # firefox.
    content_type = 'application/zip'

    file_extensions = ['.xpi']
    template_suffix = 'en-US.xpi'

    uses_source_string_msgids = True

    def _extract_manifest(self, archive, contained_files):
        """Extract manifest file from `ZipFile`."""
        manifest_names = ['chrome.manifest', 'en-US.manifest']
        for filename in manifest_names:
            if filename in contained_files:
                return XpiManifest(archive.read(filename))

        return None

    def _extract_install_rdf(self, archive, contained_files):
        if 'install.rdf' not in contained_files:
            raise TranslationFormatInvalidInputError("No install.rdf found")
        return XpiHeader(archive.read('install.rdf'))

    def parse(self, translation_import_queue_entry):
        """See `ITranslationFormatImporter`."""
        self._translation_file = TranslationFileData()
        self.basepath = translation_import_queue_entry.path
        self.productseries = translation_import_queue_entry.productseries
        self.distroseries = translation_import_queue_entry.distroseries
        self.sourcepackagename = (
            translation_import_queue_entry.sourcepackagename)
        self.is_published = translation_import_queue_entry.is_published

        librarian_client = getUtility(ILibrarianClient)
        self.content = librarian_client.getFileByAlias(
            translation_import_queue_entry.content.id)

        # Before going into MozillaZipFile, extract metadata.
        content = self.content.read()
        archive = ZipFile(StringIO(content), 'r')
        contained_files = set(archive.namelist())
        manifest = self._extract_manifest(archive, contained_files)
        header = self._extract_install_rdf(archive, contained_files)

        archive = None

        parser = MozillaZipParser(self.basepath, content, manifest=manifest)

        self._translation_file.header = header
        self._translation_file.messages = parser.messages

        return self._translation_file

    def getHeaderFromString(self, header_string):
        """See `ITranslationFormatImporter`."""
        return XpiHeader(header_string)

