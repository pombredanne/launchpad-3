/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Tests for DistroSeries Differences.
 *
 * @module lp.registry.distroseries.differences
 * @submodule test
 */

YUI.add('lp.registry.distroseries.differences.test', function(Y) {

    var namespace = Y.namespace('lp.registry.distroseries.differences.test');

    var Assert = Y.Assert;
    var ArrayAssert = Y.ArrayAssert;

    var suite = new Y.Test.Suite("distroseries.differences Tests");
    var differences = Y.lp.registry.distroseries.differences;

    var TestFunctions = {
        name: 'TestFunctions',

        test_get_packagesets_in_query: function() {
            Assert.isFunction(namespace.get_packagesets_in_query);
        },

        test_get_changed_by_in_query: function() {
            Assert.isFunction(namespace.get_changed_by_in_query);
        }

    };

    suite.add(new Y.Test.Case(TestFunctions));

    namespace.suite = suite;

}, "0.1", {"requires": [
               'test', 'console', 'node-event-simulate',
               'lp.registry.distroseries.differences']});
