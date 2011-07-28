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

        test_get_packagesets_in_query_no_matching_parameters: function() {
            ArrayAssert.itemsAreSame(
                [], namespace.get_packagesets_in_query(""));
            ArrayAssert.itemsAreSame(
                [], namespace.get_packagesets_in_query("?"));
            ArrayAssert.itemsAreSame(
                [], namespace.get_packagesets_in_query("?foo=bar"));
        },

        test_get_packagesets_in_query_matching_parameters: function() {
            ArrayAssert.itemsAreSame(
                ["foo"], namespace.get_packagesets_in_query(
                    "field.packageset=foo"));
            // A leading question mark is okay.
            ArrayAssert.itemsAreSame(
                ["foo"], namespace.get_packagesets_in_query(
                    "?field.packageset=foo"));
            ArrayAssert.itemsAreSame(
                ["foo", "bar"], namespace.get_packagesets_in_query(
                    "?field.packageset=foo&field.packageset=bar"));
        },

        test_get_packagesets_in_query_numeric_parameters: function() {
            // All-digit parameters are still returned as strings.
            ArrayAssert.itemsAreSame(
                ["123"], namespace.get_packagesets_in_query(
                    "field.packageset=123"));
        },

        test_get_changed_by_in_query: function() {
            Assert.isFunction(namespace.get_changed_by_in_query);
        },

        test_get_changed_by_in_query_no_matching_parameters: function() {
            Assert.isNull(namespace.get_changed_by_in_query(""));
            Assert.isNull(namespace.get_changed_by_in_query("?"));
            Assert.isNull(namespace.get_changed_by_in_query("?foo=bar"));
        },

        test_get_changed_by_in_query_matching_parameters: function() {
            Assert.areSame(
                "foo", namespace.get_changed_by_in_query(
                    "field.changed_by=foo"));
            // A leading question mark is okay.
            Assert.areSame(
                "foo", namespace.get_changed_by_in_query(
                    "?field.changed_by=foo"));
            // Only the first changed_by parameter is returned.
            Assert.areSame(
                "foo", namespace.get_changed_by_in_query(
                    "?field.changed_by=foo&field.changed_by=bar"));
        }

    };

    suite.add(new Y.Test.Case(TestFunctions));

    namespace.suite = suite;

}, "0.1", {"requires": [
               'test', 'console', 'node-event-simulate',
               'lp.registry.distroseries.differences']});
