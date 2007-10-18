# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Export module for gettext's .po file format.

You can read more about this file format from:
http://www.gnu.org/software/gettext/manual/html_chapter/gettext_10.html#PO-Files
"""

__metaclass__ = type

__all__ = [
    'GettextPOExporter'
    ]

import os
from cStringIO import StringIO
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatExporter, TranslationConstants, TranslationFileFormat)
from canonical.launchpad.translationformat import TranslationMessage
from canonical.launchpad.translationformat.translation_export import (
    ExportedTranslationFile, LaunchpadWriteTarFile)


def comments_text_representation(translation_message):
    r'''Return text representation of the comments.

    :param translation_message: An ITranslationMessage that will get comments
        exported.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'bar')
    >>> translation_message.flags = ('fuzzy', )
    >>> comments_text_representation(translation_message)
    u'#, fuzzy'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'a'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'b')
    >>> translation_message.comment = u' blah\n'
    >>> comments_text_representation(translation_message)
    u'# blah'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'%d foo'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'%d bar')
    >>> translation_message.flags = ('fuzzy', 'c-format')
    >>> comments_text_representation(translation_message)
    u'#, fuzzy, c-format'
    '''
    text = []
    # comment and source_comment always end in a newline, so
    # splitting by \n always results in an empty last element
    if translation_message.comment:
        for line in translation_message.comment.split('\n')[:-1]:
            text.append(u'#' + line)
    if not translation_message.is_obsolete:
        # Source comments are only exported if it's not an obsolete entry.
        if translation_message.source_comment:
            for line in translation_message.source_comment.split('\n')[:-1]:
                text.append(u'#. ' + line)
        if translation_message.file_references:
            for line in translation_message.file_references.split('\n'):
                text.append(u'#: ' + line)
    if translation_message.flags:
        flags = sorted(translation_message.flags)
        if 'fuzzy' in flags:
            # Force 'fuzzy' to be the first flag in the list like gettext's
            # tools do.
            flags.remove('fuzzy')
            flags.insert(0, 'fuzzy')
        text.append(u'#, %s' % u', '.join(flags))

    return u'\n'.join(text)

def wrap_text(text, prefix, wrap_width):
    r'''Return a list of strings with the given text wrapped to given width.

    We are not using textwrap module because the .po file format has some
    peculiarities like:

    msgid ""
    "a really long line."

    instead of:

    msgid "a really long"
    "line."

    with a wrapping width of 21.

    :param text: Unicode string to wrap.
    :param prefix: Unicode prefix to prepend to the given text before wrapping
        it.
    :param wrap_width: The width where the text should be wrapped.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdefghijkl'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap_width=20)
    u'msgid "abcdefghijkl"\nmsgstr "z"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdefghijklmnopqr'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap_width=20)
    u'msgid ""\n"abcdefghijklmnopqr"\nmsgstr "z"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdef hijklm'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap_width=20)
    u'msgid ""\n"abcdef hijklm"\nmsgstr "z"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdefghijklmnopqr st'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap_width=20)
    u'msgid ""\n"abcdefghijklmnopqr "\n"st"\nmsgstr "z"'

    newlines in the text interfere with wrapping.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abc\ndef'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap_width=20)
    u'msgid ""\n"abc\\n"\n"def"\nmsgstr "z"'

    but not when it's just a line that ends with a newline char
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abc\n'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'def\n')
    >>> export_translation_message(translation_message)
    u'msgid "abc\\n"\nmsgstr "def\\n"'

    It's time to test the wrapping with the '-' char:
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"WARNING: unsafe enclosing directory permissions on homedir"
    ...     u" `%s'\n")
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM,
    ...     u"WARNUNG: Unsichere Zugriffsrechte des umgebenden Verzeichnisses"
    ...         u" des Home-Verzeichnisses `%s'\n")
    >>> print export_translation_message(translation_message)
    msgid "WARNING: unsafe enclosing directory permissions on homedir `%s'\n"
    msgstr ""
    "WARNUNG: Unsichere Zugriffsrechte des umgebenden Verzeichnisses des Home-"
    "Verzeichnisses `%s'\n"

    When we changed the wrapping code, we got a bug with this string.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"The location and hierarchy of the Evolution contact folders has"
    ...         u" changed since Evolution 1.x.\n\n")
    >>> print export_translation_message(translation_message)
    msgid ""
    "The location and hierarchy of the Evolution contact folders has changed "
    "since Evolution 1.x.\n"
    "\n"
    msgstr ""

    When the wrapping size was exactly gotten past by in the middle of
    escape sequence like \" or \\, it got cut off in there, thus
    creating a broken PO message.  This is the test for bug #46156.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcde word\"1234567890abcdefghij")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcde "
    "word\"1234567890abcd"
    "efghij"
    msgstr ""

    Lets also make sure that the unconditional break is not occurring
    inside a single long word in the middle of the escape sequence
    like \" or \\:
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcdefghij\\klmno")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcdefghij"
    "\\klmno"
    msgstr ""

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcdefgh\\ijklmno")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcdefgh\\"
    "ijklmno"
    msgstr ""

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcdefg\\\\hijklmno")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcdefg\\"
    "\\hijklmno"
    msgstr ""

    For compatibility with msgcat -w, it also wraps on \\ properly.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"\\\\\\\\\\")
    >>> print export_translation_message(translation_message, wrap_width=5)
    msgid ""
    "\\\\"
    "\\\\"
    "\\"
    msgstr ""

    >>> print export_translation_message(translation_message, wrap_width=6)
    msgid ""
    "\\\\\\"
    "\\\\"
    msgstr ""
    '''
    def local_escape(text):
        ret = text.replace(u'\\', u'\\\\')
        ret = ret.replace(ur'"', ur'\"')
        ret = ret.replace(u'\t', u'\\t')
        return ret.replace(u'\n', u'\\n')

    # Quickly get escaped character byte widths using
    #   escaped_length.get(char, 1)
    escaped_length = {
        '\\': 2,
        '\"': 2,
        '\t': 2,
        '\n': 2}

    # What characters to wrap at
    wrap_at = [' ', '\t', '\n', '-', '\\']

    if wrap_width is None:
        raise AssertionError('wrap_width should not be None')
    wrapped_lines = [u'%s%s' % (prefix, u' ""')]
    if not text:
        return wrapped_lines
    if '\n' not in text[:-1]:
        # If there are no new-lines, or it's at the end of string.
        unwrapped_line = u'%s "%s"' % (prefix, local_escape(text))
        if len(unwrapped_line) <= wrap_width:
            return [unwrapped_line]
        del unwrapped_line
    paragraphs = text.split('\n')
    end = len(paragraphs) - 1
    for i, paragraph in enumerate(paragraphs):
        if i == end:
            if not paragraph:
                break
        else:
            paragraph += '\n'

        if len(local_escape(paragraph)) <= wrap_width:
            wrapped_line = [paragraph]
        else:
            line = u''
            escaped_line_len = 0
            new_block = u''
            escaped_new_block_len = 0
            wrapped_line = []
            for char in paragraph:
                escaped_char_len = escaped_length.get(char, 1)
                if (escaped_line_len + escaped_new_block_len
                    + escaped_char_len <= wrap_width):
                    if char in wrap_at:
                        line += u'%s%s' % (new_block, char)
                        escaped_line_len += (escaped_new_block_len
                                             + escaped_char_len)
                        new_block = u''
                        escaped_new_block_len = 0
                    else:
                        new_block += char
                        escaped_new_block_len += escaped_char_len
                else:
                    if escaped_line_len == 0:
                        # Word is too long to fit into single line,
                        # break it carefully, watching not to break
                        # in the middle of the escape
                        line = new_block
                        line_len = len(line)
                        escaped_line_len = escaped_new_block_len
                        while escaped_line_len > wrap_width:
                            escaped_line_len -= (
                                escaped_length.get(line[line_len-1], 1))
                            line_len -= 1
                        line = line[:line_len]
                        new_block = new_block[line_len:]
                        escaped_new_block_len -= escaped_line_len
                    wrapped_line.append(line)
                    line = u''
                    escaped_line_len = 0
                    new_block += char
                    escaped_new_block_len += escaped_char_len
            if line or new_block:
                wrapped_line.append(u'%s%s' % (line, new_block))
        for line in wrapped_line:
            wrapped_lines.append(u'"%s"' % (local_escape(line)))
    return wrapped_lines

def msgid_text_representation(translation_message, wrap_width):
    """Return text representation of the msgids.

    :param translation_message: An `ITranslationMessage` that will get its
        msgids exported.
    :param wrap_width: The width where the text should be wrapped.
    """
    text = []
    if translation_message.context is not None:
        text.extend(
            wrap_text(translation_message.context, u'msgctxt', wrap_width))
    text.extend(wrap_text(translation_message.msgid, u'msgid', wrap_width))
    if translation_message.msgid_plural:
        # This message has a plural form that we must export.
        text.extend(
            wrap_text(
                translation_message.msgid_plural, u'msgid_plural',
                wrap_width))
    if translation_message.is_obsolete:
        text = ['#~ ' + line for line in text]

    return u'\n'.join(text)

def translation_text_representation(translation_message, wrap_width):
    """Return text representation of the translations.

    :param translation_message: An `ITranslationMessage` that will get its
        translations exported.
    :param wrap_width: The width where the text should be wrapped.
    """
    text = []
    if translation_message.msgid_plural:
        # It's a message with plural forms.
        for i, translation in enumerate(translation_message.translations):
            text.extend(wrap_text(translation, u'msgstr[%s]' % i, wrap_width))

        if len(text) == 0:
            # We don't have any translation for it.
            text = [u'msgstr[0] ""', u'msgstr[1] ""']
    else:
        # It's a message without plural form.
        if translation_message.translations:
            translation = translation_message.translations[
                TranslationConstants.SINGULAR_FORM]
            text = wrap_text(translation, u'msgstr', wrap_width)
        else:
            text = [u'msgstr ""']

    if translation_message.is_obsolete:
        text = ['#~ ' + line for line in text]

    return u'\n'.join(text)

def export_translation_message(translation_message, wrap_width=77):
    r'''Return a text representing translation_message.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'bar')
    >>> export_translation_message(translation_message)
    u'msgid "foo"\nmsgstr "bar"'

    obsolete entries are prefixed with #~ .
    >>> translation_message.is_obsolete = True
    >>> export_translation_message(translation_message)
    u'#~ msgid "foo"\n#~ msgstr "bar"'

    also, obsolete entries preserve fuzzy strings.
    >>> translation_message.flags = ('fuzzy', )
    >>> export_translation_message(translation_message)
    u'#, fuzzy\n#~ msgid "foo"\n#~ msgstr "bar"'

    plural forms have its own way to represent translations.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo'
    >>> translation_message.msgid_plural = u'foos'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'bar')
    >>> translation_message.addTranslation(
    ...     TranslationConstants.PLURAL_FORM, u'bars')
    >>> translation_message.nplurals = 2
    >>> export_translation_message(translation_message)
    u'msgid "foo"\nmsgid_plural "foos"\nmsgstr[0] "bar"\nmsgstr[1] "bars"'

    backslashes are escaped (doubled) and quotes are backslashed.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo"bar\\baz'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message)
    u'msgid "foo\\"bar\\\\baz"\nmsgstr "z"'

    tabs are backslashed too, with standard C syntax.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'\tServer name: %s'
    >>> export_translation_message(translation_message)
    u'msgid "\\tServer name: %s"\nmsgstr ""'

    You can have context on messages.

    >>> translation_message = TranslationMessage()
    >>> translation_message.context = u'bla'
    >>> translation_message.msgid = u'foo'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'bar')
    >>> export_translation_message(translation_message)
    u'msgctxt "bla"\nmsgid "foo"\nmsgstr "bar"'
    '''
    return u'\n'.join([
        comments_text_representation(translation_message),
        msgid_text_representation(translation_message, wrap_width),
        translation_text_representation(translation_message, wrap_width),
        ]).strip()


class GettextPOExporter:
    """Support class to export Gettext .po files."""
    implements(ITranslationFormatExporter)

    def __init__(self, context=None):
        # 'context' is ignored because it's only required by the way the
        # exporters are instantiated but it isn't used by this class.
        self.format = TranslationFileFormat.PO
        self.supported_source_formats = [
            TranslationFileFormat.PO,
            TranslationFileFormat.KDEPO,
            TranslationFileFormat.XPI]

    def _getHeaderAsMessage(self, translation_file):
        """Return an `ITranslationMessage` with the header content."""
        header_translation_message = TranslationMessage()
        header_translation_message.addTranslation(
            TranslationConstants.SINGULAR_FORM,
            translation_file.header.getRawContent())
        header_translation_message.comment = (
            translation_file.header.comment)
        if translation_file.is_template:
            header_translation_message.flags.update(['fuzzy'])
        return header_translation_message

    def exportTranslationMessage(self, translation_message):
        """See `ITranslationFormatExporter`."""
        return export_translation_message(translation_message)

    def exportTranslationFiles(self, translation_file_list,
                               ignore_obsolete=False, force_utf8=False):
        """See `ITranslationFormatExporter`."""
        assert len(translation_file_list) > 0, (
            'Got an empty list of files to export!')

        exported_files = {}
        for translation_file in translation_file_list:
            dirname = os.path.dirname(translation_file.path)
            if dirname == '':
                # There is no directory in the path. Use
                # translation_domain as its directory.
                dirname = translation_file.translation_domain

            if translation_file.is_template:
                file_extension = 'pot'
                file_path = os.path.join(
                    dirname, '%s.%s' % (
                        translation_file.translation_domain,
                        file_extension))
            else:
                file_extension = 'po'
                file_path = os.path.join(
                    dirname, '%s-%s.%s' % (
                        translation_file.translation_domain,
                        translation_file.language_code,
                        file_extension))

            if force_utf8:
                translation_file.header.charset = 'UTF-8'
            header_translation_message = self._getHeaderAsMessage(
                translation_file)
            exported_header = self.exportTranslationMessage(
                header_translation_message)
            chunks = [exported_header.encode(translation_file.header.charset)]
            for message in translation_file.messages:
                if (message.is_obsolete and
                    (ignore_obsolete or len(message.translations) == 0)):
                    continue
                exported_message = self.exportTranslationMessage(message)
                try:
                    encoded_text = exported_message.encode(
                        translation_file.header.charset)
                except UnicodeEncodeError, error:
                    if translation_file.header.charset.upper() == 'UTF-8':
                        # It's already UTF-8, we cannot do anything.
                        raise UnicodeEncodeError(
                            '%s:\n%s' % (file_path, str(error)))

                    # This message cannot be represented in current encoding,
                    # change to UTF-8 and try again.
                    old_charset = translation_file.header.charset
                    translation_file.header.charset = 'UTF-8'
                    # We need to update the header too.
                    header_translation_message = self._getHeaderAsMessage(
                        translation_file)
                    exported_header = self.exportTranslationMessage(
                        header_translation_message)
                    chunks[0] = exported_header.encode(old_charset)
                    # Update already exported entries.
                    for index, chunk in enumerate(chunks):
                        chunks[index] = chunk.decode(
                            old_charset).encode('UTF-8')
                    encoded_text = exported_message.encode('UTF-8')

                chunks.append(encoded_text)

            exported_file_content = '\n\n'.join(chunks)

            # Gettext .po files are supposed to end with a new line.
            exported_file_content += '\n'

            exported_files[file_path] = exported_file_content

        if len(exported_files) == 1:
            # It's a single file export.
            exported_file = ExportedTranslationFile(
                StringIO(exported_file_content))
            exported_file.path = file_path
            # We use x-po for consistency with other .po editors like
            # GTranslator.
            exported_file.content_type = 'application/x-po'
            exported_file.file_extension = file_extension
        else:
            # There are multiple files being exported. We need to generate an
            # archive that include all them.
            exported_file = ExportedTranslationFile(
                LaunchpadWriteTarFile.files_to_stream(exported_files))
            # For tar.gz files, the standard content type is
            # application/x-gtar. You can see more info on
            # http://en.wikipedia.org/wiki/List_of_archive_formats
            exported_file.content_type = 'application/x-gtar'
            exported_file.file_extension = 'tar.gz'
            # By leaving path set to None, we let the caller decide.

        return exported_file
