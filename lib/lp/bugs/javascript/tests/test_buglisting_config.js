/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.buglisting_config.test', function(Y) {

var buglisting_config = Y.namespace('lp.buglisting_config.test');

var suite = new Y.Test.Suite('BugListingConfigUtil Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;

suite.add(new Y.Test.Case({

    name: 'buglisting_display_config_tests',

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

    test_default_display_keys : function() {
        // The default display keys should exist in a new widget.
        var expected_display_keys = [
            ['bugnumber', 'Bug number'],
            ['bugtitle', 'Bug title'],
            ['importance', 'Importance'],
            ['status', 'Status'],
            ['bug-heat-icons', 'Bug heat']
        ];
        var blconfig = new Y.lp.buglisting_utils.BugListingConfigUtil();
        var expected = this.getClassesAndNames(expected_display_keys);
        var actual = this.getClassesAndNames(blconfig.get('display_keys'));
        ArrayAssert.itemsAreSame(expected[0], actual[0]);
        ArrayAssert.itemsAreSame(expected[1], actual[1]);
    }

}));

buglisting_config.suite = suite;

}, '0.1', {'requires': [
    'test', 'node-event-simulate', 'lp.buglisting_config']});
