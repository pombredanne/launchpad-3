
from StringIO import StringIO

from zope.testing.doctestunit import DocTestSuite

from canonical.lp import initZopeless
from canonical.launchpad.scripts.rosetta import attach
from canonical.launchpad.helpers import join_lines, RosettaWriteTarFile
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestSetup
from canonical.librarian.ftests.harness import LibrarianTestSetup

files = {
    'directories.txt': join_lines(
        'foo',
        'bar',
    ),
    'translations.txt': join_lines(
        'File: pmount_0.7.2-2_translations.tar.gz',
        'Distribution: ubuntu',
        'Release: hoary',
        'Component: main',
        'Source: pmount',
        'Version: 0.7.2-2',
        '',
        'File: evolution_2.2.0-0ubuntu2_translations.tar.gz',
        'Distribution: ubuntu',
        'Release: hoary',
        'Component: main',
        'Source: evolution',
        'Version: 2.4.0-0ubuntu1',
    ),
    'translations.tar.gz': RosettaWriteTarFile.files_to_string({
        'source/po/template.pot': 'foo',
        'source/po/es/po': 'bar',
    }),
}

class FakeURLOpener:
    def open(self, url):
        bits = url.split('/')
        key = bits[-1]

        for key in files:
            if url.endswith(key):
                return StringIO(files[key])

        raise RuntimeError("unexpeted URL", url)

class FakeLogger:
    def __init__(self):
        self.log = []

    def append(self, *args):
        self.log.append(' '.join([str(arg) for arg in args]))

    def error(self, *args, **kw):
        self.append("ERROR", args, kw)

        if 'exc_info' in kw:
            import sys
            import traceback
            exc_info = sys.exc_info()
            self.append(exc_info[0])
            self.append(exc_info[1])
            tb = traceback.format_tb(exc_info[2])
            for line in tb:
                self.append(line[:-1])

    def warning(self, *args, **kw):
        self.append("WARNING", *args)

    def info(self, *args, **kw):
        self.append("INFO", *args)

    def debug(self, *args, **kw):
        self.append("DEBUG", *args)

def test():
    """
    Set up stuff.

    >>> LaunchpadFunctionalTestSetup().setUp()
    >>> LibrarianTestSetup().setUp()
    >>> login(ANONYMOUS)

    >>> class FakeTransactionManager:
    ...     def commit(self):
    ...         pass
    ...
    ...     def abort(self):
    ...         pass
    ...
    >>> ztm = FakeTransactionManager()

    Get our mock objects, and set attach() loose on them.

    >>> urlopener = FakeURLOpener()
    >>> logger = FakeLogger()
    >>> attach(urlopener, archive_uri='foo', ztm=ztm, logger=logger)
    >>> for line in logger.log:
    ...     print line
    INFO Getting foo/foo/pmount_0.7.2-2_translations.tar.gz
    DEBUG foo/foo/pmount_0.7.2-2_translations.tar.gz attached to pmount sourcepackage
    INFO Getting foo/foo/evolution_2.2.0-0ubuntu2_translations.tar.gz
    DEBUG foo/foo/evolution_2.2.0-0ubuntu2_translations.tar.gz attached to evolution sourcepackage
    WARNING Creating new PO template name 'review-hoary-evolution-1'
    WARNING Creating new PO template 'review-hoary-evolution-1' for hoary/evolution
    INFO Getting foo/bar/pmount_0.7.2-2_translations.tar.gz
    DEBUG foo/bar/pmount_0.7.2-2_translations.tar.gz attached to pmount sourcepackage
    DEBUG This tarball or a newer one is already imported. Ignoring it.
    INFO Getting foo/bar/evolution_2.2.0-0ubuntu2_translations.tar.gz
    DEBUG foo/bar/evolution_2.2.0-0ubuntu2_translations.tar.gz attached to evolution sourcepackage
    DEBUG This tarball or a newer one is already imported. Ignoring it.

    >>> LibrarianTestSetup().tearDown()
    >>> LaunchpadFunctionalTestSetup().tearDown()
    """

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

