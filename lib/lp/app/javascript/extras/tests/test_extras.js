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

        test_static_with_DOM_nodes: function() {
            // NodeList.map converts DOM nodes into Y.Node instances.
            var nodes = [
                document.createElement("div"),
                document.createElement("label"),
                document.createElement("strong")
            ];
            Y.NodeList.map(nodes, function(node) {
                Assert.isInstanceOf(Y.Node, node);
            });
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

    var TestAttributeFunctions = {
        name: 'TestAttributeFunctions',

        test_attrgetter: function() {
            var subject = {foo: 123, bar: 456};
            Assert.areSame(123, extras.attrgetter("foo")(subject));
            Assert.areSame(456, extras.attrgetter("bar")(subject));
        },

        test_attrselect: function() {
            var subject = [
                {foo: 1, bar: 5},
                {foo: 3, bar: 7},
                {foo: 2, bar: 6},
                {foo: 4, bar: 8}
            ];
            ArrayAssert.itemsAreSame(
                [1, 3, 2, 4], extras.attrselect("foo")(subject));
            ArrayAssert.itemsAreSame(
                [5, 7, 6, 8], extras.attrselect("bar")(subject));
        },

        test_attrcaller: function() {
            var subject = [
                {foo: function(num) { return num + 1; }},
                {foo: function(num) { return num + 2; }},
                {foo: function(num) { return num + 3; }}
            ];
            ArrayAssert.itemsAreSame(
                [4, 5, 6], subject.map(extras.attrcaller("foo", 3)));
        }

    };

    var TestDict = {
        name: 'TestDict',

        test_new: function() {
            var dict = new extras.Dict();
            Assert.isInstanceOf(extras.Dict, dict);
            Assert.isTrue(dict.isEmpty());
        },

        test_new_with_initial: function() {
            var initial = {foo: 123, bar: 456};
            var dict = new extras.Dict(initial);
            Assert.isInstanceOf(extras.Dict, dict);
            Assert.isFalse(dict.isEmpty());
            Assert.areSame(123, dict.foo);
            Assert.areSame(456, dict.bar);
        },

        test_fromKeys: function() {
            var dict = extras.Dict.fromKeys(["foo", "bar"], "baz");
            Assert.isInstanceOf(extras.Dict, dict);
            Assert.areSame("baz", dict.foo);
            Assert.areSame("baz", dict.bar);
        },

        test_fromKeys_no_value: function() {
            // undefined is used as the default value.
            var dict = extras.Dict.fromKeys(["foo"]);
            Assert.isInstanceOf(extras.Dict, dict);
            Assert.isTrue(dict.hasKey("foo"));
            Assert.isUndefined(dict.foo);
        },

        test_isEmpty: function() {
            var dict = new extras.Dict();
            dict.foo = 123, dict.bar = 456;
            Assert.isFalse(dict.isEmpty());
            delete dict.foo, delete dict.bar;
            Assert.isTrue(dict.isEmpty());
        },

        test_isSame: function() {
            var dict_a = new extras.Dict(),
                dict_b = new extras.Dict();
            Assert.isTrue(dict_a.isSame(dict_b));
            dict_a.foo = 123;
            Assert.isFalse(dict_a.isSame(dict_b));
            dict_b.foo = 123;
            Assert.isTrue(dict_a.isSame(dict_b));
            dict_a.bar = 456;
            Assert.isFalse(dict_a.isSame(dict_b));
        },

        test_clear: function() {
            var dict = new extras.Dict();
            dict.foo = 123, dict.bar = 456;
            dict.clear();
            Assert.isTrue(dict.isEmpty());
        },

        test_copy: function() {
            var dict = new extras.Dict();
            dict.foo = 123, dict.bar = 456;
            var copy = dict.copy();
            Assert.areNotSame(copy, dict);
            Assert.isTrue(copy.isSame(dict));
        },

        test_get: function() {
            var dict = new extras.Dict({foo: 123});
            Assert.areSame(123, dict.get("foo"));
            Assert.areSame(123, dict.get("foo", 456));
            Assert.areSame(789, dict.get("bar", 789));
        },

        test_hasKey: function() {
            var dict = new extras.Dict({foo: 123});
            Assert.isTrue(dict.hasKey("foo"));
            Assert.isFalse(dict.hasKey("bar"));
            // hasKey() does not consider prototype properties.
            Assert.isFalse(dict.hasKey("hasOwnProperty"));
            Assert.isFalse(dict.hasKey("hasKey"));
        },

        test_items: function() {
            var dict = new extras.Dict({foo: 123, bar: 456});
            var items = dict.items().sort(function(a, b) {
                if (a.key == b.key) {
                    return 0;
                }
                else {
                    return a.key > b.key ? 1 : -1;
                }
            });
            ArrayAssert.itemsAreSame(
                ["bar", "foo"], extras.attrselect("key")(items));
            ArrayAssert.itemsAreSame(
                [456, 123], extras.attrselect("value")(items));
        },

        test_keys: function() {
            var dict = new extras.Dict({foo: 123, bar: 456});
            ArrayAssert.itemsAreSame(
                ["bar", "foo"], dict.keys().sort());
        },

        test_pop: function() {
            var dict = new extras.Dict({foo: 123, bar: 456});
            var value = dict.pop("foo");
            Assert.areSame(123, value);
            Assert.isFalse(dict.hasKey("foo"));
            Assert.isTrue(dict.hasKey("bar"));
        },

        test_popItem: function() {
            var dict = new extras.Dict({foo: 123, bar: 456});
            var item = dict.popItem();
            if (item.value === 123) {
                Assert.areSame("foo", item.key);
                Assert.isFalse(dict.hasKey("foo"));
                Assert.isTrue(dict.hasKey("bar"));
            }
            else if (item.value === 456) {
                Assert.areSame("bar", item.key);
                Assert.isTrue(dict.hasKey("foo"));
                Assert.isFalse(dict.hasKey("bar"));
            }
            else {
                Y.fail("Unexpected: " + value);
            }
        },

        test_setDefault: function() {
            var dict = new extras.Dict({foo: 123});
            Assert.areSame(123, dict.setDefault("foo", 789));
            Assert.areSame(456, dict.setDefault("bar", 456));
            Assert.areSame(456, dict.bar);
        },

        test_update_with_object: function() {
            var dict = new extras.Dict({foo: 123});
            dict.update({bar: 456});
            Assert.areSame(123, dict.foo);
            Assert.areSame(456, dict.bar);
        },

        test_update_with_array: function() {
            var dict = new extras.Dict({foo: 123});
            dict.update([["bar", 456], {key: "baz", value: 789}]);
            Assert.areSame(123, dict.foo);
            Assert.areSame(456, dict.bar);
            Assert.areSame(789, dict.baz);
        },

        test_values: function() {
            var dict = new extras.Dict({foo: 123, bar: 456});
            ArrayAssert.itemsAreSame(
                [123, 456], dict.values().sort());
        }

    };

    // Populate the suite.
    suite.add(new Y.Test.Case(TestNodeListMap));
    suite.add(new Y.Test.Case(TestAttributeFunctions));
    suite.add(new Y.Test.Case(TestDict));

    // Exports.
    namespace.suite = suite;

}, "0.1", {requires: ["test", "lp.extras", "lp.extras-dict"]});
