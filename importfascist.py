# Copyright Canonical Limited 2005.  All rights reserved.

import __builtin__
import atexit
import itertools
import types
from operator import attrgetter

original_import = __builtin__.__import__
database_root = 'canonical.launchpad.database'
naughty_imports = set()


def text_lines_to_set(text):
    return set(line.strip() for line in text.splitlines() if line.strip())


# zope.testing.doctest: called as part of creating a DocTestSuite.
permitted_database_imports = text_lines_to_set("""
    zope.testing.doctest
    canonical.librarian.db
    canonical.doap.fileimporter
    canonical.foaf.nickname
    canonical.archivepublisher.ftparchive
    canonical.archivepublisher.publishing
    canonical.archivepublisher.domination
    canonical.archivepublisher.deathrow
    canonical.authserver.database
    canonical.launchpad.vocabularies.dbobjects
    canonical.librarian.client
    importd.Job
    """)


warned_database_imports = text_lines_to_set("""
    canonical.launchpad.scripts.ftpmaster
    canonical.launchpad.scripts.gina.handlers
    canonical.launchpad.browser.distroseries
    canonical.launchpad.scripts.builddmaster
    canonical.launchpad.scripts.po_import
    canonical.launchpad.systemhomes
    canonical.rosetta
    """)


def database_import_allowed_into(module_path):
    """Return True if database code is allowed to be imported into the given
    module path.  Otherwise, returns False.

    It is allowed if:
        - The import was made with the __import__ hook.
        - The importer is from within canonical.launchpad.database.
        - The importer is a 'test' module.
        - The importer is in the set of permitted_database_imports.

    Note that being in the set of warned_database_imports does not make
    the import allowed.

    """
    if (module_path == '__import__ hook' or
        module_path.startswith('canonical.launchpad.database') or
        is_test_module(module_path)):
        return True
    return module_path in permitted_database_imports


def is_test_module(module_path):
    """Returns True if the module is for unit or functional tests.

    Otherwise returns False.
    """
    name_splitted = module_path.split('.')
    return 'tests' in name_splitted or 'ftests' in name_splitted


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
                'Use canonical.launchpad.interfaces.NotFoundError instead.'
                % self.import_into)


def import_fascist(name, globals={}, locals={}, fromlist=[]):
    try:
        module = original_import(name, globals, locals, fromlist)
    except:
        #if 'layers' in name:
        #    import pdb; pdb.set_trace()
        raise
    # Python's re module imports some odd stuff every time certain regexes
    # are used.  Let's optimize this.
    # Also, 'dedent' is not in textwrap.__all__.
    if name == 'sre' or name == 'textwrap':
        return module

    global naughty_imports

    # Some uses of __import__ pass None for globals, so handle that.
    import_into = None
    if globals is not None:
        import_into = globals.get('__name__')

    if import_into is None:
        # We're being imported from the __import__ builtin.
        # We could find out by jumping up the stack a frame.
        # Let's not for now.
        import_into = '__import__ hook'
    if (import_into.startswith('canonical.launchpad.database') and
        name == 'zope.exceptions'):
        if fromlist and 'NotFoundError' in fromlist:
            raise NotFoundPolicyViolation(import_into)
    if (name.startswith(database_root) and
        not database_import_allowed_into(import_into)):
        error = DatabaseImportPolicyViolation(import_into, name)
        naughty_imports.add(error)
        # Raise an error except in the case of browser.traversers.
        # This exception to raising an error is only temporary, until
        # browser.traversers is cleaned up.
        if import_into not in warned_database_imports:
            raise error

    if fromlist is not None and import_into.startswith('canonical'):
        # We only want to warn about "from foo import bar" violations in our 
        # own code.
        if list(fromlist) == ['*'] and not hasattr(module, '__all__'):
            # "from foo import *" is naughty if foo has no __all__
            error = FromStarPolicyViolation(import_into, name)
            naughty_imports.add(error)
            raise error
        elif (list(fromlist) != ['*'] and hasattr(module, '__all__') and
              not is_test_module(import_into)):
            # "from foo import bar" is naughty if bar isn't in foo.__all__ (and
            # foo actually has an __all__).  Unless foo is within a tests
            # or ftests module or bar is itself a module.
            for attrname in fromlist:
                if attrname != '__doc__' and attrname not in module.__all__:
                    if not isinstance(
                        getattr(module, attrname, None), types.ModuleType):
                        error = NotInModuleAllPolicyViolation(
                            import_into, name, attrname)
                        naughty_imports.add(error)
                        # Not raising on NotInModuleAllPolicyViolation yet.
                        #raise error
    return module


def report_naughty_imports():
    if naughty_imports:
        print
        print '** %d import policy violations **' % len(naughty_imports)
        current_type = None

        database_violations = []
        fromstar_violations = []
        notinall_violations = []
        sorting_map = {
            DatabaseImportPolicyViolation: database_violations,
            FromStarPolicyViolation: fromstar_violations,
            NotInModuleAllPolicyViolation: notinall_violations
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
