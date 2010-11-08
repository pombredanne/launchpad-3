#!/usr/bin/python
#locate all the bad imports in zcml
#create  a set
#for each item in set
#find true path
#replace all occurences.

import os
import sys

from find import find_matches


def get_interfaces(types=None, globs=None):
    interfaces = set()
    root = 'lib'
    if types is None:
        types = r'\.(zcml)'
    if globs is None:
        globs = r'\bcanonical\.launchpad\.interfaces.(I\w*)\b'
    for summary in find_matches(root, types, globs):
        for line in summary['lines']:
            interfaces.add(line['match'].group(1))
    return interfaces


def get_interface_modules(interfaces):
    interface_modules = {}
    root = 'lib'
    types = r'(errors|enums|interfaces).*\.py'
    interface_def = r'\bclass (%s)\b'
    for interface in interfaces:
        for summary in find_matches(root, types, interface_def % interface):
            # Chop lib/ and .py from the string and repace the slash with dot.
            module_ = summary['file_path'][4:-3].replace('/', '.')
            interface_modules[interface] = module_
            break
    return interface_modules


def update_zcml_globs_to_interfaces():
    root = 'lib'
    types = r'\.(zcml)'
    globs = r'\bcanonical\.launchpad\.interfaces.(I\w*)\b'
    interfaces = get_interfaces(types=types, glob_interface=globs)
    interface_modules = get_interface_modules(interfaces)
    glob_interface = r'\b(canonical\.launchpad\.interfaces.%s)\b'
    for interface, module_ in interface_modules.items():
        pattern = glob_interface % interface
        substitution = '%s.%s' % (module_, interface)
        for summary in find_matches(
            root, types, pattern, substitution=substitution):
            print "\n%(file_path)s" % summary
            for line in summary['lines']:
                print "    %(lineno)4s: %(text)s" % line


def update_doctest_globs_to_interfaces():
    root = 'lib'
    types = r'\.(txt)'
    globs = r'from \bcanonical\.launchpad\.interfaces import (\w+)$'
    interfaces = get_interfaces(types=types, globs=globs)
    interface_modules = get_interface_modules(interfaces)
    glob_interface = r'\b(from canonical\.launchpad\.interfaces import %s)\b'
    for interface, module_ in interface_modules.items():
        pattern = glob_interface % interface
        substitution = 'from %s import %s' % (module_, interface)
        for summary in find_matches(
            root, types, pattern, substitution=substitution):
            print "\n%(file_path)s" % summary
            for line in summary['lines']:
                print "    %(lineno)4s: %(text)s" % line


def multiline_extract_match(file_path, match_re, substitution=None):
    """Return a summary of matches in a file."""
    lines = []
    content = []
    match = None
    file_ = open(file_path, 'r')
    in_match = False
    current_match = None
    try:
        for lineno, line in enumerate(file_):
            if in_match:
                identifiers = line.split(',')
                for idf in identifiers:
                    idf = idf.strip()
                    idf = idf.strip('...')
                    idf = idf.strip()
                    if idf.endswith(')'):
                        in_match = False
                        idf = idf[0:-1]
                    idf = idf.strip()
                    if idf == '':
                        continue
                    expanded_line = (
                        '%s %s\n' % (current_match.group(0), idf))
                    lines.append(
                        {'lineno': lineno + 1, 'text': expanded_line.strip(),
                         'match': None})
                    if substitution is not None:
                        content.append(expanded_line)
                    if not in_match:
                        current_match = None
                continue
            # Else check if this is the start of a multi-line.
            match = match_re.search(line)
            if match and line.strip().endswith('('):
                in_match = True
                current_match = match
                continue
            # Always append the non-matching lines to content to rebuild
            # the file.
            if substitution is not None:
                content.append(line)
    finally:
        file_.close()
    if lines:
        if substitution is not None:
            file_ = open(file_path, 'w')
            try:
                file_.write(''.join(content))
            finally:
                file_.close()
        return {'file_path': file_path, 'lines': lines}
    return None


def update_multi_doctest_globs_to_interfaces():
    root = 'lib'
    types = r'\.(txt)'
    pattern = r'[ ]+>>> from canonical\.launchpad\.interfaces import'
    substitution = True
    for summary in find_matches(
        root, types, pattern, substitution=substitution,
        extract_match=multiline_extract_match):
        print "\n%(file_path)s" % summary
        for line in summary['lines']:
            print "    %(lineno)4s: %(text)s" % line


