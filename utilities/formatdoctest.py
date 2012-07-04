#!/usr/bin/python
#
# Copyright (C) 2009 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2.
#
# It comes from the Gedit Developer Plugins project (launchpad.net/gdp); see
# http://bazaar.launchpad.net/~sinzui/gdp/trunk/files/head%3A/plugins/gdp/ &
# http://bazaar.launchpad.net/%7Esinzui/gdp/trunk/annotate/head%3A/COPYING.

"""Reformat a doctest to Launchpad style."""

__metatype__ = type

import compiler
from difflib import unified_diff
from doctest import (
    DocTestParser,
    Example,
    )
from optparse import OptionParser
import re
import sys
from textwrap import wrap

import pyflakes
from pyflakes.checker import Checker


class DoctestReviewer:
    """Check and reformat doctests."""
    rule_pattern = re.compile(r'([=~-])+[ ]*$')
    moin_pattern = re.compile(r'^(=+)[ ](.+)[ ](=+[ ]*)$')
    continuation_pattern = re.compile(r'^(\s*\.\.\.) (.+)$', re.M)

    SOURCE = 'source'
    WANT = 'want'
    NARRATIVE = 'narrative'

    def __init__(self, doctest, file_name):
        self.doctest = doctest
        self.file_name = file_name
        doctest = self._disambuguate_doctest(doctest)
        parser = DocTestParser()
        self.parts = parser.parse(doctest, file_name)
        self.blocks = []
        self.block = []
        self.block_method = self.preserve_block
        self.code_lines = []
        self.example = None
        self.last_bad_indent = 0
        self.has_printed_filename = False

    def _disambuguate_doctest(self, doctest):
        """Clarify continuations that the doctest parser hides."""
        return self.continuation_pattern.sub(r'\1    \2', doctest)

    def _print_message(self, message, lineno):
        """Print the error message with the lineno.

        :param message: The message to print.
        :param lineno: The line number the message pertains to.
        """
        if not self.has_printed_filename:
            print '%s:' % self.file_name
            self.has_printed_filename = True
        print '    % 4s: %s' % (lineno, message)

    def _is_formatted(self, text):
        """Return True if the text is pre-formatted, otherwise False.

        :param: text a string, or a list of strings.
        """
        if isinstance(text, list):
            text = text[0]
        return text.startswith(' ')

    def _walk(self, doctest_parts):
        """Walk the doctest parts; yield the line and kind.

        Yield the content of the line, and its kind (SOURCE, WANT, NARRATIVE).
        SOURCE and WANT lines are stripped of indentation, SOURCE is also
        stripped of the interpreter symbols.
        
        :param doctest_parts: The output of DocTestParser.parse.
        """
        for part in doctest_parts:
            if part == '':
                continue
            if isinstance(part, Example):
                self.example = part
                for line in part.source.splitlines():
                    kind = DoctestReviewer.SOURCE
                    yield line, kind
                for line in part.want.splitlines():
                    kind = DoctestReviewer.WANT
                    yield line, kind
            else:
                self.example = None
                kind = DoctestReviewer.NARRATIVE
                for line in part.splitlines():
                    yield line, kind

    def _apply(self, line_methods):
        """Call each line_method for each line in the doctest.

        :param line_methods: a list of methods that accept lineno, line,
            and kind as arguments. Each method must return the line for
            the next method to process.
        """
        self.blocks = []
        self.block = []
        lineno = 0
        previous_kind = DoctestReviewer.NARRATIVE
        for line, kind in self._walk(self.parts):
            lineno += 1
            self._append_source(kind, line)
            if kind != previous_kind and kind != DoctestReviewer.WANT:
                # The WANT block must adjoin the preceding SOURCE block.
                self._store_block(previous_kind)
            for method in line_methods:
                line = method(lineno, line, kind, previous_kind)
                if line is None:
                    break
            if not line:
                continue
            self.block.append(line)
            previous_kind = kind
        # Capture the last block and a blank line.
        self.block.append('\n')
        self._store_block(previous_kind)

    def _append_source(self, kind, line):
        """Update the list of source code lines seen."""
        if kind == self.SOURCE:
            self.code_lines.append(line)
        else:
            self.code_lines.append('')

    def _store_block(self, kind):
        """Append the block to blocks, re-wrap unformatted narrative.

        :param kind: The block's kind (SOURCE, WANT, NARRATIVE)
        """
        if len(self.block) == 0:
            return
        block = self.block_method(kind, self.block, self.blocks)
        self.blocks.append('\n'.join(block))
        self.block = []

    def check(self):
        """Check the doctest for style and code issues.

        1. Check line lengths.
        2. Check that headings are not in Moin format.
        3. Check indentation.
        4. Check trailing whitespace.
        """
        self.code_lines = []
        line_checkers = [
            self.check_length,
            self.check_heading,
            self.check_indentation,
            self.check_trailing_whitespace,]
        self._apply(line_checkers)
        code = '\n'.join(self.code_lines)
        self.check_source_code(code)

    def format(self):
        """Reformat doctest.

        1. Tests are reindented to 4 spaces.
        2. Simple narrative is rewrapped to 78 character width.
        3. Formatted (indented) narrative is preserved.
        4. Moin headings are converted to RSR =, == , and === levels.
        5. There is one blank line between blocks,
        6. Except for headers which have two leading blank lines.
        7. All trailing whitespace is removed.

        SOURCE and WANT long lines are not fixed--this is a human operation.
        """
        line_checkers = [
            self.fix_trailing_whitespace,
            self.fix_indentation,
            self.fix_heading,
            self.fix_narrative_paragraph,]
        self.block_method = self.format_block
        self._apply(line_checkers)
        self.block_method = self.preserve_block
        return '\n\n'.join(self.blocks)

    def preserve_block(self, kind, block, blocks):
        """Do nothing to the block.

        :param kind: The block's kind (SOURCE, WANT, NARRATIVE)
        :param block: The list of lines that should remain together.
        :param blocks: The list of all collected blocks.
        """
        return block

    def format_block(self, kind, block, blocks):
        """Format paragraph blocks.

        :param kind: The block's kind (SOURCE, WANT, NARRATIVE)
        :param block: The list of lines that should remain together.
        :param blocks: The list of all collected blocks.
        """
        if kind != DoctestReviewer.NARRATIVE or self._is_formatted(block):
            return block
        try:
            rules = ('===', '---', '...')
            last_line = block[-1]
            is_heading = last_line[0:3] in rules and last_line[-3:] in rules
        except IndexError:
            is_heading = False
        if len(blocks) != 0 and is_heading:
            # Headings should have an extra leading blank line.
            block.insert(0, '')
        elif is_heading:
            # Do nothing. This is the first heading in the file.
            pass
        else:
            long_line = ' '.join(block).strip()
            block = wrap(long_line, 72)
        return block

    def is_comment(self, line):
        """Return True if the line is a comment."""
        comment_pattern = re.compile(r'\s*#')
        return comment_pattern.match(line) is not None

    def check_length(self, lineno, line, kind, previous_kind):
        """Check the length of the line.

        Each kind of line has a maximum length:

        * NARRATIVE: 78 characters.
        * SOURCE: 70 characters (discounting indentation and interpreter).
        * WANT: 74 characters (discounting indentation).
        """

        length = len(line)
        if kind == DoctestReviewer.NARRATIVE and self.is_comment(line):
            # comments follow WANT rules because they are in code.
            kind = DoctestReviewer.WANT
            line = line.lstrip()
        if kind == DoctestReviewer.NARRATIVE and length > 78:
            self._print_message('%s exceeds 78 characters.' % kind, lineno)
        elif kind == DoctestReviewer.WANT and length > 74:
            self._print_message('%s exceeds 78 characters.' % kind, lineno)
        elif kind == DoctestReviewer.SOURCE and length > 70:
            self._print_message('%s exceeds 78 characters.' % kind, lineno)
        else:
            # This line has a good length.
            pass
        return line

    def check_indentation(self, lineno, line, kind, previous_kind):
        """Check the indentation of the SOURCE or WANT line."""
        if kind == DoctestReviewer.NARRATIVE:
            return line
        if self.example.indent != 4:
            if self.last_bad_indent != lineno - 1:
                self._print_message('%s has bad indentation.' % kind, lineno)
            self.last_bad_indent = lineno
        return line

    def check_trailing_whitespace(self, lineno, line, kind, previous_kind):
        """Check for the presence of trailing whitespace in the line."""
        if line.endswith(' '):
            self._print_message('%s has trailing whitespace.' % kind, lineno)
        return line

    def check_heading(self, lineno, line, kind, previous_kind):
        """Check for narrative lines that use moin headers instead of RST."""
        if kind != DoctestReviewer.NARRATIVE:
            return line
        moin = self.moin_pattern.match(line)
        if moin is not None:
            self._print_message('%s uses a moin header.' % kind, lineno - 1)
        return line

    def check_source_code(self, code):
        """Check for source code problems in the doctest using pyflakes.

        The most common problem found are unused imports. `UndefinedName`
        errors are suppressed because the test setup is not known.
        """
        if code == '':
            return
        try:
            tree = compiler.parse(code)
        except (SyntaxError, IndentationError) as exc:
            (lineno, offset_, line) = exc[1][1:]
            if line.endswith("\n"):
                line = line[:-1]
            self._print_message(
                'Could not compile:\n          %s' % line, lineno - 1)
        else:
            warnings = Checker(tree)
            for warning in warnings.messages:
                if isinstance(warning, pyflakes.messages.UndefinedName):
                    continue
                dummy, lineno, message = str(warning).split(':')
                self._print_message(message.strip(), lineno)

    def fix_trailing_whitespace(self, lineno, line, kind, previous_kind):
        """Return the line striped of trailing whitespace."""
        return line.rstrip()

    def fix_indentation(self, lineno, line, kind, previous_kind):
        """set the indentation to 4-spaces."""
        if kind == DoctestReviewer.NARRATIVE:
            return line
        elif kind == DoctestReviewer.WANT:
            return '    %s' % line
        else:
            if line.startswith(' '):
                # This is a continuation of DoctestReviewer.SOURCE.
                return '    ... %s' % line
            else:
                # This is a start of DoctestReviewer.SOURCE.
                return '    >>> %s' % line

    def fix_heading(self, lineno, line, kind, previous_kind):
        """Switch Moin headings to RST headings."""
        if kind != DoctestReviewer.NARRATIVE:
            return line
        moin = self.moin_pattern.match(line)
        if moin is None:
            return line
        heading_level = len(moin.group(1))
        heading = moin.group(2)
        rule_length = len(heading)
        if heading_level == 1:
            rule = '=' * rule_length
        elif heading_level == 2:
            rule = '-' * rule_length
        else:
            rule = '.' * rule_length
        # Force the heading on to the block of lines.
        self.block.append(heading)
        return rule

    def fix_narrative_paragraph(self, lineno, line, kind, previous_kind):
        """Break narrative into paragraphs."""
        if kind != DoctestReviewer.NARRATIVE or len(self.block) == 0:
            return line
        if line == '':
            # This is the start of a new paragraph in the narrative.
            self._store_block(previous_kind)
        if self._is_formatted(line) and not self._is_formatted(self.block):
            # This line starts a pre-formatted paragraph.
            self._store_block(previous_kind)
        return line


