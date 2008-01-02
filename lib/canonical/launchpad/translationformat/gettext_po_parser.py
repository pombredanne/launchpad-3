# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
#
# Contains code from msgfmt.py (available from python source code),
#     written by Martin v. Loewis <loewis@informatik.hu-berlin.de>
#     changed by Christian 'Tiran' Heimes <ch@comlounge.net>

__metaclass__ = type

__all__ = [
    'POHeader',
    'POParser',
    'plural_form_mapper',
    ]

import gettext
import datetime
import re
import codecs
import logging
import pytz
from email.Utils import parseaddr
from zope.interface import implements
from zope.app import datetimeutils

from canonical.launchpad.interfaces import (
    ITranslationHeaderData, TranslationConstants,
    TranslationFormatInvalidInputError, TranslationFormatSyntaxError)
from canonical.launchpad.translationformat.translation_common_format import (
    TranslationFileData, TranslationMessageData)
from canonical.launchpad.versioninfo import revno

class BadPluralExpression(Exception):
    pass

def make_plural_function(expression):
    """Create a lambda function for C-like plural expression."""
    # Largest expressions we could find in practice were 113 characters
    # long.  500 is a reasonable value which is still 4 times more than
    # that, yet not incredibly long.
    if expression is None or len(expression) > 500:
        raise BadPluralExpression

    # Guard against '**' usage: it's not useful in evaluating
    # plural forms, yet can be used to introduce a DoS.
    if expression.find('**') != -1:
        raise BadPluralExpression

    # We allow digits, whitespace [ \t], parentheses, "n", and operators
    # as allowed by GNU gettext implementation as well.
    if not re.match('^[0-9 \t()n|&?:!=<>+%*/-]*$', expression):
        raise BadPluralExpression

    try:
        function = gettext.c2py(expression)
    except (ValueError, SyntaxError):
        raise BadPluralExpression

    return function

def plural_form_mapper(first_expression, second_expression):
    """Maps plural forms from one plural formula to the other.

    Returns a dict indexed by indices in the `first_formula`
    pointing to corresponding indices in the `second_formula`.
    """
    identity_map = {0:0, 1:1, 2:2, 3:3}
    try:
        first_func = make_plural_function(first_expression)
        second_func = make_plural_function(second_expression)
    except BadPluralExpression:
        return identity_map

    # Can we create a mapping from one expression to the other?
    mapping = {}
    for n in range(1000):
        try:
            first_form = first_func(n)
            second_form = second_func(n)
        except (ArithmeticError, TypeError):
            return identity_map

        # Is either result out of range?
        if first_form not in [0,1,2,3] or second_form not in [0,1,2,3]:
            return identity_map

        if first_form in mapping:
            if mapping[first_form] != second_form:
                return identity_map
        else:
            mapping[first_form] = second_form

    # The mapping must be an isomorphism.
    if sorted(mapping.keys()) != sorted(mapping.values()):
        return identity_map

    # Fill in the remaining inputs from the identity map:
    result = identity_map.copy()
    result.update(mapping)
    return result

class POSyntaxWarning(Warning):
    """ Syntax warning in a po file """

    def __init__(self, lno=0, msg=None):
        self.lno = lno
        self.msg = msg

    def __str__(self):
        if self.msg:
            return self.msg
        elif self.lno is None:
            return 'PO file: syntax warning on unknown line'
        else:
            return 'PO file: syntax warning on entry at line %d' % self.lno


def parse_charset(string_to_parse, is_escaped=True):
    """Return charset used in the given string_to_parse."""
    # Scan for the charset in the same way that gettext does.
    default_charset = 'UTF-8'
    pattern = r'charset=([^\s]+)'
    if is_escaped:
        pattern = r'charset=([^\s]+)\\n'

    # Default to UTF-8 if the header still has the default value or
    # is unknown.
    charset = default_charset
    match = re.search(pattern, string_to_parse)
    if match is not None and match.group(1) != 'CHARSET':
        charset = match.group(1).strip()
        try:
            codecs.getencoder(charset)
        except LookupError:
            # The given codec is not valid, let's fallback to UTF-8.
            charset = default_charset

    return charset


