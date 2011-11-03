/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.baseconfig.test', function(Y) {

var baseconfig_test = Y.namespace('lp.baseconfig.test');

var suite = new Y.Test.Suite('BaseConfig Tests');

var Assert = Y.Assert;

suite.add(new Y.Test.Case({

    name: 'baseconfig_widget_tests',

    test_basic_test: function() {
        Assert.isTrue(false);
    }

}));

baseconfig_test.suite = suite;

}, '0.1', {'requires': ['test', 'node-event-simulate']});
