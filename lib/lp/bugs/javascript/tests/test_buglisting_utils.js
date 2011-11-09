/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.buglisting_utils.test', function(Y) {

var buglisting_utils = Y.namespace('lp.buglisting_utils.test');

var suite = new Y.Test.Suite('BugListingConfigUtil Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;
var ObjectAssert = Y.ObjectAssert;

suite.add(new Y.Test.Case({

    name: 'buglisting_display_utils_tests',

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
        var blutil = new Y.lp.buglisting_utils.BugListingConfigUtil();
        Assert.isInstanceOf(Y.lp.configutils.BaseConfigUtil, blutil);
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
        var blutil = new Y.lp.buglisting_utils.BugListingConfigUtil();
        var expected = this.getClassesAndNames(expected_display_keys);
        var actual = this.getClassesAndNames(blutil.get('display_keys'));
        ArrayAssert.itemsAreSame(expected[0], actual[0]);
        ArrayAssert.itemsAreSame(expected[1], actual[1]);
    },

    test_default_display_config: function() {
        // The default field_visibility should exist in a new widget.
        var expected_config = {
            show_bugtarget: true,
            show_bug_heat: true,
            show_id: true,
            show_importance: true,
            show_status: true,
            show_title: true,
            show_milestone_name: false
        }
        var blutil = new Y.lp.buglisting_utils.BugListingConfigUtil();
        ObjectAssert.areEqual(
            expected_config, blutil.get('field_visibility'));
    }

}));

buglisting_utils.suite = suite;

}, '0.1', {'requires': [
    'test', 'node-event-simulate', 'lp.buglisting_utils']});
