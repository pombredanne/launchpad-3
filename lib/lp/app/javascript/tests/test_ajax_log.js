/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.ajax_log.test', function (Y) {

    var tests = Y.namespace('lp.ajax_log.test');
    tests.suite = new Y.Test.Suite('ajax_log Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'ajax_log_tests',

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.ajax_log,
                "Could not locate the lp.ajax_log module");
        }

    }));

}, '0.1', {'requires': ['test', 'console', 'lp.ajax_log']});
