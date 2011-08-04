/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Tests for Extras.
 *
 * @module lp.extras
 * @submodule test
 */

YUI.add('lp.extras.test', function(Y) {

    var namespace = Y.namespace('lp.extras.test');

    var Assert = Y.Assert;
    var ArrayAssert = Y.ArrayAssert;

    var suite = new Y.Test.Suite("extras Tests");
    var extras = Y.lp.extras;

    var TestNodeListMap = {
        name: 'TestNodeListMap',

        test_static: function() {
            var nodes = [
                Y.Node.create("<div />"),
                Y.Node.create("<label />"),
                Y.Node.create("<strong />")
            ];
            ArrayAssert.itemsAreSame(
                nodes,
                Y.NodeList.map(
                    nodes, function(node) { return node; })
            );
            ArrayAssert.itemsAreSame(
                ["DIV", "LABEL", "STRONG"],
                Y.NodeList.map(nodes, function(node) {
                    return node.get("tagName");
                })
            );
        },

        test_method: function() {
            var nodes = [
                Y.Node.create("<div />"),
                Y.Node.create("<label />"),
                Y.Node.create("<strong />")
            ];
            var nodelist = new Y.NodeList(nodes);
            ArrayAssert.itemsAreSame(
                nodes,
                nodelist.map(function(node) { return node; })
            );
            ArrayAssert.itemsAreSame(
                ["DIV", "LABEL", "STRONG"],
                nodelist.map(function(node) {
                    return node.get("tagName");
                })
            );
        }

    };

    suite.add(new Y.Test.Case(TestNodeListMap));

    // Exports.
    namespace.suite = suite;

    // For development only.
    window.Y = Y;

}, "0.1", {requires: ["test", "lp.extras"]});
