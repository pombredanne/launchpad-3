# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import atexit
import itertools
from operator import attrgetter
import types

import __builtin__


original_import = __builtin__.__import__
database_root = 'canonical.launchpad.database'
naughty_imports = set()

# Silence bogus warnings from Hardy's python-pkg-resources package.
import warnings
warnings.filterwarnings('ignore', category=UserWarning, append=True,
                        message=r'Module .*? is being added to sys.path')


def text_lines_to_set(text):
    return set(line.strip() for line in text.splitlines() if line.strip())


permitted_database_imports = text_lines_to_set("""
    canonical.archivepublisher.deathrow
    canonical.archivepublisher.domination
    canonical.archivepublisher.ftparchive
    canonical.archivepublisher.publishing
    lp.codehosting.inmemory
    canonical.launchpad.browser.branchlisting
    lp.code.browser.branchlisting
    canonical.launchpad.browser.librarian
    canonical.launchpad.feed.branch
    lp.code.feed.branch
    canonical.launchpad.interfaces.person
    lp.scripts.garbo
    lp.bugs.vocabulary
    lp.registry.vocabularies
    lp.services.worlddata.vocabularies
    lp.soyuz.vocabularies
    lp.translations.vocabularies
    canonical.librarian.client
    canonical.librarian.db
    doctest
    """)


warned_database_imports = text_lines_to_set("""
    canonical.launchpad.scripts.ftpmaster
    canonical.launchpad.scripts.gina.handlers
    canonical.launchpad.browser.distroseries
    canonical.launchpad.scripts.builddmaster
    lp.translations.scripts.po_import
    canonical.launchpad.systemhomes
    canonical.rosetta
    """)


# Sometimes, third-party modules don't export all of their public APIs through
# __all__. The following dict maps from such modules to a list of attributes
# that are allowed to be imported, whether or not they are in __all__.
valid_imports_not_in_all = {
    'bzrlib.lsprof': set(['BzrProfiler']),
    'cookielib': set(['domain_match']),
    'email.Utils': set(['mktime_tz']),
    'openid.fetchers': set(['Urllib2Fetcher']),
    'storm.database': set(['STATE_DISCONNECTED']),
    'textwrap': set(['dedent']),
    'twisted.internet.threads': set(['deferToThreadPool']),
    'zope.component': set(
        ['adapter',
         'ComponentLookupError',
         'provideAdapter',
         'provideHandler',
         ]),
    }


def database_import_allowed_into(module_path):
    """Return True if database code is allowed to be imported into the given
    module path.  Otherwise, returns False.

    It is allowed if:
        - The import was made with the __import__ hook.
        - The importer is from within canonical.launchpad.database.
        - The importer is a 'test' module.
        - The importer is in the set of permitted_database_imports.
        - The importer is within a model module or package.

    Note that being in the set of warned_database_imports does not make
    the import allowed.

    """
    if (module_path == '__import__ hook' or
        module_path.startswith('canonical.launchpad.database') or
        '.model' in module_path or
        is_test_module(module_path)):
        return True
    return module_path in permitted_database_imports


def is_test_module(module_path):
    """Returns True if the module is for unit or functional tests.

    Otherwise returns False.
    """
    name_splitted = module_path.split('.')
    return ('tests' in name_splitted or
            'ftests' in name_splitted or
            'testing' in name_splitted)


class attrsgetter:
    """Like operator.attrgetter, but works on multiple attribute names."""

    def __init__(self, *names):
        self.names = names

    def __call__(self, obj):
        return tuple(getattr(obj, name) for name in self.names)


class JackbootError(ImportError):
    """Import Fascist says you can't make this import."""

    def __init__(self, import_into, name, *args):
        ImportError.__init__(self, import_into, name, *args)
        self.import_into = import_into
        self.name = name

    def format_message(self):
        return 'Generic JackbootError: %s imported into %s' % (
            self.name, self.import_into)

    def __str__(self):
        return self.format_message()


class DatabaseImportPolicyViolation(JackbootError):
    """Database code is imported directly into other code."""

    def format_message(self):
        return 'You should not import %s into %s' % (
            self.name, self.import_into)


class FromStarPolicyViolation(JackbootError):
    """import * from a module that has no __all__."""

    def format_message(self):
        return ('You should not import * from %s because it has no __all__'
                ' (in %s)' % (self.name, self.import_into))


class NotInModuleAllPolicyViolation(JackbootError):
    """import of a name that does not appear in a module's __all__."""

    def __init__(self, import_into, name, attrname):
        JackbootError.__init__(self, import_into, name, attrname)
        self.attrname = attrname

    def format_message(self):
        return ('You should not import %s into %s from %s,'
                ' because it is not in its __all__.' %
                (self.attrname, self.import_into, self.name))


class NotFoundPolicyViolation(JackbootError):
    """import of zope.exceptions.NotFoundError into
    canonical.launchpad.database.
    """

    def __init__(self, import_into):
        JackbootError.__init__(self, import_into, '')

    def format_message(self):
        return ('%s\nDo not import zope.exceptions.NotFoundError.\n'
                'Use lp.app.errors.NotFoundError instead.'
                % self.import_into)


