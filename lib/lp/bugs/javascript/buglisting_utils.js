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

    /**
     * Private object to reference defaults for field_visibility.
     */
    _field_visibility_defaults = {
        show_bugtarget: true,
        show_bug_heat: true,
        show_id: true,
        show_importance: true,
        show_status: true,
        show_title: true,
        show_milestone_name: false
    };

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
        },


        /**
         * A config for field visibility.  This determines which
         * fields are visibile in a bug listing.
         *
         * @attribute field_visibility
         * @type Object
         */
        field_visibility: {
            valueFn: function() {
                return _field_visibility_defaults;
            },
            setter: function(value) {
                var defaults = _field_visibility_defaults;
                return Y.merge(defaults, value);
            }
        },

        /**
         * A reference to the form overlay used in the overlay.
         *
         * @attribute form
         * @type Y.lazr.FormOverlay
         * @default null
         */
        form: {
            value: null
        }
    };

    Y.extend(BugListingConfigUtil, Y.lp.configutils.BaseConfigUtil, {});

    var buglisting_utils = Y.namespace('lp.buglisting_utils');
    buglisting_utils.BugListingConfigUtil = BugListingConfigUtil;

}, '0.1', {'requires': ['lp.configutils']});
