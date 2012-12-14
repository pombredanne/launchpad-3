/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.${LIBRARY}.test', function (Y) {

    var tests = Y.namespace('lp.${LIBRARY}.test');
    tests.suite = new Y.Test.Suite('${LIBRARY} Tests');

    tests.suite.add(new Y.Test.Case({
        name: '${LIBRARY}_tests',

        setUp: function () {},
        tearDown: function () {},

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.${LIBRARY},
                "Could not locate the lp.${LIBRARY} module");
        }

    }));

}, '0.1', {
    requires: ['test', 'lp.testing.helpers', 'console', 'lp.${LIBRARY}']
});
