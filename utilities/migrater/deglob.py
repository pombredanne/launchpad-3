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
    interfaces = get_interfaces(types=types, glob_interface=globs)
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
    update_doctest_globs_to_interfaces()


if __name__ == '__main__':
    main()
