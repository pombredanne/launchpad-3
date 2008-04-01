# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MozillaXpiImporter',
    ]

import cElementTree
import logging
import os
import re
from email.Utils import parseaddr
from StringIO import StringIO
from xml.parsers.xmlproc import dtdparser, xmldtd, utils
from zipfile import ZipFile
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatImporter, ITranslationHeaderData, TranslationConstants,
    TranslationFileFormat, TranslationFormatInvalidInputError,
    TranslationFormatSyntaxError)
from canonical.launchpad.translationformat.translation_common_format import (
    TranslationFileData, TranslationMessageData)
from canonical.librarian.interfaces import ILibrarianClient


class MozillaHeader:
    implements(ITranslationHeaderData)

    def __init__(self, header_content):
        self._raw_content = header_content
        self.is_fuzzy = False
        self.template_creation_date = None
        self.translation_revision_date = None
        self.language_team = None
        self.has_plural_forms = False
        self.number_plural_forms = 0
        self.plural_form_expression = None
        self.charset = 'UTF-8'
        self.launchpad_export_date = None
        self.comment = None

    def getRawContent(self):
        """See `ITranslationHeaderData`."""
        return self._raw_content

    def updateFromTemplateHeader(self, template_header):
        """See `ITranslationHeaderData`."""
        # Nothing to do for this format.
        return

    def getLastTranslator(self):
        """See `ITranslationHeaderData`."""
        name = None
        email = None
        parse = cElementTree.iterparse(StringIO(self._raw_content))
        for event, elem in parse:
            if elem.tag == "{http://www.mozilla.org/2004/em-rdf#}contributor":
                # This file would have more than one contributor, but
                # we are only getting latest one.
                name, email = parseaddr(elem.text)

        return name, email

    def setLastTranslator(self, email, name=None):
        """Set last translator information.

        :param email: A string with the email address for last translator.
        :param name: The name for the last translator or None.
        """
        # Nothing to do for this format.
        return


class MozillaZipFile:
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It handles embedded jar, dtd and properties files.
    """

    def __init__(self, filename, content):
        self.filename = filename
        self.header = None
        self.messages = []
        self.last_translator = None

        zip = ZipFile(StringIO(content), 'r')
        for entry in sorted(zip.namelist()):
            if entry.endswith('.properties'):
                data = zip.read(entry)
                pf = PropertyFile(filename=entry, content=data)
                self.extend(pf.messages)
            elif entry.endswith('.dtd'):
                data = zip.read(entry)
                dtdf = DtdFile(filename=entry, content=data)
                self.extend(dtdf.messages)
            elif entry.endswith('.jar'):
                data = zip.read(entry)
                jarf = MozillaZipFile(filename=entry, content=data)
                self.extend(jarf.messages)
            elif entry == 'install.rdf':
                data = zip.read(entry)
                self.header = MozillaHeader(data)
            else:
                # Ignore this file, we don't need to do anything with it.
                continue

    def _updateMessageFileReferences(self, message):
        """Update message's file_references with full path."""
        if self.filename is not None:
            # Include self.filename to this entry's file reference.
            if self.filename.endswith('.jar'):
                filename = '%s!' % self.filename
            else:
                filename = self.filename
            message.file_references_list = [
                os.path.join(filename, file_reference)
                for file_reference in message.file_references_list]
        # Fill file_references field based on the list of files we
        # found.
        message.file_references = ', '.join(
            message.file_references_list)

    def _isKeyShortcutMessage(self, message):
        """Whether the message represents a key shortcut."""
        return (
            self.filename is not None and
            self.filename.startswith('en-US.xpi') and
            message.translations and (
                message.msgid_singular.endswith('.accesskey') or
                message.msgid_singular.endswith('.commandkey') or
                message.msgid_singular.endswith('.key')))

    def extend(self, newdata):
        """Append 'newdata' messages to self.messages."""
        for message in newdata:
            self._updateMessageFileReferences(message)

            # Special case accesskeys and commandkeys:
            # these are single letter messages, lets display
            # the value as a source comment.
            if self._isKeyShortcutMessage(message):
                comment = (
                    u"Select the shortcut key that you want to use. Please,\n"
                    u"don't change this translation if you are not really\n"
                    u"sure about what you are doing.\n")
                if message.source_comment:
                    message.source_comment += comment
                else:
                    message.source_comment = comment
            self.messages.append(message)


class MozillaDtdConsumer (xmldtd.WFCDTD):
    """Mozilla DTD translatable message parser.

    msgids are stored as entities. This class extracts it along
    with translations, comments and source references.
    """
    def __init__(self, parser, filename, messages):
        self.started = False
        self.last_comment = None
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
        message.source_comment = self.last_comment
        self.messages.append(message)
        self.started += 1
        self.last_comment = None


