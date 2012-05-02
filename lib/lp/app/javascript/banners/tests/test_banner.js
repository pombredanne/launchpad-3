/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.app.banner.test', function (Y) {

    var tests = Y.namespace('lp.app.banner.test');
    tests.suite = new Y.Test.Suite('lp.app.banner Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'banner_tests',

        setUp: function () {},
        tearDown: function () {},

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.app.banner,
                "Could not locate the lp.app.banner module");
        }

    }));

}, '0.1', {'requires': ['test', 'console', 'lp.app.banner']});
