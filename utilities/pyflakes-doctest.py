#!/usr/bin/python
# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Perform pyflakes checks on doctests."""

import compiler
import doctest
import operator
import os
import sys

import pyflakes
# XXX sinzui 2008-04-03:
# pyflakes broke its API. We should be using pyflakes.checker.Checker,
# but while we are transitioning to Hardy, we will preserve the old
# behaviour.
try:
    from pyflakes.checker import Checker
except ImportError:
    Checker = pyflakes.Checker


# Names we define in the globals for our doctests
GLOBAL_NAMES = set([
    # for system documentation
    'ANONYMOUS',
    'ILaunchBag',
    'bugtarget',
    'commit',
    'create_view',
    'flush_database_updates',
    'getUtility',
    'login',
    'logout',
    'transaction',
    'LaunchpadObjectFactory',
    # for page tests
    'admin_browser',
    'anon_browser',
    'browser',
    'extract_link_from_tag',
    'extract_text',
    'filebug',
    'find_main_content',
    'find_portlet',
    'find_tag_by_id',
    'find_tags_by_class',
    'first_tag_by_class',
    'get_feedback_messages',
    'http',
    'mailinglist_api',
    'parse_relationship_section',
    'print_action_links',
    'print_batch_header',
    'print_comments',
    'print_navigation',
    'print_navigation_links',
    'print_portlet_links',
    'print_ppa_packages',
    'print_radio_button_field',
    'print_self_link_of_entries',
    'print_submit_buttons',
    'print_tab_links',
    'setupBrowser',
    'user_browser',
    'webservice',
    'public_webservice',
    'user_webservice',
    # For OpenID per-version tests
    'PROTOCOL_URI',
    # For buildd tests
    'test_dbuser'
    ])


def extract_script(data):
    """Process a doctest into an equivalent Python script.

    This code is based on doctest.script_from_examples() but has been
    modified not to insert or remove lines of content.  This should
    make line numbers in the output script match those in the input.

        >>> text = '''
        ...
        ... Some text
        ...     >>> 2 + 2
        ...     5
        ...
        ... More text
        ...
        ...     >>> if False:
        ...     ...     whatever
        ...
        ... end.
        ... '''

        >>> print extract_script(text)
        #
        # Some text
        2 + 2
        ## 5
        #
        # More text
        #
        if False:
            whatever
        #
        # end.
        <BLANKLINE>
    """
    output = []
    for piece in doctest.DocTestParser().parse(data):
        if isinstance(piece, doctest.Example):
            # Add the example's source code (strip trailing NL)
            output.append(piece.source[:-1])
            # Add the expected output:
            want = piece.want
            if want:
                output += ['## '+l for l in want.split('\n')[:-1]]
        else:
            # Add non-example text.
            output += [doctest._comment_line(l)
                       for l in piece.split('\n')[:-1]]
    # Combine the output, and return it.
    # Add a courtesy newline to prevent exec from choking
    return '\n'.join(output) + '\n'


def suppress_warning(warning):
    """Returns True if a particular warning should be supressed."""
    if isinstance(warning, pyflakes.messages.UndefinedName):
        # Suppress warnings due to names that are defined as globals.
        if warning.message_args[0] in GLOBAL_NAMES:
            return True
    return False


def check_doctest(filename):
    """Create a PyFlakes object from a doctest."""
    data = open(filename, 'r').read()
    script = extract_script(data)

    try:
        tree = compiler.parse(script)
    except (SyntaxError, IndentationError), exc:
        (lineno, offset, line) = exc[1][1:]
        if line.endswith("\n"):
            line = line[:-1]
        print >> sys.stderr, 'could not compile %r:%d' % (filename, lineno)
        print >> sys.stderr, line
        print >> sys.stderr, " " * (offset-1), "^"
    else:
        w = Checker(tree, filename)
        for warning in sorted(w.messages, key=operator.attrgetter('lineno')):
            if suppress_warning(warning):
                continue
            print warning


def main(argv):
    """Check the files passed on the command line."""
    for arg in argv[1:]:
        if os.path.isdir(arg):
            for dirpath, dirnames, filenames in os.walk(arg):
                for filename in filenames:
                    if filename.endswith('.txt'):
                        check_doctest(os.path.join(dirpath, filename))
        else:
            check_doctest(arg)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