def get_header_dictionary(raw_header, handled_keys_order):
    """Return dictionary with all keys in raw_header.

    :param raw_header: string representing the header in native format.
    :param handled_keys_order: list of header keys in the order they must
        appear on export time.
    :return: dictionary with all key/values in raw_header.
    """
    header_dictionary = {}
    for line in raw_header.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            field, value = line.split(':', 1)
        except ValueError:
            logging.warning(POSyntaxWarning(
                msg='PO file header entry has a bad entry: %s' % line))
            continue

        # Store in lower case the entries we know about so we are sure
        # that we update entries even when it's not using the right
        # character case.
        if field.lower() in handled_keys_order:
            field = field.lower()

        header_dictionary[field] = value.strip()

    return header_dictionary


class POHeader:
    """See `ITranslationHeaderData`."""
    implements(ITranslationHeaderData)

    # Set of known keys in the .po header.
    _handled_keys_mapping = {
        'project-id-version': 'Project-Id-Version',
        'report-msgid-bugs-to': 'Report-Msgid-Bugs-To',
        'pot-creation-date': 'POT-Creation-Date',
        'po-revision-date': 'PO-Revision-Date',
        'last-translator': 'Last-Translator',
        'language-team': 'Language-Team',
        'mime-version': 'MIME-Version',
        'content-type': 'Content-Type',
        'content-transfer-encoding': 'Content-Transfer-Encoding',
        'plural-forms': 'Plural-Forms',
        'x-launchpad-export-date': 'X-Launchpad-Export-Date',
        'x-rosetta-export-date': 'X-Rosetta-Export-Date',
        'x-generator': 'X-Generator',
        }

    _handled_keys_order = [
        'project-id-version', 'report-msgid-bugs-to', 'pot-creation-date',
        'po-revision-date', 'last-translator', 'language-team',
        'mime-version', 'content-type', 'content-transfer-encoding',
        'plural-forms', 'x-launchpad-export-date', 'x-rosetta-export-date',
        'x-generator'
        ]

    _strftime_text = '%F %R%z'

    def __init__(self, header_content, comment=None):
        self._raw_header = header_content
        self.is_fuzzy = False
        UTC = pytz.timezone('UTC')
        self.template_creation_date = datetime.datetime.now(UTC)
        self.translation_revision_date = datetime.datetime.now(UTC)
        self._last_translator = 'FULL NAME <EMAIL@ADDRESS>'
        self.language_team = 'LANGUAGE <LL@li.org>'
        self.has_plural_forms = False
        self.number_plural_forms = None
        self.plural_form_expression = None
        self.launchpad_export_date = None

        # First thing to do is to get the charset used to decode correctly the
        # header content.
        self.charset = parse_charset(self._raw_header, is_escaped=False)

        # Decode comment using the declared charset.
        self.comment = self._decode(comment)
        # And the same with the raw content.
        self._raw_header = self._decode(self._raw_header)

        # Parse the header in a dictionary so it's easy for us to export it
        # with updates later.
        self._header_dictionary = get_header_dictionary(
            self._raw_header, self._handled_keys_order)
        self._parseHeaderFields()

    def _decode(self, text):
        if text is None or isinstance(text, unicode):
            # There is noo need to do anything.
            return text
        charset = self.charset
        try:
            text = unicode(text, charset)
        except UnicodeError:
            logging.info(POSyntaxWarning(
                msg='string is not in declared charset %r' % charset
                ))
            text = unicode(text, charset, 'replace')
        except LookupError:
            raise TranslationFormatInvalidInputError(
                message='Unknown charset %r' % charset)

        return text

    def _parseHeaderFields(self):
        """Return plural form values based on the parsed header."""
        for key, value in self._header_dictionary.iteritems():
            if key == 'plural-forms':
                parts = parse_assignments(value)
                if parts.get('nplurals') != 'INTEGER':
                    # We found something different than gettext's default
                    # value.
                    nplurals = parts.get('nplurals')
                    try:
                        self.number_plural_forms = int(nplurals)
                    except TypeError:
                        # There are some po files with bad headers that have a
                        # non numeric value here and sometimes an empty value.
                        # In that case, set the default value.
                        logging.info(
                            POSyntaxWarning(
                                msg=("The plural form header has an unknown"
                                    " error. Using the default value...")))
                        self.number_plural_forms = 1
                    self.plural_form_expression = parts.get('plural', '0')
            elif key == 'pot-creation-date':
                try:
                    self.template_creation_date = (
                        datetimeutils.parseDatetimetz(value))
                except datetimeutils.DateTimeError:
                    # We couldn't parse it, leave current default value.
                    pass
            elif key == 'po-revision-date':
                try:
                    self.translation_revision_date = (
                        datetimeutils.parseDatetimetz(value))
                except datetimeutils.DateTimeError:
                    # We couldn't parse it.
                    self.translation_revision_date = None
            elif key == 'last-translator':
                self._last_translator = value
            elif key == 'language-team':
                self.language_team = value
            elif key in ('x-launchpad-export-date', 'x-rosetta-export-date'):
                # The key we use right now to note the export date is
                # X-Launchpad-Export-Date but we need to accept the old one
                # too so old exports will still work.
                try:
                    self.launchpad_export_date = (
                        datetimeutils.parseDatetimetz(value))
                except datetimeutils.DateTimeError:
                    self.launchpad_export_date = None
            else:
                # We don't use the other keys.
                pass

    def getRawContent(self):
        """See `ITranslationHeaderData`."""
        raw_content_list = []
        for key in self._handled_keys_order:
            value = self._handled_keys_mapping[key]
            if key == 'project-id-version':
                if key in self._header_dictionary:
                    content = self._header_dictionary[key]
                else:
                    # Use default one.
                    content = 'PACKAGE VERSION'
                raw_content_list.append('%s: %s\n' % (value, content))
            elif key == 'report-msgid-bugs-to':
                if key in self._header_dictionary:
                    content = self._header_dictionary[key]
                else:
                    # Use default one.
                    content = ' '
                raw_content_list.append(
                    '%s: %s\n' % (value, content))
            elif key == 'pot-creation-date':
                raw_content_list.append(
                    '%s: %s\n' % (value, self.template_creation_date.strftime(
                        self._strftime_text)))
            elif key == 'po-revision-date':
                if self.translation_revision_date is None:
                    revision_date_text = 'YEAR-MO-DA HO:MI+ZONE'
                else:
                    revision_date_text = (
                        self.translation_revision_date.strftime(
                            self._strftime_text))
                raw_content_list.append(
                    '%s: %s\n' % (
                        value, revision_date_text))
            elif key == 'last-translator':
                raw_content_list.append(
                    '%s: %s\n' % (value, self._last_translator))
            elif key == 'language-team':
                raw_content_list.append(
                    '%s: %s\n' % (value, self.language_team))
            elif key == 'mime-version':
                raw_content_list.append('%s: 1.0\n' % value)
            elif key == 'content-type':
                raw_content_list.append(
                    '%s: text/plain; charset=%s\n' % (value, self.charset))
            elif key == 'content-transfer-encoding':
                raw_content_list.append('%s: 8bit\n' % value)
            elif key == 'plural-forms':
                if not self.has_plural_forms:
                    # This file doesn't have plural forms so we don't export
                    # any plural form information in the header.
                    continue
                if self.number_plural_forms is None:
                    # Use the default values.
                    nplurals = 'INTEGER'
                    plural = 'EXPRESSION'
                else:
                    nplurals = str(self.number_plural_forms)
                    plural = self.plural_form_expression
                raw_content_list.append('%s: nplurals=%s; plural=%s;\n' % (
                    value, nplurals, plural))
            elif key == 'x-rosetta-export-date':
                # Ignore it, new exports use x-launchpad-export-date.
                continue
            elif key == 'x-launchpad-export-date':
                UTC = pytz.timezone('UTC')
                now = datetime.datetime.now(UTC)
                raw_content_list.append(
                    '%s: %s\n' % (value, now.strftime(self._strftime_text)))
            elif key == 'x-generator':
                # Note the revision number so it would help for debugging
                # problems with bad exports.
                if revno is None:
                    build = 'Unknown'
                else:
                    build = revno
                raw_content_list.append(
                    '%s: Launchpad (build %s)\n' % (value, build))
            else:
                raise AssertionError('key %s is not being handled!' % value)

        # Now, we copy any other header information in the original .po file.
        for key, value in self._header_dictionary.iteritems():
            if key in self._handled_keys_mapping:
                # It's already handled, skip it.
                continue

            raw_content_list.append('%s: %s\n' % (key, value.strip()))

        return u''.join(raw_content_list)

    def updateFromTemplateHeader(self, template_header):
        """See `ITranslationHeaderData`."""
        template_header_dictionary = get_header_dictionary(
            template_header.getRawContent(), self._handled_keys_order)
        # 'Domain' is a non standard header field. However, this is required
        # for good Plone support. It relies in that field to know the
        # translation domain. For more information you can take a look to
        # https://bugs.launchpad.net/rosetta/+bug/5
        fields_to_copy = ['Domain']

        for field in fields_to_copy:
            if field in template_header_dictionary:
                self._header_dictionary[field] = (
                    template_header_dictionary[field])

        # Standard fields update.
        self.template_creation_date = template_header.template_creation_date

    def getLastTranslator(self):
        """See `ITranslationHeaderData`."""
        # Get last translator information. If it's not found, we use the
        # default value from Gettext.
        name, email = parseaddr(self._last_translator)

        if email == 'EMAIL@ADDRESS' or '@' not in email:
            # Gettext (and Launchpad) sets by default the email address to
            # EMAIL@ADDRESS unless it knows the real address, thus,
            # we know this isn't a real account so we don't accept it as a
            # valid one.
            return None, None
        else:
            return name, email

    def setLastTranslator(self, email, name=None):
        """See `ITranslationHeaderData`."""
        assert email is not None, 'Email address cannot be None'

        if name is None:
            name = u''
        self._last_translator = u'%s <%s>' % (name, email)


