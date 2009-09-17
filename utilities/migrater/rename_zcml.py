# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities to move zcml to a new location in the tree."""

__metaclass__ = type

__all__ = [
    'handle_zcml',
    ]

import os
import re

from find import find_matches
from lxml import etree
from rename_module import (
    bzr_add, bzr_has_filename, bzr_move_file, bzr_remove_file)


EMPTY_ZCML = """\
<configure
    xmlns="http://namespaces.zope.org/zope"
    xmlns:browser="http://namespaces.zope.org/browser"
    xmlns:i18n="http://namespaces.zope.org/i18n"
    xmlns:xmlrpc="http://namespaces.zope.org/xmlrpc"
    i18n_domain="launchpad"></configure>"""

namespaces = {
    'zope': 'http://namespaces.zope.org/zope',
    'browser': 'http://namespaces.zope.org/browser',
    }


def handle_zcml(
    app_name, old_top, new_top, app_files, app_members, not_moved):
    """Migrate the file if it is ZCML."""
    new_path = os.path.join(new_top, app_name)
    zcml_files = [path for path in app_files if path.endswith('.zcml')]
    for lib_path in zcml_files:
        old_path = os.path.join(old_top, lib_path)
        if not os.path.exists(old_path):
            print "Processing  %s" % old_path
            continue
        migrate_zcml(old_top, old_path, new_path)
        dummy, file_name = os.path.split(old_path)
        rewrite_zcml_class_paths(
            old_top, new_path, file_name, app_members, app_name)
        create_browser_zcml(app_name, new_path, file_name, app_members)
        not_moved.remove(lib_path)
    package_names = consolidate_app_zcml(app_name, new_path)
    register_zcml(package_names, old_top)


def migrate_zcml(old_top, old_path, new_path):
    """Move the ZCML into the new tree and reorganise it."""
    bzr_move_file(old_path, new_path)
    print '%s => %s' % (old_path, new_path)
    # Remove the old registration.
    old_zcml_dir = os.path.join(old_top, 'zcml')
    delete_pattern = r'^.*"%s".*\n' % os.path.basename(old_path)
    for dummy in find_matches(
        old_zcml_dir, 'configure.zcml', delete_pattern, substitution=''):
        print "    Removed old configure include."


def rewrite_zcml_class_paths(old_top, new_path,
                             file_name, app_members, app_name):
    """Rewrite app classes to use relative paths."""
    abs_lib = 'canonical\.launchpad'
    module_name, dummy = os.path.splitext(file_name)
    for package_name in app_members:
        try:
            members = '|'.join(app_members[package_name][module_name])
        except KeyError:
            old_module_path = os.path.join(
                old_top, package_name, '%s.py' % module_name)
            if os.path.isfile(old_module_path):
                print '    ** missing %s.%s' % (package_name, module_name)
            continue
        module_pattern = r'\b%s(\.%s\.)(?:\w*\.)?(%s)\b' % (
            abs_lib, package_name, members)
        substitution = r'lp.%s\1%s.\2' % (app_name, module_name)
        for dummy in find_matches(
            new_path, file_name, module_pattern, substitution=substitution):
            # This function is an iterator, but we do not care about the
            # summary of what is changed.
            pass
    # Update the menu and navigation directives.
    module_pattern = r'module="canonical.launchpad.browser"'
    substitution = r'module="lp.%s.browser.%s"' % (app_name, module_name)
    for dummy in find_matches(
        new_path, file_name, module_pattern, substitution=substitution):
        pass


def create_browser_zcml(app_name, new_path, file_name, app_members):
    """Extract browser ZCML to the browser/ directory."""
    module_name, dummy = os.path.splitext(file_name)
    browser_module_name = '.browser.%s' % module_name
    new_file_path = os.path.join(new_path, file_name)
    source = open(new_file_path)
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(source, parser)
    finally:
        source.close()
    doc = tree.getroot()
    browser_doc = etree.fromstring(EMPTY_ZCML)
    # Move the facet browser directives first.
    for facet_node in doc.xpath('./zope:facet', namespaces=namespaces):
        facet = facet_node.get('facet')
        browser_facet = etree.Element('facet', facet=facet)
        for node in facet_node.xpath('./browser:*', namespaces=namespaces):
            facet_node.remove(node)
            browser_facet.append(node)
        if len(browser_facet) > 0:
            browser_doc.append(browser_facet)
    # All remaining browser directives can be moved.
    for node in doc.xpath('./browser:*', namespaces=namespaces):
        doc.remove(node)
        browser_doc.append(node)
    # Split the menus directive into two nodes, one for the this app, and
    # one for the old Launchpad app.
    module_class_path = "lp.%s.browser.%s" % (app_name, module_name)
    other_class_path = "canonical.launchpad.browser"
    for node in browser_doc.xpath('./browser:menus', namespaces=namespaces):
        app_menus = []
        other_menus = []
        module_members = app_members['browser'][module_name]
        for menu in node.get('classes').split():
            if menu in module_members:
                app_menus.append(menu)
            else:
                other_menus.append(menu)
        if len(other_menus) > 0:
            browser_doc.append(
                create_menu_node(other_class_path, other_menus))
        if len(app_menus) > 0:
            browser_doc.append(
                create_menu_node(module_class_path, app_menus))
        browser_doc.remove(node)
    # Only save the browser and other doc if information was put into them.
    if len(browser_doc) > 0:
        file_path = os.path.join(new_path, 'browser', file_name)
        write_zcml_file(file_path, browser_doc)
        write_zcml_file(new_file_path, doc)


