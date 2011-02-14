#!/usr/bin/python
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Print the YUI modules we are using."""

yui_deps = [
    './lib/canonical/launchpad/icing/yui/yui/yui-min.js',
    './lib/canonical/launchpad/icing/yui/oop/oop-min.js',
    './lib/canonical/launchpad/icing/yui/dom/dom-min.js',
    './lib/canonical/launchpad/icing/yui/dom/dom-style-ie-min.js',
    './lib/canonical/launchpad/icing/yui/event-custom/event-custom-min.js',
    './lib/canonical/launchpad/icing/yui/event/event-min.js',
    './lib/canonical/launchpad/icing/yui/pluginhost/pluginhost-min.js',
    './lib/canonical/launchpad/icing/yui/node/node-min.js',
    './lib/canonical/launchpad/icing/yui/event/event-base-ie-min.js',
    './lib/canonical/launchpad/icing/yui/node/align-plugin-min.js',
    './lib/canonical/launchpad/icing/yui/attribute/attribute-min.js',
    './lib/canonical/launchpad/icing/yui/base/base-min.js',
    './lib/canonical/launchpad/icing/yui/anim/anim-min.js',
    './lib/canonical/launchpad/icing/yui/async-queue/async-queue-min.js',
    './lib/canonical/launchpad/icing/yui/json/json-min.js',
    './lib/canonical/launchpad/icing/yui/plugin/plugin-min.js',
    './lib/canonical/launchpad/icing/yui/cache/cache-min.js',
    './lib/canonical/launchpad/icing/yui/classnamemanager/classnamemanager-min.js',
    './lib/canonical/launchpad/icing/yui/collection/collection-min.js',
    './lib/canonical/launchpad/icing/yui/dump/dump-min.js',
    './lib/canonical/launchpad/icing/yui/intl/intl-min.js',
    './lib/canonical/launchpad/icing/yui/substitute/substitute-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-base-ie-min.js',
    './lib/canonical/launchpad/icing/yui/console/lang/console.js',
    './lib/canonical/launchpad/icing/yui/console/console-min.js',
    './lib/canonical/launchpad/icing/yui/console/console-filters-min.js',
    './lib/canonical/launchpad/icing/yui/cookie/cookie-min.js',
    './lib/canonical/launchpad/icing/yui/dataschema/dataschema-min.js',
    './lib/canonical/launchpad/icing/yui/datatype/lang/datatype.js',
    './lib/canonical/launchpad/icing/yui/datatype/datatype-min.js',
    './lib/canonical/launchpad/icing/yui/querystring/querystring-stringify-simple-min.js',
    './lib/canonical/launchpad/icing/yui/queue-promote/queue-promote-min.js',
    './lib/canonical/launchpad/icing/yui/io/io-min.js',
    './lib/canonical/launchpad/icing/yui/datasource/datasource-min.js',
    './lib/canonical/launchpad/icing/yui/dd/dd-min.js',
    './lib/canonical/launchpad/icing/yui/dd/dd-gestures-min.js',
    './lib/canonical/launchpad/icing/yui/dd/dd-drop-plugin-min.js',
    './lib/canonical/launchpad/icing/yui/event/event-touch-min.js',
    './lib/canonical/launchpad/icing/yui/event-gestures/event-gestures-min.js',
    './lib/canonical/launchpad/icing/yui/dd/dd-gestures-min.js',
    './lib/canonical/launchpad/icing/yui/dd/dd-plugin-min.js',
    './lib/canonical/launchpad/icing/yui/dom/dom-style-ie-min.js',
    './lib/canonical/launchpad/icing/yui/dom/selector-css3-min.js',
    './lib/canonical/launchpad/icing/yui/editor/editor-min.js',
    './lib/canonical/launchpad/icing/yui/event-simulate/event-simulate-min.js',
    './lib/canonical/launchpad/icing/yui/event-valuechange/event-valuechange-min.js',
    './lib/canonical/launchpad/icing/yui/escape/escape-min.js',
    './lib/canonical/launchpad/icing/yui/text/text-data-wordbreak-min.js',
    './lib/canonical/launchpad/icing/yui/text/text-wordbreak-min.js',
    './lib/canonical/launchpad/icing/yui/text/text-data-accentfold-min.js',
    './lib/canonical/launchpad/icing/yui/text/text-accentfold-min.js',
    './lib/canonical/launchpad/icing/yui/highlight/highlight-min.js',
    './lib/canonical/launchpad/icing/yui/history/history-min.js',
    './lib/canonical/launchpad/icing/yui/history/history-hash-ie-min.js',
    './lib/canonical/launchpad/icing/yui/history-deprecated/history-deprecated-min.js',
    './lib/canonical/launchpad/icing/yui/history/history-hash-ie-min.js',
    './lib/canonical/launchpad/icing/yui/imageloader/imageloader-min.js',
    './lib/canonical/launchpad/icing/yui/jsonp/jsonp-min.js',
    './lib/canonical/launchpad/icing/yui/jsonp/jsonp-url-min.js',
    './lib/canonical/launchpad/icing/yui/loader/loader-min.js',
    './lib/canonical/launchpad/icing/yui/node/node-event-simulate-min.js',
    './lib/canonical/launchpad/icing/yui/transition/transition-min.js',
    './lib/canonical/launchpad/icing/yui/node-flick/node-flick-min.js',
    './lib/canonical/launchpad/icing/yui/node-focusmanager/node-focusmanager-min.js',
    './lib/canonical/launchpad/icing/yui/node-menunav/node-menunav-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-position-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-position-align-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-position-constrain-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-stack-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-stdmod-min.js',
    './lib/canonical/launchpad/icing/yui/overlay/overlay-min.js',
    './lib/canonical/launchpad/icing/yui/profiler/profiler-min.js',
    './lib/canonical/launchpad/icing/yui/querystring/querystring-min.js',
    './lib/canonical/launchpad/icing/yui/querystring/querystring-parse-simple-min.js',
    './lib/canonical/launchpad/icing/yui/scrollview/scrollview-base-min.js',
    './lib/canonical/launchpad/icing/yui/scrollview/scrollview-base-ie-min.js',
    './lib/canonical/launchpad/icing/yui/scrollview/scrollview-scrollbars-min.js',
    './lib/canonical/launchpad/icing/yui/scrollview/scrollview-min.js',
    './lib/canonical/launchpad/icing/yui/scrollview/scrollview-paginator-min.js',
    './lib/canonical/launchpad/icing/yui/node/shim-plugin-min.js',
    './lib/canonical/launchpad/icing/yui/slider/slider-min.js',
    './lib/canonical/launchpad/icing/yui/sortable/sortable-min.js',
    './lib/canonical/launchpad/icing/yui/sortable/sortable-scroll-min.js',
    './lib/canonical/launchpad/icing/yui/stylesheet/stylesheet-min.js',
    './lib/canonical/launchpad/icing/yui/swfdetect/swfdetect-min.js',
    './lib/canonical/launchpad/icing/yui/swf/swf-min.js',
    './lib/canonical/launchpad/icing/yui/tabview/tabview-base-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-child-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-parent-min.js',
    './lib/canonical/launchpad/icing/yui/tabview/tabview-min.js',
    './lib/canonical/launchpad/icing/yui/tabview/tabview-plugin-min.js',
    './lib/canonical/launchpad/icing/yui/test/test-min.js',
    './lib/canonical/launchpad/icing/yui/uploader/uploader-min.js',
    './lib/canonical/launchpad/icing/yui/widget-anim/widget-anim-min.js',
    './lib/canonical/launchpad/icing/yui/widget/widget-locale-min.js',
    './lib/canonical/launchpad/icing/yui/yql/yql-min.js',
]

for line in yui_deps:
    print line
