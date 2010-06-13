#!/usr/bin/python
#locate all the bad imports in zcml
#create  a set
#for each item in set
#find true path
#replace all occurences.

from find import find_matches


def get_interfaces():
    interfaces = set()
    root = 'lib'
    types = r'\.(zcml)'
    glob_interface = r'\bcanonical\.launchpad\.interfaces.(I\w*)\b'
    for summary in find_matches(root, types, glob_interface):
        for line in summary['lines']:
            interfaces.add(line['match'].group(1))
    return interfaces


def get_interface_modules(interfaces):
    interface_modules = {}
    root = 'lib'
    types = r'interfaces/.*\.py'
    interface_def = r'\bclass (%s)\b'
    for interface in interfaces:
        for summary in find_matches(root, types, interface_def % interface):
            # Chop lib/ and .py from the string and repace the slash with dot.
            module_ = summary['file_path'][4:-3].replace('/', '.')
            interface_modules[interface] = module_
            break
    return interface_modules


def update_globs_to_interfaces(interface_modules):
    root = 'lib'
    types = r'\.(zcml)'
    glob_interface = r'\b(canonical\.launchpad\.interfaces.%s)\b'
    for interface, module_ in interface_modules.items():
        pattern = glob_interface % interface
        substitution = '%s.%s' % (module_, interface)
        for summary in find_matches(
            root, types, pattern, substitution=substitution):
            print "\n%(file_path)s" % summary
            for line in summary['lines']:
                print "    %(lineno)4s: %(text)s" % line


def main():
    interfaces = get_interfaces()
    interface_modules = get_interface_modules(interfaces)
    update_globs_to_interfaces(interface_modules)


if __name__ == '__main__':
    main()
