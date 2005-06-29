
import doctest
import unittest

def is_valid_mofile(mofile):
    """Test whether a string is a valid MO file."""

    # There are different magics for big- and little-endianness, so we test
    # for both.
    be_magic = '\x95\x04\x12\xde'
    le_magic = ''.join(reversed(be_magic))

    for magic in (be_magic, le_magic):
        if mofile[:len(magic)] == magic:
            return True

    return False

def test_mo_compiler():
    """
    >>> from canonical.launchpad.components.poexport import MOCompiler
    >>> compiler = MOCompiler()

    >>> mofile = compiler.compile('''
    ... msgid "foo"
    ... msgstr "bar"
    ... ''')
    >>> is_valid_mofile(mofile)
    True

    >>> mofile = compiler.compile('''
    ... blah
    ... ''')
    Traceback (most recent call last):
    ...
    MOCompilationError: PO file compilation failed:
    <stdin>:2: keyword "blah" unknown
    <stdin>:2:1: parse error
    /usr/bin/msgfmt: found 2 fatal errors
    <BLANKLINE>
    """

def test_suite():
    return doctest.DocTestSuite()

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

