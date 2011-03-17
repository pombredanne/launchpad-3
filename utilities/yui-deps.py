#!/usr/bin/python
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Print the YUI modules we are using."""

from sys import argv


yui_root = 'lib/canonical/launchpad/icing/yui'
yui_deps = [
    'yui/yui',
    'oop/oop',
    'dom/dom',
    'dom/dom-style-ie',
    'event-custom/event-custom',
    'event/event',
    'pluginhost/pluginhost',
    'node/node',
    'event/event-base-ie',
    'node/align-plugin',
    'attribute/attribute',
    'base/base',
    'anim/anim',
    'async-queue/async-queue',
    'json/json',
    'plugin/plugin',
    'cache/cache',
    'classnamemanager/classnamemanager',
    'collection/collection',
    'dump/dump',
    'intl/intl',
    'substitute/substitute',
    'widget/widget',
    'widget/widget-base-ie',
    'console/lang/console.js',
    'console/console',
    'console/console-filters',
    'cookie/cookie',
    'dataschema/dataschema',
    'datatype/lang/datatype.js',
    'datatype/datatype',
    'querystring/querystring-stringify-simple',
    'queue-promote/queue-promote',
    'io/io',
    'datasource/datasource',
    'dd/dd',
    'dd/dd-gestures',
    'dd/dd-drop-plugin',
    'event/event-touch',
    'event-gestures/event-gestures',
    'dd/dd-plugin',
    'dom/selector-css3',
    'editor/editor',
    'event-simulate/event-simulate',
    'event-valuechange/event-valuechange',
    'escape/escape',
    'text/text-data-wordbreak',
    'text/text-wordbreak',
    'text/text-data-accentfold',
    'text/text-accentfold',
    'highlight/highlight',
    'history/history',
    'history/history-hash-ie',
    'history-deprecated/history-deprecated',
    'imageloader/imageloader',
    'jsonp/jsonp',
    'jsonp/jsonp-url',
    'loader/loader',
    'node/node-event-simulate',
    'transition/transition',
    'node-flick/node-flick',
    'node-focusmanager/node-focusmanager',
    'node-menunav/node-menunav',
    'widget/widget-position',
    'widget/widget-position-align',
    'widget/widget-position-constrain',
    'widget/widget-stack',
    'widget/widget-stdmod',
    'overlay/overlay',
    'profiler/profiler',
    'querystring/querystring',
    'querystring/querystring-parse-simple',
    'scrollview/scrollview-base',
    'scrollview/scrollview-base-ie',
    'scrollview/scrollview-scrollbars',
    'scrollview/scrollview',
    'scrollview/scrollview-paginator',
    'node/shim-plugin',
    'slider/slider',
    'sortable/sortable',
    'sortable/sortable-scroll',
    'stylesheet/stylesheet',
    'swfdetect/swfdetect',
    'swf/swf',
    'tabview/tabview-base',
    'widget/widget-child',
    'widget/widget-parent',
    'tabview/tabview',
    'tabview/tabview-plugin',
    'test/test',
    'uploader/uploader',
    'widget-anim/widget-anim',
    'widget/widget-locale',
    'yql/yql',
]


if __name__ == '__main__':
    ext = "-%s.js" % argv[1] if len(argv) >= 2 else ".js"
    for yui_dep in yui_deps:
        # If the yui_dep already has a .js suffix, don't add ext to it.
        if yui_dep.endswith(".js"):
            yui_dep_path = "%s/%s" % (yui_root, yui_dep)
        else:
            yui_dep_path = "%s/%s%s" % (yui_root, yui_dep, ext)
        print yui_dep_path