def create_menu_node(module, menus):
    """Create a browser:menus node for the module and list of menu classes."""
    menus_tag = '{%s}menus' % namespaces['browser']
    classes = ' '.join(menus)
    return etree.Element(
        menus_tag, module=module, classes=classes, nsmap=namespaces)


def write_zcml_file(file_path, doc):
    """Write the zcml file to its location."""
    xml = format_xml(etree.tostring(doc, pretty_print=True))
    browser_file = open(file_path, 'w')
    try:
        browser_file.write(xml)
    finally:
        browser_file.close()


def format_xml(xml):
    """Format the xml for pretty printing."""
    lines = []
    leading_pattern = re.compile(r'^( *)<')
    attribute_pattern = re.compile(r' ([\w:]+=)')
    open_comment_pattern = re.compile(r'(<!--)')
    close_comment_pattern = re.compile(r'(-->)')
    classes_pattern = re.compile(
        r'( +)(classes|attributes)(=")([^"]+)')
    trailing_whitespace_pattern = re.compile(r'\s+$')
    for line in xml.splitlines():
        match = leading_pattern.match(line)
        if match is None:
            leading = ''
        else:
            leading = match.group(1)
            if len(leading) > 8:
                # lxml does not normalise whitespace between closing tags.
                leading = '        '
                line = leading + line.strip()
        line = open_comment_pattern.sub(r'\n%s\1' % leading, line)
        line = close_comment_pattern.sub(r'\1\n%s' % leading, line)
        line = attribute_pattern.sub(r'\n  %s\1' % leading, line)
        classes = classes_pattern.search(line)
        if classes is not None:
            indent = classes.group(1)
            modules = classes.group(4).split()
            module_indent = '\n  %s' % indent
            markup = r'\1\2\3' + module_indent + module_indent.join(modules)
            line = classes_pattern.sub(markup, line)
        lines.append(line)
    xml = '\n'.join(lines)
    xml = trailing_whitespace_pattern.sub('', xml)
    xml = xml.replace('  ', '    ')
    return xml


def consolidate_app_zcml(app_name, dir_path):
    """Consolidate the all the app zcml into configure.zcml."""
    consolidate_zcml(dir_path)
    consolidate_zcml(os.path.join(dir_path, 'browser'))
    # This function should also create the coop/<module>.zcml files and
    # build a list of each one so that they can be registered. The registry
    # doesn't have coop files, so it just returns a list of its own name.
    return [app_name]


def consolidate_zcml(dir_path):
    """Consolidate the directory zcml into configure.zcml."""
    all_lines = []
    if os.path.isdir(os.path.join(dir_path, 'browser')):
        # This configure.zcml must include the browser package.
        all_lines.append('\n    <include package=".browser" />')
    converted_zcml = []
    for file_name in os.listdir(dir_path):
        if not file_name.endswith('.zcml') or file_name == 'configure.zcml':
            # This is not a single zcml file.
            continue
        file_path = os.path.join(dir_path, file_name)
        zcml_file = open(file_path)
        in_root = False
        after_root = False
        try:
            for line in zcml_file:
                if '</configure>' not in line and after_root:
                    all_lines.append(line)
                    continue
                if not in_root and '<configure' in line:
                    in_root = True
                if in_root and '>' in line:
                    after_root = True
        finally:
            zcml_file.close()
        converted_zcml.append(file_path)
    configure_xml = EMPTY_ZCML.replace('><', '>%s<' % ''.join(all_lines))
    configure_path = os.path.join(dir_path, 'configure.zcml')
    if os.path.isfile(configure_path):
        configure_path = configure_path + '.extra'
        print '    ** Warning %s must be reconciled with configure.zcml ' % (
            configure_path)
    parser = etree.XMLParser(remove_blank_text=True)
    doc = etree.fromstring(configure_xml, parser=parser)
    write_zcml_file(configure_path, doc)
    bzr_add([configure_path])
    for file_path in converted_zcml:
        if bzr_has_filename(file_path):
            bzr_remove_file(file_path)
        else:
            os.remove(file_path)


def register_zcml(package_names, old_top):
    """Register the new zcml in Launchpad's config."""
    # Package names could be like: ['answers', 'coop.answersbugs']
    for package_name in package_names:
        include = r'<include package="lp\.%s" />' % package_name
        unregistered = False
        for dummy in find_matches(old_top, 'configure.zcml', include):
            # The module is already registered.
            unregistered = True
        if unregistered:
            continue
        insert_after = r'(<include package="canonical.launchpad.xmlrpc" />)'
        include = r'\1\n\n  <include package="lp.%s" />' % package_name
        for dummy in find_matches(
            old_top, 'configure.zcml', insert_after, substitution=include):
            pass


# Verify the formatter is sane.
if __name__ == '__main__':
    source = open('lib/lp/registry/browser/configure.zcml')
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(source, parser)
    finally:
        source.close()
    doc = tree.getroot()
    write_zcml_file('./test.xml', doc)
