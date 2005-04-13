# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing.doctest import DocTestSuite
from canonical.launchpad import helpers

def make_test_string_1():
    '''
    Generate a test tarball that looks something like a source tarball which
    has exactly one directory called 'po' which is interesting (i.e. contains
    some files which look like POT/PO files).

    >>> tarball = helpers.string_to_tarfile(make_test_string_1())

    Check it looks vaguely sensible.

    >>> names = tarball.getnames()
    >>> 'uberfrob-0.1/po/cy.po' in names
    True
    '''

    return helpers.make_tarfile({
        'uberfrob-0.1' : {
            'README' : 'Uberfrob is an advanced frobnicator.',
            'po' : {
                'cy.po' : '# Blah.',
                'es.po' : '# Blah blah.',
                'uberfrob.pot' : '# Yowza!',
                 },
            'blah' : {
                'po' : {
                    'la' : 'la la' }
                },
            'uberfrob.py' :
                'import sys\n'
                'print "Frob!"\n'
            }
        })

def make_test_string_2():
    r'''
    Generate a test tarball string that has some interesting files in a common
    prefix.

    >>> tarball = helpers.string_to_tarfile(make_test_string_2())

    Check the expected files are in the archive.

    >>> tarball.getnames()
    ['test/', 'test/cy.po', 'test/es.po', 'test/test.pot']

    Check the contents.

    >>> f = tarball.extractfile('test/cy.po')
    >>> f.readline()
    '# Test PO file.\n'
    '''

    po = helpers.join_lines(
        '# Test PO file.',
        'msgid "foo"',
        'msgstr "bar"',
        )

    return helpers.make_tarfile({
        'test' : {
            'test.pot' : helpers.join_lines(
                '# Test POT file.',
                'msgid "foo"',
                'msgstr ""',
                ),
            'cy.po' : po,
            'es.po' : po,
            }
        })

def test_make_tarfile():
    """
    >>> s = helpers.make_tarfile({ 'foo' : 'bar', 'zot' : { 'gurgle' : 'sploink' } })
    >>> tarball = helpers.string_to_tarfile(s)
    >>> tarball.getnames()
    ['foo', 'zot/', 'zot/gurgle']
    >>> tarball.extractfile('zot/gurgle').read()
    'sploink'
    """

def test_join_lines():
    r"""
    >>> helpers.join_lines('foo', 'bar', 'baz')
    'foo\nbar\nbaz\n'
    """

def test_find_directories():
    """
    >>> tarball = helpers.string_to_tarfile(make_test_string_1())
    >>> helpers.find_po_directories(tarball)
    ['uberfrob-0.1/blah/po/', 'uberfrob-0.1/po/']
    """

def test_examine_tarfile():
    """
    >>> tarball = helpers.string_to_tarfile(make_test_string_1())
    >>> pot, po = helpers.examine_tarfile(tarball)
    >>> pot
    ('uberfrob-0.1/po/uberfrob.pot',)
    >>> po
    ('uberfrob-0.1/po/cy.po', 'uberfrob-0.1/po/es.po')

    >>> tarball = helpers.string_to_tarfile(make_test_string_2())
    >>> pot, po = helpers.examine_tarfile(tarball)
    >>> pot
    ('test/test.pot',)
    >>> po
    ('test/cy.po', 'test/es.po')
    """

def test_shortest():
    """
    >>> helpers.shortest(['xyzzy', 'foo', 'blah'])
    ['foo']
    >>> helpers.shortest(['xyzzy', 'foo', 'bar'])
    ['foo', 'bar']
    """

def test_simple_popen2():
    r"""
    >>> print helpers.simple_popen2('rev', 'ooF\nraB\nzaB\n')
    Foo
    Bar
    Baz
    <BLANKLINE>
    """

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

