/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.buglisting_utils', function(Y) {
    /**
     * blah, blah, blah.
     *
     * @module lp.buglisting_utils
     */
    function BugListingConfigUtil() {
        BugListingConfigUtil.superclass.constructor.apply(this, arguments);
    }

    BugListingConfigUtil.NAME = 'buglistingconfigutil';

    BugListingConfigUtil.ATTRS = {

        /**
         * A list of [key, name] pairs where key is the class name
         * used to select the element in the DOM, and the name is
         * the display name for the item in the widget.
         *
         * @attribute display_keys
         * @type Array
         */
        display_keys: {
            value: [
                ['bugnumber', 'Bug number'],
                ['bugtitle', 'Bug title'],
                ['importance', 'Importance'],
                ['status', 'Status'],
                ['bug-heat-icons', 'Bug heat']
            ]
        }
    };

    Y.extend(BugListingConfigUtil, Y.lp.configutils.BaseConfigUtil, {});

    var buglisting_utils = Y.namespace('lp.buglisting_utils');
    buglisting_utils.BugListingConfigUtil = BugListingConfigUtil;

}, '0.1', {'requires': ['lp.configutils']});
