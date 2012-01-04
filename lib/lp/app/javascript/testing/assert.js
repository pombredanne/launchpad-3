/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.testing.assert', function(Y) {
    /**
     * A utility module for use in YUI unit-tests with custom asserts
     *
     * @module lp.testing.mockio
     */
    var namespace =  Y.namespace("lp.testing.assert");

    /**
     * Assert that two structures are equal by comparing their json form.
     */
    namespace.assert_equal_structure = function(expected, actual){
        Y.Assert.areEqual(JSON.stringify(expected), JSON.stringify(actual));
    };
}, '0.1', {'requires': []});
