#!/usr/bin/python
#
# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Print the YUI modules we are using."""

from sys import argv

yui_roots = {
    2: 'build/js/yui2',
}
yui_deps = {
    2: [
        'yahoo/yahoo.js',
        'dom/dom.js',
        'event/event.js',
        'yahoo-dom-event/yahoo-dom-event.js',
        'calendar/calendar.js',
    ]
}


if __name__ == '__main__':
    ext = "-%s.js" % argv[1] if len(argv) >= 2 else ".js"
    for version, yui_deps in yui_deps.iteritems():
        yui_root = yui_roots[version]
        for yui_dep in yui_deps:
            # If the yui_dep already has a .js suffix, don't add ext to it.
            if yui_dep.endswith(".js"):
                yui_dep_path = "%s/%s" % (yui_root, yui_dep)
            else:
                yui_dep_path = "%s/%s%s" % (yui_root, yui_dep, ext)
            print yui_dep_path
