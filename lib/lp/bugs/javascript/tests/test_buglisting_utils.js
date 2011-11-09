/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.buglisting_utils.test', function(Y) {

var buglisting_utils = Y.namespace('lp.buglisting_utils.test');

var suite = new Y.Test.Suite('BugListingConfigUtil Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;
var ObjectAssert = Y.ObjectAssert;

suite.add(new Y.Test.Case({

    name: 'buglisting_display_utils_tests',

    tearDown: function() {
        if (Y.Lang.isValue(this.list_util)) {
            this.list_util.destroy();
        }
    },

    /**
     * Unpack a list of key, name pairs into individual lists.
     *
     * [[Foo, 'Foo Item'], ['Bar', 'Bar item']] becomes
     * ['Foo', 'Bar'] and ['Foo Item', 'Bar Item'].
     */
    getClassesAndNames: function(keys) {
        var classes = [];
        var names = [];
        var len = keys.length;
        var i;
        for (i=0; i<len; i++) {
            classes.push(keys[i][0]);
            names.push(keys[i][1]);
        }
        return [classes, names];
    },

    test_bug_listing_util_extends_base_util: function() {
        // BugListingConfigUtil extends from BaseConfigUtil.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        Assert.isInstanceOf(Y.lp.configutils.BaseConfigUtil, this.list_util);
    },

    test_default_display_keys: function() {
        // The default display keys should exist in a new widget.
        var expected_display_keys = [
            ['bugnumber', 'Bug number'],
            ['bugtitle', 'Bug title'],
            ['importance', 'Importance'],
            ['status', 'Status'],
            ['bug-heat-icons', 'Bug heat']
        ];
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        var expected = this.getClassesAndNames(expected_display_keys);
        var actual = this.getClassesAndNames(
            this.list_util.get('display_keys'));
        ArrayAssert.itemsAreSame(expected[0], actual[0]);
        ArrayAssert.itemsAreSame(expected[1], actual[1]);
    },

    test_default_field_visibility_config: function() {
        // The default field_visibility should exist in a new widget.
        var expected_config = {
            show_bugtarget: true,
            show_bug_heat: true,
            show_id: true,
            show_importance: true,
            show_status: true,
            show_title: true,
            show_milestone_name: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        ObjectAssert.areEqual(
            expected_config, this.list_util.get('field_visibility'));
    },

    test_supplied_field_visibility_config: function() {
        // field_visibility can be changed at the call site.
        // Supplied fields will be merged with the defaults.
        var supplied_config = {
            show_bugtarget: false,
            show_bug_heat: false
        };
        var expected_config = {
            show_bugtarget: false,
            show_bug_heat: false,
            show_id: true,
            show_importance: true,
            show_status: true,
            show_title: true,
            show_milestone_name: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: supplied_config
        });
        ObjectAssert.areEqual(
            expected_config, this.list_util.get('field_visibility'));
    },

    test_field_visibility_form_reference: function() {
        // The form created from field_visibility defaults is referenced
        // via BugListingConfigUtil.get('form')
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        Assert.isNotUndefined(this.list_util.get('form'));
    },

    test_field_visibility_form_shows_defaults: function() {
        // The form should have a checkbox for every default item,
        // and the checked value should match true or false values.

    },

    test_field_visibility_form_shows_supplied_defaults: function() {
        // The form checkboxes should also match the user supplied
        // config values.

    },

    test_field_visibility_form_update_config: function() {
        // Changing elements on the form also updates the field_visibility
        // config values.

    },

    test_fields_visibility_form_reset: function() {
        // Clicking "reset to defaults" on the form returns
        // field_visibility to its default values.

    }

}));

buglisting_utils.suite = suite;

}, '0.1', {'requires': [
    'test', 'node-event-simulate', 'lp.buglisting_utils']});