def get_option_parser():
    """Return the option parser for this program."""
    usage = "usage: %prog [options] doctest.txt"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-f", "--format", dest="is_format", action="store_true",
        help="Reformat the doctest.")
    parser.add_option(
        "-i", "--interactive", dest="is_interactive",  action="store_true",
        help="Approve each change.")
    parser.set_defaults(
        is_format=False,
        is_interactive=False)
    return parser


def main(argv=None):
    """Run the operations requested from the command line."""
    if argv is None:
        argv = sys.argv
    parser = get_option_parser()
    (options, args) = parser.parse_args(args=argv[1:])
    if len(args) == 0:
        parser.error("A doctest must be specified.")

    for file_name in args:
        try:
            doctest_file = open(file_name)
            old_doctest = doctest_file.read()
        finally:
            doctest_file.close()
        reviewer = DoctestReviewer(old_doctest, file_name)

        if not options.is_format:
            reviewer.check()
            continue

        new_doctest = reviewer.format()
        if new_doctest != old_doctest:
            if options.is_interactive:
                diff = unified_diff(
                    old_doctest.splitlines(), new_doctest.splitlines())
                print '\n'.join(diff)
                print '\n'
                do_save = raw_input(
                    'Do you wish to save the changes? S(ave) or C(ancel)?')
            else:
                do_save = 'S'

            if do_save.upper() == 'S':
                try:
                    doctest_file = open(file_name, 'w')
                    doctest_file.write(new_doctest)
                finally:
                    doctest_file.close()
            reviewer = DoctestReviewer(new_doctest, file_name)
            reviewer.check()


if __name__ == '__main__':
    sys.exit(main())
