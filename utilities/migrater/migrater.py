#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Migrate modules from the old LP directory structure to the new using
a control file and the exising mover script that Francis wrote.
"""

import errno
import os
import re

from find import find_files, find_matches
from optparse import OptionParser
from rename_module import (
    bzr_add, bzr_move_file, bzr_remove_file, rename_module, update_references)
from rename_zcml import handle_zcml
from utils import log, run, spew


MOVER = os.path.join(os.path.dirname(__file__), 'rename_module.py')

TLA_MAP = dict(
    ans='answers',
    app='app',
    blu='blueprints',
    bug='bugs',
    cod='code',
    reg='registry',
    sha='shared',
    soy='soyuz',
    svc='services',
    tes='testing',
    tra='translations',
    pkg='registry',
    hdb='hardwaredb',
    )

RENAME_MAP = dict(
    components='adapters',
    database='model',
    ftests='tests',
    pagetests='stories',
    )

OLD_TOP = 'lib/canonical/launchpad'
NEW_TOP = 'lib/lp'

APP_DIRECTORIES = [
    'adapters',
    'browser',
    'doc',
    'emailtemplates',
    'event',
    'feed',
    'interfaces',
    'model',
    'notifications',
    'scripts',
    'stories',
    'subscribers',
    'templates',
    'tests',
    'browser/tests',
    ]

TEST_PATHS = set(('doc', 'tests', 'ftests', 'pagetests'))
# Ripped straight from GNU touch(1)
FLAGS = os.O_WRONLY | os.O_CREAT | os.O_NONBLOCK | os.O_NOCTTY


def parse_args():
    """Return a tuple of parser, option, and arguments."""
    usage = """\
%prog [options] controlfile app_codes+

controlfile is the file containing the list of files to be moved.  Each file
is prefixed with a TLA identifying the apps.

