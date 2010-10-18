#!/usr/bin/python
#locate all the bad imports in zcml
#create  a set
#for each item in set
#find true path
#replace all occurences.

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


def main():
    update_multi_doctest_globs_to_interfaces()
    update_doctest_globs_to_interfaces()


if __name__ == '__main__':
    main()
