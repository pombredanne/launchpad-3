
import tarfile
import unittest
from StringIO import StringIO

from zope.testing.doctestunit import DocTestSuite

class DummyLanguage:
    def __init__(self, code):
        self.code = code

class DummyPOFile:
    def __init__(self, code, variant):
        self.language = DummyLanguage(code)
        self.variant = variant

class DummyPOTemplate:
    name = 'foo'
    poFiles = [DummyPOFile('bar', None), DummyPOFile('baz', None)]

class BadDummyPOTemplate:
    '''Bad, because it contains a PO file which has a non-None variant.'''

    name = 'fnord'
    poFiles = [DummyPOFile('snap', None), DummyPOFile('crackle', 'pop')]

class DummyExporter:
    def export(self, code):
        return 'dummy export'

def test_POTemplateTarExport():
    '''
    >>> from canonical.launchpad.browser import POTemplateTarExport

    Create a dummy exporter, do the export, and convert the string obtained
    into a tar file object.

    >>> tarexport = POTemplateTarExport()
    >>> tarexport.context = DummyPOTemplate()
    >>> contents = tarexport.make_tar_gz(DummyExporter())
    >>> archive = tarfile.open('', 'r', StringIO(contents))

    Check that the tar file has the expected members.

    >>> members = archive.getmembers()
    >>> [member.name for member in members]
    ['rosetta-foo/', 'rosetta-foo/bar.po', 'rosetta-foo/baz.po']

    Check the contents of one of the members.

    >>> handle = archive.extractfile('rosetta-foo/bar.po')
    >>> handle.read()
    'dummy export'

    Check what happens with a PO template which has a PO file with a variant.

    >>> tarexport = POTemplateTarExport()
    >>> tarexport.context = BadDummyPOTemplate()
    >>> tarexport.make_tar_gz(DummyExporter())
    Traceback (most recent call last):
    ...
    RuntimeError: PO files with variants are not supported.
    '''

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