# The names of the arguments form part of the interface of __import__(...),
# and must not be changed, as code may choose to invoke __import__ using
# keyword arguments - e.g. the encodings module in Python 2.6.
# pylint: disable-msg=W0102,W0602
def import_fascist(name, globals={}, locals={}, fromlist=[], level=-1):
    global naughty_imports

    try:
        module = original_import(name, globals, locals, fromlist, level)
    except ImportError:
        # XXX sinzui 2008-04-17 bug=277274:
        # import_fascist screws zope configuration module which introspects
        # the stack to determine if an ImportError means a module
        # initialization error or a genuine error. The browser:page always
        # tries to load a layer from zope.app.layers first, which most of the
        # time doesn't exist and dies a horrible death because of the import
        # fascist. That's the long explanation for why we special case this
        # module.
        if name.startswith('zope.app.layers.'):
            name = name[16:]
            module = original_import(name, globals, locals, fromlist, level)
        else:
            raise
    # Python's re module imports some odd stuff every time certain regexes
    # are used.  Let's optimize this.
    if name == 'sre':
        return module

    # Mailman 2.1 code base is originally circa 1998, so yeah, no __all__'s.
    if name.startswith('Mailman'):
        return module

    # Some uses of __import__ pass None for globals, so handle that.
    import_into = None
    if globals is not None:
        import_into = globals.get('__name__')

    if import_into is None:
        # We're being imported from the __import__ builtin.
        # We could find out by jumping up the stack a frame.
        # Let's not for now.
        import_into = '__import__ hook'

    # Check the "NotFoundError" policy.
    if (import_into.startswith('canonical.launchpad.database') and
        name == 'zope.exceptions'):
        if fromlist and 'NotFoundError' in fromlist:
            raise NotFoundPolicyViolation(import_into)

    # Check the database import policy.
    if (name.startswith(database_root) and
        not database_import_allowed_into(import_into)):
        error = DatabaseImportPolicyViolation(import_into, name)
        naughty_imports.add(error)
        # Raise an error except in the case of browser.traversers.
        # This exception to raising an error is only temporary, until
        # browser.traversers is cleaned up.
        if import_into not in warned_database_imports:
            raise error

    # Check the import from __all__ policy.
    if fromlist is not None and (
        import_into.startswith('canonical') or import_into.startswith('lp')):
        # We only want to warn about "from foo import bar" violations in our
        # own code.
        fromlist = list(fromlist)
        module_all = getattr(module, '__all__', None)
        if module_all is None:
            if fromlist == ['*']:
                # "from foo import *" is naughty if foo has no __all__
                error = FromStarPolicyViolation(import_into, name)
                naughty_imports.add(error)
                raise error
        else:
            if fromlist == ['*']:
                # "from foo import *" is allowed if foo has an __all__
                return module
            if is_test_module(import_into):
                # We don't bother checking imports into test modules.
                return module
            allowed_fromlist = valid_imports_not_in_all.get(
                name, set())
            for attrname in fromlist:
                # Check that each thing we are importing into the module is
                # either in __all__, is a module itself, or is a specific
                # exception.
                if attrname == '__doc__':
                    # You can always import __doc__.
                    continue
                if isinstance(
                    getattr(module, attrname, None), types.ModuleType):
                    # You can import modules even when they aren't declared in
                    # __all__.
                    continue
                if attrname in allowed_fromlist:
                    # Some things can be imported even if they aren't in
                    # __all__.
                    continue
                if attrname not in module_all:
                    error = NotInModuleAllPolicyViolation(
                        import_into, name, attrname)
                    naughty_imports.add(error)
    return module


def report_naughty_imports():
    if naughty_imports:
        print
        print '** %d import policy violations **' % len(naughty_imports)

        database_violations = []
        fromstar_violations = []
        notinall_violations = []
        sorting_map = {
            DatabaseImportPolicyViolation: database_violations,
            FromStarPolicyViolation: fromstar_violations,
            NotInModuleAllPolicyViolation: notinall_violations,
            }
        for error in naughty_imports:
            sorting_map[error.__class__].append(error)

        if database_violations:
            print
            print "There were %s database import violations." % (
                len(database_violations))
            sorted_violations = sorted(
                database_violations,
                key=attrsgetter('name', 'import_into'))

            for name, sequence in itertools.groupby(
                sorted_violations, attrgetter('name')):
                print "You should not import %s into:" % name
                for import_into, unused_duplicates_seq in itertools.groupby(
                    sequence, attrgetter('import_into')):
                    # Show first occurrence only, to avoid duplicates.
                    print "   ", import_into

        if fromstar_violations:
            print
            print "There were %s imports 'from *' without an __all__." % (
                len(fromstar_violations))
            sorted_violations = sorted(
                fromstar_violations,
                key=attrsgetter('import_into', 'name'))

            for import_into, sequence in itertools.groupby(
                sorted_violations, attrgetter('import_into')):
                print "You should not import * into %s from" % import_into
                for error in sequence:
                    print "   ", error.name

        if notinall_violations:
            print
            print (
                "There were %s imports of names not appearing in the __all__."
                % len(notinall_violations))
            sorted_violations = sorted(
                notinall_violations,
                key=attrsgetter('name', 'attrname', 'import_into'))

            for (name, attrname), sequence in itertools.groupby(
                sorted_violations, attrsgetter('name', 'attrname')):
                print "You should not import %s from %s:" % (attrname, name)
                import_intos = sorted(
                    set([error.import_into for error in sequence]))
                for import_into in import_intos:
                    print "   ", import_into


def install_import_fascist():
    __builtin__.__import__ = import_fascist
    atexit.register(report_naughty_imports)