class POParser(object):
    """Parser class for Gettext files."""

    def __init__(self, plural_formula=None):
        self._translation_file = None
        self._lineno = 0
        # This is a default plural form mapping (i.e. no mapping) when
        # no header is present in the PO file.
        self._plural_form_mapping = {0: 0, 1: 1, 2: 2, 3: 3}
        self._expected_plural_formula = plural_formula

    def _decode(self):
        # is there anything to convert?
        if not self._pending_chars:
            return

        # if the PO header hasn't been parsed, then we don't know the
        # encoding yet
        if self._translation_file.header is None:
            return

        charset = self._translation_file.header.charset
        decode = codecs.getdecoder(charset)
        # decode as many characters as we can:
        try:
            newchars, length = decode(self._pending_chars, 'strict')
        except UnicodeDecodeError, exc:
            # XXX: James Henstridge 2006-03-16:
            # If the number of unconvertable chars is longer than a
            # multibyte sequence to be, the UnicodeDecodeError indicates
            # a real error, rather than a partial read.
            # I don't know what the longest multibyte sequence in the
            # encodings we need to support, but it shouldn't be more
            # than 10 bytes ...
            if len(self._pending_chars) - exc.start > 10:
                raise TranslationFormatInvalidInputError(
                    line_number=self._lineno,
                    message="could not decode input from %s" % charset)
            newchars, length = decode(self._pending_chars[:exc.start],
                                      'strict')
        self._pending_unichars += newchars
        self._pending_chars = self._pending_chars[length:]

    def _getHeaderLine(self):
        if self._translation_file.header is not None:
            # We know what charset the data is in, as we've already
            # parsed the header.  However, we're going to handle this
            # more efficiently, so we don't want to use _getHeaderLine
            # except for parsing the header.
            raise AssertionError(
                'using _getHeaderLine after header is parsed')

        # We don't know what charset the data is in, so we parse it one line
        # at a time until we have the header, and then we'll know how to
        # treat the rest of the data.
        parts = re.split(r'\n|\r\n|\r', self._pending_chars, 1)
        if len(parts) == 1:
            # only one line
            return None
        line, self._pending_chars = parts
        return line.strip()

    def parse(self, content_text):
        """Parse string as a PO file."""
        # Initialise the parser.
        self._translation_file = TranslationFileData()
        self._messageids = set()
        self._pending_chars = content_text
        self._pending_unichars = u''
        self._lineno = 0
        # Message specific variables.
        self._message = TranslationMessageData()
        self._message_lineno = self._lineno
        self._section = None
        self._plural_case = None
        self._parsed_content = u''

        # First thing to do is to get the charset used in the content_text.
        charset = parse_charset(content_text)

        # Now, parse the header, inefficiently. It ought to be short, so
        # this isn't disastrous.
        line = self._getHeaderLine()
        while line is not None:
            self._parseLine(line.decode(charset))
            if (self._translation_file.header is not None or
                self._message.msgid_singular):
                # Either found the header already or it's a message with a
                # non empty msgid which means is not a header.
                break
            line = self._getHeaderLine()

        if line is None:
            if (self._translation_file.header is None and
                not self._message.msgid_singular):
                # Seems like the file has only the header without any message,
                # we parse it.
                self._dumpCurrentSection()
                self._parseHeader()

            # There is nothing left to parse.
            return self._translation_file

        # Parse anything left all in one go.
        lines = re.split(r'\n|\r\n|\r', self._pending_unichars)
        for line in lines:
            self._parseLine(line)

        if self._translation_file.header is None:
            raise TranslationFormatSyntaxError(
                message='No header found in this pofile')

        if self._message is not None:
            # We need to dump latest message.
            if self._section is None:
                # The message has not content or it's just a comment, ignore
                # it.
                return self._translation_file
            elif self._section == 'msgstr':
                self._dumpCurrentSection()
                self._storeCurrentMessage()
            else:
                raise TranslationFormatSyntaxError(
                    line_number = self._lineno,
                    message='Got a truncated message!')

        return self._translation_file

    def _storeCurrentMessage(self):
        if self._message is not None:
            msgkey = self._message.msgid_singular
            if self._message.context is not None:
                msgkey = '%s\2%s' % (self._message.context, msgkey)
            if msgkey in self._messageids:
                # We use '%r' instead of '%d' because there are situations
                # when it returns an "<unprintable instance object>". You can
                # see more details on bug #2896
                raise TranslationFormatInvalidInputError(
                    message='PO file: duplicate msgid ending on line %r' % (
                        self._message_lineno))

            number_plural_forms = (
                self._translation_file.header.number_plural_forms)
            if (self._message.msgid_plural and
                len(self._message.translations) < number_plural_forms):
                # Has plural forms but the number of translations is lower.
                # Fill the others with an empty string.
                for index in range(
                    len(self._message.translations), number_plural_forms):
                    self._message.addTranslation(index, u'')

            self._translation_file.messages.append(self._message)
            self._messageids.add(msgkey)
            self._message = None

    def _parseHeader(self):
        try:
            self._translation_file.header = POHeader(
                self._message.translations[
                    TranslationConstants.SINGULAR_FORM],
                self._message.comment)
        except TranslationFormatInvalidInputError, error:
            if error.line_number is None:
                error.line_number = self._message_lineno
            raise
        self._translation_file.header.is_fuzzy = (
            'fuzzy' in self._message.flags)

        if self._translation_file.messages:
            logging.warning(
                POSyntaxWarning(
                    self._lineno, 'Header entry is not first entry'))

        plural_formula = self._translation_file.header.plural_form_expression
        if plural_formula is None:
            # We default to a simple plural formula which uses
            # a single form for translations.
            plural_formula = '0'
        self._plural_form_mapping = plural_form_mapper(
            plural_formula, self._expected_plural_formula)
        # convert buffered input to the encoding specified in the PO header
        self._decode()

    def _parseQuotedString(self, string):
        r"""Parse a quoted string, interpreting escape sequences.

          >>> parser = POParser()
          >>> parser._parseQuotedString(u'\"abc\"')
          u'abc'
          >>> parser._parseQuotedString(u'\"abc\\ndef\"')
          u'abc\ndef'
          >>> parser._parseQuotedString(u'\"ab\x63\"')
          u'abc'
          >>> parser._parseQuotedString(u'\"ab\143\"')
          u'abc'

          After the string has been converted to unicode, the backslash
          escaped sequences are still in the encoding that the charset header
          specifies. Such quoted sequences will be converted to unicode by
          this method.

          We don't know the encoding of the escaped characters and cannot be
          just recoded as Unicode so it's a TranslationFormatInvalidInputError
          >>> utf8_string = u'"view \\302\\253${version_title}\\302\\273"'
          >>> parser._parseQuotedString(utf8_string)
          Traceback (most recent call last):
          ...
          TranslationFormatInvalidInputError: could not decode escaped string: (\302\253)

          Now, we note the original encoding so we get the right Unicode
          string.

          >>> class FakeHeader:
          ...     charset = 'UTF-8'
          >>> parser._translation_file = TranslationFileData()
          >>> parser._translation_file.header = FakeHeader()
          >>> parser._parseQuotedString(utf8_string)
          u'view \xab${version_title}\xbb'

          Let's see that we raise a TranslationFormatInvalidInputError exception when we
          have an escaped char that is not valid in the declared encoding
          of the original string:

          >>> iso8859_1_string = u'"foo \\xf9"'
          >>> parser._parseQuotedString(iso8859_1_string)
          Traceback (most recent call last):
          ...
          TranslationFormatInvalidInputError: could not decode escaped string as UTF-8: (\xf9)

          An error will be raised if the entire string isn't contained in
          quotes properly:

          >>> parser._parseQuotedString(u'abc')
          Traceback (most recent call last):
            ...
          TranslationFormatSyntaxError: string is not quoted
          >>> parser._parseQuotedString(u'\"ab')
          Traceback (most recent call last):
            ...
          TranslationFormatSyntaxError: string not terminated
          >>> parser._parseQuotedString(u'\"ab\"x')
          Traceback (most recent call last):
            ...
          TranslationFormatSyntaxError: extra content found after string: (x)
        """
        if string[0] != '"':
            raise TranslationFormatSyntaxError(
                line_number=self._lineno, message="string is not quoted")

        escape_map = {
            'a': '\a',
            'b': '\b',
            'f': '\f',
            'n': '\n',
            'r': '\r',
            't': '\t',
            'v': '\v',
            '"': '"',
            '\'': '\'',
            '\\': '\\',
            }

        # Remove initial quote char
        string = string[1:]
        output = ''
        while string:
            if string[0] == '"':
                # Reached the end of the quoted string.  It's rare, but there
                # may be another quoted string on the same line.  It should be
                # suffixed to what we already have, with any whitespace
                # between the strings removed.
                string = string[1:].lstrip()
                if not string:
                    # End of line, end of string: the normal case
                    break
                if string[0] == '"':
                    # Start of a new string.  We've already swallowed the
                    # closing quote and any intervening whitespace; now
                    # swallow the re-opening quote and go on as if the string
                    # just went on normally
                    string = string[1:]
                    continue

                # if there is any non-string data afterwards, raise an
                # exception
                if string and not string.isspace():
                    raise TranslationFormatSyntaxError(
                        line_number=self._lineno,
                        message="extra content found after string: (%s)" % string)
                break
            elif string[0] == '\\' and string[1] in escape_map:
                # We got one of the special escaped chars we know about, we
                # unescape them using the mapping table we have.
                output += escape_map[string[1]]
                string = string[2:]
                continue

            escaped_string = ''
            while string[0] == '\\':
                # Let's handle any normal char escaped. This kind of chars are
                # still in the original encoding so we need to extract the
                # whole block of escaped chars to recode them later into
                # Unicode.
                if string[1] == 'x':
                    # hexadecimal escape
                    escaped_string += string[:4]
                    string = string[4:]
                elif string[1].isdigit():
                    # octal escape
                    escaped_string += string[:2]
                    string = string[2:]
                    # up to two more octal digits
                    for i in range(2):
                        if string[0].isdigit():
                            escaped_string += string[0]
                            string = string[1:]
                        else:
                            break
                elif string[1] in escape_map:
                    # It's part of our mapping table, we ignore it here.
                    break
                else:
                    raise TranslationFormatSyntaxError(
                        line_number=self._lineno,
                        message="unknown escape sequence %s" % string[:2])
            if escaped_string:
                # We found some text escaped that should be recoded to
                # Unicode.
                # First, we unescape it.
                unescaped_string = escaped_string.decode('string-escape')

                if (self._translation_file is not None and
                    self._translation_file.header is not None):
                    # There is a header, so we know the original encoding for
                    # the given string.
                    charset = self._translation_file.header.charset
                    try:
                        output += unescaped_string.decode(charset)
                    except UnicodeDecodeError:
                        raise TranslationFormatInvalidInputError(
                            line_number=self._lineno,
                            message=(
                                "could not decode escaped string as %s: (%s)"
                                    % (charset, escaped_string)))
                else:
                    # We don't know the original encoding of the imported file
                    # so we cannot get the right values. We store the string
                    # assuming that is a valid ASCII escape sequence.
                    try:
                        output += unescaped_string.decode('ascii')
                    except UnicodeDecodeError:
                        raise TranslationFormatInvalidInputError(
                            line_number=self._lineno,
                            message=(
                                "could not decode escaped string: (%s)" % (
                                    escaped_string)))
            else:
                # It's a normal char, we just store it and jump to next one.
                output += string[0]
                string = string[1:]
        else:
            # We finished parsing the string without finding the ending quote
            # char.
            raise TranslationFormatSyntaxError(
                line_number=self._lineno, message="string not terminated")

        return output

    def _dumpCurrentSection(self):
        """Dump current parsed content inside the translation message."""
        if self._section is None:
            # There is nothing to dump.
            return
        elif self._section == 'msgctxt':
            self._message.context = self._parsed_content
        elif self._section == 'msgid':
            self._message.msgid_singular = self._parsed_content
        elif self._section == 'msgid_plural':
            self._message.msgid_plural = self._parsed_content
            # Note in the header that there are plural forms.
            self._translation_file.header.has_plural_forms = True
        elif self._section == 'msgstr':
            self._message.addTranslation(
                self._plural_form_mapping[self._plural_case],
                self._parsed_content)
        else:
            raise AssertionError('Unknown section %s' % self._section)

        self._parsed_content = u''

    def _parseLine(self, original_line):
        self._lineno += 1
        # Skip empty lines
        l = original_line.strip()

        is_obsolete = False
        if l[:2] == '#~':
            is_obsolete = True
            l = l[2:].lstrip()

        if not l:
            return

        # If we get a comment line after a msgstr or a line starting with
        # msgid or msgctxt, this is a new entry.
        if ((l.startswith('#') or l.startswith('msgid') or
             l.startswith('msgctxt')) and self._section == 'msgstr'):
            if self._message is None:
                # first entry - do nothing.
                pass
            elif self._message.msgid_singular:
                self._dumpCurrentSection()
                self._storeCurrentMessage()
            elif self._translation_file.header is None:
                # When there is no msgid in the parsed message, it's the
                # header for this file.
                self._dumpCurrentSection()
                self._parseHeader()
            else:
                logging.warning(
                    POSyntaxWarning(self._lineno, 'We got a second header.'))

            # Start a new message.
            self._message = TranslationMessageData()
            self._message_lineno = self._lineno
            self._section = None
            self._plural_case = None
            self._parsed_content = u''

        if self._message is not None:
            # Record whether the message is obsolete.
            self._message.is_obsolete = is_obsolete

        if l[0] == '#':
            # Record flags
            if l[:2] == '#,':
                new_flags = [flag.strip() for flag in l[2:].split(',')]
                self._message.flags.update(new_flags)
                return
            # Record file references
            if l[:2] == '#:':
                if self._message.file_references:
                    # There is already a file reference, let's split it from
                    # the new one with a new line char.
                    self._message.file_references += '\n'
                self._message.file_references += l[2:].strip()
                return
            # Record source comments
            if l[:2] == '#.':
                self._message.source_comment += l[2:].strip() + '\n'
                return
            # Record comments
            self._message.comment += l[1:] + '\n'
            return

        # Now we are in a msgctxt or msgid section, output previous section
        if l.startswith('msgid_plural'):
            if self._section != 'msgid':
                raise TranslationFormatSyntaxError(line_number=self._lineno)
            self._dumpCurrentSection()
            self._section = 'msgid_plural'
            l = l[len('msgid_plural'):]
        elif l.startswith('msgctxt'):
            if (self._section is not None and
                (self._section == 'msgctxt' or
                 self._section.startswith('msgid'))):
                raise TranslationFormatSyntaxError(line_number=self._lineno)
            self._section = 'msgctxt'
            l = l[len('msgctxt'):]
        elif l.startswith('msgid'):
            if self._section is not None and self._section.startswith('msgid'):
                raise TranslationFormatSyntaxError(line_number=self._lineno)
            if self._section is not None:
                self._dumpCurrentSection()
            self._section = 'msgid'
            l = l[len('msgid'):]
            self._plural_case = None
        # Now we are in a msgstr section
        elif l.startswith('msgstr'):
            self._dumpCurrentSection()
            self._section = 'msgstr'
            l = l[len('msgstr'):]
            # XXX kiko 2005-08-19: if l is empty, it means we got an msgstr
            # followed by a newline; that may be critical, but who knows?
            if l and l[0] == '[':
                # plural case
                new_plural_case, l = l[1:].split(']', 1)
                new_plural_case = int(new_plural_case)
                if (self._plural_case is not None) and (
                        new_plural_case != self._plural_case + 1):
                    logging.warning(POSyntaxWarning(self._lineno,
                                                  'bad plural case number'))
                if new_plural_case != self._plural_case:
                    self._plural_case = new_plural_case
                else:
                    logging.warning(POSyntaxWarning(
                        self._lineno, 'msgstr[] but same plural case number'))
            else:
                self._plural_case = TranslationConstants.SINGULAR_FORM
        elif self._section is None:
            raise TranslationFormatSyntaxError(
                line_number=self._lineno,
                message='Invalid content: %r' % original_line)
        else:
            # This line could be the continuation of a previous section.
            pass

        l = l.strip()
        if not l:
            logging.info(
                POSyntaxWarning(
                    self._lineno,
                    'line has no content; this is not supported by'
                    'some implementations of msgfmt'))
            return

        l = self._parseQuotedString(l)

        if self._section in ('msgctxt', 'msgid', 'msgid_plural', 'msgstr'):
            self._parsed_content += l
        else:
            raise TranslationFormatSyntaxError(
                line_number=self._lineno,
                message='Invalid content: %r' % original_line)


# convenience function to parse "assignment" expressions like
# the plural-form header
def parse_assignments(text, separator=';', assigner='=', skipfirst=False):
    parts = {}
    if skipfirst:
        start=1
    else:
        start=0
    for assignment in text.split(separator)[start:]:
        if not assignment.strip():
            # empty
            continue
        if assigner in assignment:
            name, value = assignment.split(assigner, 1)
        else:
            logging.warning(POSyntaxWarning(
                msg="Found an error in the header content: %s" % text
                ))
            continue

        parts[name.strip()] = value.strip()
    return parts
