/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.buglisting_config.test', function(Y) {

var buglisting_config = Y.namespace('lp.buglisting_config.test');

var suite = new Y.Test.Suite('BugListingDisplayConfig Tests');

var Assert = Y.Assert;

suite.add(new Y.Test.Case({

    name: 'buglisting_display_config_tests',

    test_basic_starting_test: function() {
        Assert.isTrue(false);
    },

}));

buglisting_config.suite = suite;

}, '0.1', {'requires': [
    'test', 'node-event-simulate', 'lp.buglisting_config']});