app_codes is a list of TLAs identifying the apps to migrate.
"""
    parser = OptionParser(usage)
    parser.add_option(
        '--dryrun',
        action='store_true', default=False, dest='dry_run',
        help=("If this option is used actions will be printed "
              "but not executed."))
    parser.add_option(
        '--no-move',
        action='store_false', default=True, dest='move',
        help="Don't actually move any files, just set up the app's tree.")

    options, arguments = parser.parse_args()
    return parser, options, arguments


def convert_ctl_data(data):
    """Return a dict of files, each keyed to an app."""
    app_data = {}
    for line in data:
        try:
            tla, fn = line.split()
        except ValueError:
            continue
        if not tla in app_data:
            app_data[tla] = []
        app_data[tla].append(fn[2:])
    return app_data

COLLIDED = []


def move_it(old_path, new_path):
    """Move a versioned file without colliding with another file."""
    # Move the file and fix the imports.  LBYL.
    if os.path.exists(new_path):
        if os.path.getsize(new_path) == 0:
            # We must remove the file since bzr refuses to clobber existing
            # files.
            bzr_remove_file(new_path)
        else:
            log('COLLISION! target already exists: %s', new_path)
            COLLIDED.append(new_path)
            # Try to find an alternative.  I seriously doubt we'll ever have
            # more than two collisions.
            for counter in range(10):
                fn, ext = os.path.splitext(new_path)
                new_target = fn + '_%d' % counter + ext
                log('    new target: %s', new_target)
                if not os.path.exists(new_target):
                    new_path = new_target
                    break
            else:
                raise AssertionError('Too many collisions: ' + new_path)
    rename_module(old_path, new_path)


def make_tree(app):
    """Make the official tree structure."""
    if not os.path.exists(NEW_TOP):
        os.mkdir(NEW_TOP)
    tld = os.path.join(NEW_TOP, TLA_MAP[app])

    for directory in [''] + APP_DIRECTORIES:
        d = os.path.join(tld, directory)
        try:
            os.mkdir(d)
            bzr_add(d)
            print "created", d
        except OSError, e:
            if e.errno == errno.EEXIST:
                # The directory already exists, so assume that the __init__.py
                # file also exists.
                continue
            else:
                raise
        else:
            # Touch an empty __init__.py to make the thing a package.
            init_file = os.path.join(d, '__init__.py')
            fd = os.open(init_file, FLAGS, 0666)
            os.close(fd)
            bzr_add(init_file)
    # Add the whole directory.
    bzr_add(tld)


def file2module(module_file):
    """From a filename, return the python module name."""
    start_path = 'lib' + os.path.sep
    module_file, dummy = os.path.splitext(module_file)
    module = module_file[len(start_path):].replace(os.path.sep, '.')
    return module


def handle_script(old_path, new_path):
    """Move a script or directory and update references in cronscripts."""
    parts = old_path.split(os.path.sep)
    if (len(parts) - parts.index('scripts')) > 2:
        # The script is a directory not a single-file module.
        # Just get the directory portion and move everything at once.
        old_path = os.path.join(*parts[:-1])
        new_full_path = new_path
    else:
        # The script is a single-file module.  Add the script name to the end
        # of new_path.
        new_full_path = os.path.join(new_path, parts[-1])

    # Move the file or directory
    bzr_move_file(old_path, new_path)
    # Update references, but only in the cronscripts directory.
    source_module = file2module(old_path)
    target_module = file2module(new_full_path)
    update_references(source_module, target_module)
    update_helper_imports(old_path, new_full_path)


def map_filename(path):
    """Return the renamed file name."""
    fn, dummy = os.path.splitext(path)
    if fn.endswith('-pages'):
        # Don't remap -pages doctests here.
        return path
    else:
        return os.sep.join(RENAME_MAP.get(path_part, path_part)
                           for path_part in path.split(os.sep))


def handle_test(old_path, new_path):
    """Migrate tests."""
    spew('handle_test(%s, %s)', old_path, new_path)
    unsupported_dirs = [
        'components',
        'daemons',
        'model',
        'interfaces',
        'mail',
        'mailout',
        'translationformat',
        'utilities',
        'validators',
        'vocabularies',
        'webapp',
        'xmlrpc',
        ]
    new_path = map_filename(new_path)
    # Do target -pages.txt doctest remapping.
    file_name, ext = os.path.splitext(new_path)
    if file_name.endswith('-pages'):
        new_path = file_name[:-6] + '-views' + ext
        parts = new_path.split(os.sep)
        index = parts.index('doc')
        parts[index:index + 1] = ['browser', 'tests']
        new_path = os.sep.join(parts)
    if '/tests/' in new_path and '/browser/tests/' not in new_path:
        # All unit tests except to browser unit tests move to the app
        # tests dir.
        new_path = os.sep.join(
            path_part for path_part in new_path.split(os.sep)
            if path_part not in unsupported_dirs)
    # Create new_path's directory if it doesn't exist yet.
    try:
        test_dir, dummy = os.path.split(new_path)
        os.makedirs(test_dir)
        spew('created: %s', test_dir)
    except OSError, error:
        if error.errno != errno.EEXIST:
            raise
    else:
        # Add the whole directory.
        run('bzr', 'add', test_dir)
    move_it(old_path, new_path)
    dir_path, file_name = os.path.split(old_path)
    if file_name.endswith('py') and not file_name.startswith('test_'):
        update_helper_imports(old_path, new_path)


def update_helper_imports(old_path, new_path):
    """Fix the references to the test helper."""
    old_dir_path, file_name = os.path.split(old_path)
    old_module_path = file2module(old_dir_path).replace('.', '\\.')
    module_name, dummy = os.path.splitext(file_name)
    new_module_path = file2module(os.path.dirname(new_path))
    source = r'\b%s(\.| import )%s\b' % (old_module_path, module_name)
    target = r'%s\1%s' % (new_module_path, module_name)
    root_dirs = ['cronscripts', 'lib/canonical', 'lib/lp']
    file_pattern = '\.(py|txt|zcml)$'
    print source, target
    print "    Updating references:"
    for root_dir in root_dirs:
        for summary in find_matches(
            root_dir, file_pattern, source, substitution=target):
            print "        * %(file_path)s" % summary


def setup_test_harnesses(app_name):
    """Create the doctest harnesses."""
    app_path = os.path.join(NEW_TOP, app_name)
    doctest_path = os.path.join(app_path, 'doc')
    doctests = [file_name
                for file_name in os.listdir(doctest_path)
                if file_name.endswith('.txt')]
    print 'Installing doctest harnesses'
    install_doctest_suite(
        'test_doc.py', os.path.join(app_path, 'tests'), doctests=doctests)
    install_doctest_suite(
        'test_views.py', os.path.join(app_path, 'browser', 'tests'))


def install_doctest_suite(file_name, dir_path, doctests=None):
    """Copy the simple doctest builder."""
    test_doc_path = os.path.join(
        os.path.dirname(__file__), file_name)
    test_doc_file = open(test_doc_path, 'r')
    try:
        test_doc = test_doc_file.read()
    finally:
        test_doc_file.close()
    if doctests is not None:
        test_doc = test_doc.replace('special = {}', get_special(doctests))
    test_doc_path = os.path.join(dir_path, file_name)
    if os.path.isfile(test_doc_path):
        # This harness was made in a previous run.
        print "    Skipping %s, it was made in a previous run" % test_doc_path
        return
    test_doc_file = open(test_doc_path, 'w')
    try:
        test_doc_file.write(test_doc)
    finally:
        test_doc_file.close()
    bzr_add([test_doc_path])


def get_special(doctests):
    """extract the special setups from test_system_documentation."""
    system_doc_lines = []
    special_lines = []
    doctest_pattern = re.compile(r"^    '(%s)[^']*':" % '|'.join(doctests))
    system_doc_path = os.path.join(
        OLD_TOP, 'ftests', 'test_system_documentation.py')
    system_doc = open(system_doc_path)
    try:
        in_special = False
        for line in system_doc:
            match = doctest_pattern.match(line)
            if match is not None:
                in_special = True
                print '    * Extracting special test for %s' % match.group(1)
            if in_special:
                special_lines.append(line.replace('        ', '    '))
            else:
                system_doc_lines.append(line)
            if in_special and '),' in line:
                in_special = False
    finally:
        system_doc.close()
    if len(special_lines) == 0:
        # There was nothing to extract.
        return 'special = {}'
    # Get the setup and teardown functions.
    special_lines.insert(0, 'special = {\n')
    special_lines.append('    }')
    code = ''.join(special_lines)
    helper_pattern = re.compile(r'\b(setUp|tearDown)=(\w*)\b')
    helpers = set(match.group(2) for match in helper_pattern.finditer(code))
    if 'setUp' in helpers:
        helpers.remove('setUp')
    if 'tearDown' in helpers:
        helpers.remove('tearDown')
    # Extract the setup and teardown functions.
    lines = list(system_doc_lines)
    system_doc_lines = []
    helper_lines = []
    helper_pattern = re.compile(r'^def (%s)\b' % '|'.join(helpers))
    in_helper = False
    for line in lines:
        if in_helper and len(line) > 1 and line[0] != ' ':
            in_helper = False
        match = helper_pattern.match(line)
        if match is not None:
            in_helper = True
            print '    * Extracting special function for %s' % match.group(1)
        if in_helper:
            helper_lines.append(line)
        else:
            system_doc_lines.append(line)
    if len(helper_lines) > 0:
        code = ''.join(helper_lines) + code
    # Write the smaller test_system_documentation.py.
    system_doc = open(system_doc_path, 'w')
    try:
        system_doc.write(''.join(system_doc_lines))
    finally:
        system_doc.close()
    # Return the local app's specials code.
    special_lines.insert(0, 'special = {\n')
    special_lines.append('    }')
    return code


def handle_py_file(old_path, new_path, subdir):
    """Migrate python files."""
    if subdir in APP_DIRECTORIES:
        # We need the full path, including file name.
        move_it(old_path, new_path)
        return True
    else:
        return False


def get_all_module_members(app_name):
    """Return a dict of dicts of lists; package, module, members."""
    all_members = {}
    package_names = ['interfaces', 'model', 'browser', 'components']
    member_pattern = r'^(?:class|def) (?P<name>[\w]*)'
    for package_name in package_names:
        root_dir = os.path.join(NEW_TOP, app_name, package_name)
        module_names = {}
        for summary in find_matches(root_dir, 'py$', member_pattern):
            members = []
            for line in summary['lines']:
                members.append(line['match'].group('name'))
            module_name, dummy = os.path.splitext(
                os.path.basename(summary['file_path']))
            # Reverse sorting avoids false-positive matches in REs.
            module_names[module_name] = sorted(members, reverse=True)
        all_members[package_name] = module_names
    return all_members


def one_true_import(app_name, all_members):
    """Replace glob inports from interfaces to avoid circular imports."""
    app_path = os.path.join(NEW_TOP, app_name)
    print "Replace glob inports from interfaces to avoid circular imports."
    all_interfaces = get_all_interfaces()
    for file_path in find_files(app_path, file_pattern='py$'):
        fix_file_true_import(file_path, all_interfaces)


def fix_file_true_import(file_path, all_interfaces):
    """Fix the interface imports in a file."""
    from textwrap import fill
    bad_pattern = 'from canonical.launchpad.interfaces import'
    delimiters_pattern = re.compile(r'[,()]+')
    import_lines = []
    content = []
    in_import = False
    changed = False
    file_ = open(file_path, 'r')
    try:
        for line in file_:
            if in_import and len(line) > 1 and line[0] != ' ':
                in_import = False
                # Build a dict of interfaces used.
                bad_import = delimiters_pattern.sub(
                    ' ', ''.join(import_lines))
                identifiers = bad_import.split()[3:]
                modules = {}
                for identifier in identifiers:
                    if identifier not in all_interfaces:
                        print '        * missing %s' % identifier
                        continue
                    modules.setdefault(
                        all_interfaces[identifier], []).append(identifier)
                good_imports = []
                # Build the import code from the dict.
                for module_path in sorted(modules):
                    symbols = ', '.join(sorted(modules[module_path]))
                    if len(symbols) > 78 - len(bad_pattern):
                        symbols = '(\n%s)' % fill(
                            symbols, width=78,
                            initial_indent='    ', subsequent_indent='    ')
                    good_imports.append(
                        'from %s import %s\n' % (module_path, symbols))
                # Insert the good imports into the module.
                content.extend(good_imports)
            if line.startswith(bad_pattern):
                in_import = True
                changed = True
                import_lines = []
                print '    Fixing interface imports in %s' % file_path
            if in_import:
                import_lines.append(line)
            else:
                content.append(line)
    finally:
        file_.close()
    if changed:
        file_ = open(file_path, 'w')
        try:
            file_.write(''.join(content))
        finally:
            file_.close()


def get_all_interfaces():
    """return a dict of interface member and module path."""
    # {'IPersonSet', 'lp.registrty.interfaces.person'}
    all_interfaces = {}
    member_pattern = r'^(?:class |def )*(?P<name>[\w]*)'
    for summary in find_matches(
        '.', '(canonical|lp)/.*/interfaces.*\.py$', member_pattern):
        module_path, dummy = os.path.splitext(summary['file_path'])
        module_path = module_path.replace('./lib/', '')
        assert module_path.startswith('lp') or module_path.startswith('ca'), (
            '!! Bad module path.')
        module_path = module_path.replace('/', '.')
        for line in summary['lines']:
            all_interfaces[line['match'].group('name')] = module_path
    return all_interfaces


def handle_templates(app):
    """Migrate the page templates referenced in the zcml."""
    new_browser_path = os.path.join(NEW_TOP, TLA_MAP[app], 'browser')
    new_template_path = os.path.join(NEW_TOP, TLA_MAP[app], 'templates')
    templates = set()
    missing_templates = []
    shared_templates = []
    for summary in find_matches(
        new_browser_path, '\.zcml$', r'template="\.\./([^"]+)"'):
        for line in summary['lines']:
            file_name = line['match'].group(1)
            templates.add(os.path.join(OLD_TOP, file_name))
    # Some views have the template file in the code.
    for summary in find_matches(
        new_browser_path, '\.py$', r"""\.\./(templates/[^"']+)"""):
        for line in summary['lines']:
            file_name = line['match'].group(1)
            if 'xrds' in file_name:
                # xrds files belong to OpenID and account. Fix the single
                # reference in the registry tree.
                old_template = (
                    "../../../canonical/launchpad/templates/person-xrds.pt")
                for dummy in find_matches(
                    new_browser_path, 'person.py',
                    '../templates/person-xrds.pt', substitution=old_template):
                    pass
                continue
            templates.add(os.path.join(OLD_TOP, file_name))
    print "Processing templates"
    for template_path in templates:
        if not os.path.isfile(template_path):
            missing_templates.append(template_path)
            continue
        if is_shared_template(template_path):
            shared_templates.append(template_path)
            continue
        bzr_move_file(template_path, new_template_path)
    if len(missing_templates) > 0:
        print "zcml references unknown templates:"
        for file_path in missing_templates:
            print '    %s' % file_path
    if len(shared_templates) > 0:
        print "Warning: many apps reference these templates (fix by hand):"
        for template_path in shared_templates:
            file_name = os.path.basename(template_path)
            print '    %s' % file_name
            # Update the template reference in the browser/*zcml.
            pattern = r'(template=")\.\./(templates/%s)"' % file_name
            substitution = r'\1../../../canonical/launchpad/\2"'
            for summary in find_matches(
                new_browser_path, '\.zcml$', pattern,
                substitution=substitution):
                pass


def is_shared_template(template_path):
    """Return true if the template is referenced in the old zcml."""
    old_zcml_path = os.path.join(OLD_TOP, 'zcml')
    file_name = os.path.basename(template_path)
    for dummy in find_matches(old_zcml_path, '\.zcml$', file_name):
        return True
    return False


def main(ctl_data, apps, opts):
    """Migrate applications."""
    # Get a dict keyed by app TLA with all files for that app.
    app_to_files = convert_ctl_data(ctl_data)

    if len(apps) == 1 and apps[0] == 'all':
        apps = app_to_files.keys()

    not_moved = []
    for app in apps:
        if app not in app_to_files:
            print "No files tagged for app", app
            continue
        if app not in TLA_MAP:
            print 'Unknown file owner:', app
            continue

        app_name = TLA_MAP[app]
        make_tree(app)
        if not opts.move:
            continue

        app_files = app_to_files[app]
        for fpath in app_files:
            if fpath.endswith('.zcml'):
                # ZCML is processed after modules are moved.
                not_moved.append(fpath)
                continue
            print "Processing:", fpath
            full_path = os.path.join(OLD_TOP, fpath)
            if not os.path.exists(full_path):
                # The module has already been moved, ignore.
                continue
            to_path = map_filename(fpath)
            path, file_name = os.path.split(to_path)
            spew("    to_path = %s", to_path)
            new_path_to_dir = os.path.join(NEW_TOP, app_name, path)
            new_path_to_fn = os.path.join(NEW_TOP, app_name, to_path)
            # Special cases.
            if set(fpath.split(os.sep)) & TEST_PATHS:
                handle_test(full_path, new_path_to_fn)
                continue
            subdir = to_path.split(os.sep)[0]
            if subdir in ['scripts']:
                handle_script(full_path, new_path_to_dir)
                continue
            # Only process python modules.
            if file_name.endswith('.py'):
                if handle_py_file(full_path, new_path_to_fn, subdir):
                    continue

            not_moved.append(fpath)

        # Create the test harnesses for the moved tests.
        setup_test_harnesses(app_name)
        # Replace glob imports from interfaces to avoid circular nonsense.
        app_members = get_all_module_members(app_name)
        one_true_import(app_name, app_members)
        # Migrate the zcml.
        handle_zcml(
            app_name, OLD_TOP, NEW_TOP, app_files, app_members, not_moved)
        # Move templates referenced by the moved zcml and view classes.
        handle_templates(app)

        # Warn about the files that weren't moved.
        if len(not_moved) > 0:
            print ("Warning:  the following did not have a rule to "
                   "move them.  They are left unchanged.")
            for nm in not_moved:
                print "  ", nm
        # Warn about collisions.
        if len(COLLIDED) > 0:
            print ("Warning:  the following files collided and need to be "
                   "manually fixed.")
            for pow in COLLIDED:
                print "  ", pow


if __name__ == '__main__':
    parser, opts, args = parse_args()
    if len(args) < 2:
        parser.error('Control file and at least one app is required')

    ctl_fn = args[0]
    apps = args[1:]

    ctl_data = open(ctl_fn, 'r').readlines()
    main(ctl_data, apps, opts)