def normalize_doctest_imports(file_path, match_re, substitution=None):
    """Return a summary of matches in a file."""
    lines = []
    content = []
    match = None
    file_ = open(file_path, 'r')
    in_match = False
    imports = None
    try:
        for lineno, line in enumerate(file_):
            match = match_re.search(line)
            # Start match imports.
            if match and not in_match:
                in_match = True
                whitespace = match.group(1)
                imports = {}
                # Fall-through.
            # Store the collected imports.
            if match:
                module_ = match.group(2)
                if module_ not in imports:
                    imports[module_] = []
                imports[module_].append(match.group(3))
                continue
            # If the import section is passed, normalize the imports.
            if not match and in_match:
                module_names = sorted(imports.keys())
                # Put zope modules first.
                zopes = list(module_names)
                zopes.reverse()
                for name in zopes:
                    if name.startswith('zope'):
                        module_names.remove(name)
                        module_names.insert(0, name)
                    else:
                        break
                for module_ in module_names:
                    identifiers = sorted(imports[module_])
                    if len(identifiers) == 1:
                        expanded_line = (
                            '%s>>> from %s import %s\n' %
                            (whitespace, module_, identifiers[0]))
                    else:
                        continuation = ',\n%s...     ' % whitespace
                        idfs = continuation.join(identifiers)
                        expanded_line = (
                            '%s>>> from %s import (%s%s%s)\n' %
                            (whitespace, module_,
                             continuation[1:], idfs, continuation))
                    lines.append(
                        {'lineno': lineno + 1, 'text': expanded_line.strip(),
                         'match': None})
                    if substitution is not None:
                        content.append(expanded_line)
                # Clear imports.
                in_match = False
                imports = None
                # Append the current line.
                if substitution is not None:
                    content.append(line)
                continue
            # Always append the non-matching lines to content to rebuild
            # the file.
            if substitution is not None:
                content.append(line)
    finally:
        file_.close()
    if lines:
        if substitution is not None:
            file_ = open(file_path, 'w')
            try:
                file_.write(''.join(content))
            finally:
                file_.close()
        return {'file_path': file_path, 'lines': lines}
    return None


def normalize_all_doctest_imports():
    root = 'lib'
    types = r'\.(txt)'
    pattern = r'^([ ]+)>>> from ([\w.]+) import ([\w.]+)$'
    substitution = True
    for summary in find_matches(
        root, types, pattern, substitution=substitution,
        extract_match=normalize_doctest_imports):
        print "\n%(file_path)s" % summary
        for line in summary['lines']:
            print "    %(lineno)4s: %(text)s" % line


def update_multi_python_globs_to_interfaces(root='lib', types='tests'):
    pattern=r'from canonical\.launchpad\.interfaces import'
    substitution = True
    for summary in find_matches(
        root, types, pattern, substitution=substitution,
        extract_match=multiline_extract_match):
        print "\n%(file_path)s" % summary
        for line in summary['lines']:
            print "    %(lineno)4s: %(text)s" % line


def update_python_globs_to_interfaces(root='lib', types='tests'):
    update_multi_python_globs_to_interfaces(root=root, types=types)
    globs = r'from \bcanonical\.launchpad\.interfaces import (\w+)$'
    interfaces = get_interfaces(types=types, globs=globs)
    interface_modules = get_interface_modules(interfaces)
    glob_interface = r'\b(from canonical\.launchpad\.interfaces import %s)\b'
    for interface, module_ in interface_modules.items():
        pattern = glob_interface % interface
        substitution = 'from %s import %s' % (module_, interface)
        for summary in find_matches(
            root, types, pattern, substitution=substitution):
            print "\n%(file_path)s" % summary
            for line in summary['lines']:
                print "    %(lineno)4s: %(text)s" % line


def main():
    if len(sys.argv) != 3:
        print 'Usage: %s root_path file_test', os.path.basename(sys.argv[0])
        sys.exit(1)
    root = sys.argv[1]
    types = sys.argv[2]
    update_python_globs_to_interfaces(root, types)


if __name__ == '__main__':
    main()