class DtdFile:
    """Class for reading translatable messages from a .dtd file.

    It uses DTDParser which fills self.messages with parsed messages.
    """
    def __init__(self, filename, content):
        self.messages = []
        self.filename = filename

        # .dtd files are supposed to be using UTF-8 encoding, if the file is
        # using another encoding, it's against the standard so we reject it
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise TranslationFormatInvalidInputError, (
                'Content is not valid UTF-8 text')

        parser = dtdparser.DTDParser()
        parser.set_error_handler(utils.ErrorCounter())
        dtd = MozillaDtdConsumer(parser, filename, self.messages)
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

    def __init__(self, filename, content):
        """Constructs a dictionary from a .properties file.

        :arg filename: The file name where the content came from.
        :arg content: The file content that we want to parse.
        """
        self.filename = filename
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
                    # commnet. Ignore it because main en-US.xpi catalog from
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


def find_end_of_common_prefix(strings):
    """Find index of first character (if any) where strings differ.

    :param strings: a list of strings.
    :return: index directly after that of last character that is identical
        across all strings.
    """
    min_length = min([len(string) for string in strings])
    if len(strings) <= 1:
        return min_length

    head = strings[0]
    tail = strings[1:]
    for index in xrange(min_length):
        base_char = head[index]
        for string in tail:
            if string[index] != base_char:
                return index

    # Scan backwards for a slash, and break there.  Things are a bit prettier
    # if we avoid breaking in the middle of a directory name.
    while min_length > 0 and head[min_length-1] != '/':
        min_length -= 1

    return min_length


def normalize_file_references(filename):
    """Strip trailing crud off a file reference string.

    A file reference string consists of comma-separated file paths, each
    followed by an optional line number and a repetition of the msgid:
    "foo/bar:123(splat)" or "foo/bar(splat)".  This function whittles
    either example down to "foo/bar".
    """
    return re.sub('(:[0-9]+)?\([^)]+\)', '', filename)


def disambiguate(messages):
    """Resolve possible duplicate message ids in `messages`.

    Where messages are identical and occur in the exact same file(s), one
    copy is removed.  Context information is added to resolve clashes between
    identical message identifiers in different files inside the XPI.

    :param messages: a list of `TranslationMessageData` objects representing
        the full set of messages in an XPI.
    :return: a disambiguated list of `TranslationMessageData` objects.
    """
    result = []
    # Messages we've already seen.  Maps msgid_singular to a dict that in turn
    # maps file_references to a previously processed TranslationMessageData.
    seen = {}

    # Sets of message ids that occur in multiple files, that need
    # disambiguation by context.
    clashes = set()

    for message in messages:
        references = normalize_file_references(message.file_references)
        if message.msgid_singular in seen:
            similar_messages = seen[message.msgid_singular]
            if references in similar_messages:
                # This is a completely senseless duplication, within the same
                # file.  Ignore it.
                logging.info(
                    "Duplicate message ID '%s' in %s."
                    % (message.msgid_singular, message.file_references))
            else:
                # There is already a message with the same identifier in a
                # different file.  Accept it as a separate message.
                similar_messages[references] = message
                clashes.add(message.msgid_singular)
                result.append(message)
        else:
            # New message.  Store it.
            seen[message.msgid_singular] = {references: message}
            result.append(message)

    # Go over messages with clashing identifiers, and provide context.
    for msgid in clashes:
        cousins = seen[msgid]
        filenames = set()
        for message in cousins.itervalues():
            filenames.update(message.file_references_list)
        # Context is based on the originating file's path.  We can't use the
        # whole path, because it may contain language codes.
        # Instead, eliminate common prefixes from the file_references strings
        # for any set of clashing messages, and use the rest of those strings
        # as context strings.
        # XXX: JeroenVermeulen 2008-03-20 spec=xpi-manifest-parsing: Context
        # should really be based on chrome path, and be set for every string.
        # To figure out proper chrome paths we need to be able to parse
        # manifest files first.
        context_start = find_end_of_common_prefix(list(filenames))
        for message in cousins.itervalues():
            context_components = []

            for filename in message.file_references_list:
                component = normalize_file_references(
                    filename[context_start:])
                context_components.append(component)

            context = ','.join(context_components)
            if len(context) > 0:
                message.context = context

    return result


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

        parser = MozillaZipFile(self.basepath, self.content.read())

        self._translation_file.header = parser.header
        self._translation_file.messages = disambiguate(parser.messages)

        return self._translation_file

    def getHeaderFromString(self, header_string):
        """See `ITranslationFormatImporter`."""
        return MozillaHeader(header_string)

