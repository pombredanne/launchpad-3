/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Tests for Form Widgets.
 *
 * @module lp.app.formwidgets
 * @submodule test
 */

YUI.add('lp.app.formwidgets.test', function(Y) {

    var namespace = Y.namespace('lp.app.formwidgets.test');

    var Assert = Y.Assert;
    var ArrayAssert = Y.ArrayAssert;

    var suite = new Y.Test.Suite("formwidgets Tests");
    var widgets = Y.lp.app.formwidgets;

    var attrselect = Y.lp.extras.attrselect;

    var testFormRowWidget = {
        name: 'TestFormRowWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new widgets.FormRowWidget();
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testRender: function() {
            this.widget.render(this.container);
            Assert.isTrue(
                this.container.contains(
                    this.widget.get("boundingBox")));
        },

        testRenderWithName: function() {
            this.widget.fieldNode.append(
                Y.Node.create("<input /><input />"));
            this.widget.set("name", "field");
            this.widget.render(this.container);
            ArrayAssert.itemsAreSame(
                ["field", "field"],
                this.container.all("input").get("name"));
        },

        testRenderWithNameChange: function() {
            this.widget.fieldNode.append(
                Y.Node.create("<input /><input />"));
            this.widget.set("name", "field");
            this.widget.render(this.container);
            this.widget.set("name", "plain");
            ArrayAssert.itemsAreSame(
                ["plain", "plain"],
                this.container.all("input").get("name"));
        },

        testRenderLabel: function() {
            this.widget.set("label", "Test label");
            this.widget.render(this.container);
            Assert.areSame(
                "Test label",
                this.container.one("label").get("text"));
        },

        testRenderLabelChange: function() {
            this.widget.set("label", "Test label");
            this.widget.render(this.container);
            this.widget.set("label", "Another label");
            Assert.areSame(
                "Another label",
                this.container.one("label").get("text"));
        },

        testRenderDescription: function() {
            this.widget.set("description", "Test description.");
            this.widget.render(this.container);
            Assert.areSame(
                "Test description.",
                this.container.one("p.formHelp").get("text"));
        },

        testRenderDescriptionChange: function() {
            this.widget.set("description", "Test description.");
            this.widget.render(this.container);
            this.widget.set("description", "Another description.");
            Assert.areSame(
                "Another description.",
                this.container.one("p.formHelp").get("text"));
        },

        testRenderHelp: function() {
            this.widget.set("help",
                {link: "http://test.com/test.html", text: "Help text"});
            this.widget.render(this.container);
            Assert.isFalse(this.container
                .one('span.helper').hasClass("unseen"));
            Assert.areSame(
                "Help text",
                this.container.one("a")
                   .one('span.invisible-link').get("text"));
            Assert.areSame(
                "http://test.com/test.html",
                this.container.one("a").get('href'));
        },

        testGetHelp: function() {
            this.widget.set("help",
                {link: "http://test.com/test.html", text: "Help text"});
            this.widget.render(this.container);
            Assert.areSame(
                "http://test.com/test.html",
                this.widget.get("help").link);
            Assert.areSame(
                "Help text",
                this.widget.get("help").text);
         },

        testChangeHelp: function() {
            this.widget.set("help",
                {link: "http://test.com/test.html", text: "Help text"});
            this.widget.render(this.container);
            this.widget.set(
                "help",
                {link: "http://test.com/test2.html", text: "Help text2"});
            Assert.areSame(
                "Help text2",
                this.container.one("a")
                    .one('span.invisible-link').get("text"));
            Assert.areSame(
                "http://test.com/test2.html",
                this.container.one("a").get('href'));
        },

        testChangeHelpUndefined: function() {
            this.widget.set("help",
                {link: "http://test.com/test.html", text: "Help text"});
            this.widget.render(this.container);
            this.widget.set("help", {});
            Assert.isTrue(this.container
                .one('span.helper').hasClass("unseen"));
        },

        testSpinner: function() {
            Assert.isFalse(
                this.widget.fieldNode.contains(this.widget.spinnerNode));
            this.widget.showSpinner();
            Assert.isTrue(
                this.widget.fieldNode.contains(this.widget.spinnerNode));
            this.widget.hideSpinner();
            Assert.isFalse(
                this.widget.fieldNode.contains(this.widget.spinnerNode));
        },

        testShowError: function() {
            this.widget.showError("Unrealistic expectations.");
            Assert.areSame(
                "Unrealistic expectations.",
                this.widget.fieldNode.one("p").get("text"));
        }

    };

    suite.add(new Y.Test.Case(testFormRowWidget));

    var testChoiceListWidget = {
        name: 'TestChoiceListWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new widgets.ChoiceListWidget();
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testCompareChoices: function() {
            // _compareChoices can compare objects or strings.
            var widget = this.widget;
            var comparisons = [
                // String comparisons.
                {ca: "foo", cb: "foo", expected: +0},
                {ca: "foo", cb: "bar", expected: +1},
                {ca: "bar", cb: "foo", expected: -1},
                // Object comparisons.
                {ca: {text: "foo"}, cb: {text: "foo"}, expected: +0},
                {ca: {text: "foo"}, cb: {text: "bar"}, expected: +1},
                {ca: {text: "bar"}, cb: {text: "foo"}, expected: -1},
                // Mixed comparisons.
                {ca: {text: "foo"}, cb: "foo", expected: +0},
                {ca: "foo", cb: {text: "foo"}, expected: +0},
                {ca: {text: "foo"}, cb: "bar", expected: +1},
                {ca: "foo", cb: {text: "bar"}, expected: +1},
                {ca: {text: "bar"}, cb: "foo", expected: -1},
                {ca: "bar", cb: {text: "foo"}, expected: -1}
            ];
            Y.each(comparisons, function(comparison) {
                Assert.areSame(
                    comparison.expected,
                    widget._compareChoices(
                        comparison.ca, comparison.cb));
            });
        },

        testRenderChoices: function() {
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            ArrayAssert.itemsAreSame(
                ["a", "b"],
                this.container.all("li > input").get("value"));
            ArrayAssert.itemsAreSame(
                ["a", "b"],
                this.container.all("li > label").get("text"));
            ArrayAssert.itemsAreSame(
                ["checkbox", "checkbox"],
                this.container.all("li > input").getAttribute("type"));
        },

        testRenderObjectChoices: function() {
            var choices = [
                {value: "a", text: "A", data: "aaa"},
                {value: "b", text: "B", data: "bbb"}
            ];
            this.widget.set("choices", choices);
            this.widget.render(this.container);
            ArrayAssert.itemsAreSame(
                ["a", "b"],
                this.container.all("li > input").get("value"));
            ArrayAssert.itemsAreSame(
                ["A", "B"],
                this.container.all("li > label").get("text"));
            var items = [];
            this.container.all("li").each(
                function(node) { items.push(node); });
            ArrayAssert.itemsAreSame(
                ["aaa", "bbb"],
                this.container.all("li").map(
                    function(node) { return node.getData(); }));
        },

        testRenderChoicesChange: function() {
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            this.widget.set("choices", ["c", "d", "e"]);
            ArrayAssert.itemsAreSame(
                ["c", "d", "e"],
                this.container.all("li > input").get("value"));
            ArrayAssert.itemsAreSame(
                ["c", "d", "e"],
                this.container.all("li > label").get("text"));
        },

        testRenderAddChoices: function() {
            this.widget.add_choices(["a", "b"]);
            this.widget.render(this.container);
            ArrayAssert.itemsAreSame(
                ["a", "b"],
                this.container.all("li > input").get("value"));
            ArrayAssert.itemsAreSame(
                ["a", "b"],
                this.container.all("li > label").get("text"));
            ArrayAssert.itemsAreSame(
                ["checkbox", "checkbox"],
                this.container.all("li > input").getAttribute("type"));
        },

        testRenderRemoveChoices: function() {
            this.widget.set("choices", ["a", "b", "c", "d"]);
            this.widget.render(this.container);
            this.widget.remove_choices(["b", "d"]);
            ArrayAssert.itemsAreSame(
                ["a", "c"],
                this.container.all("li > input").get("value"));
            ArrayAssert.itemsAreSame(
                ["a", "c"],
                this.container.all("li > label").get("text"));
        },

        testRenderChoicesChangeMultiple: function() {
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            this.widget.set("multiple", false);
            ArrayAssert.itemsAreSame(
                ["radio", "radio"],
                this.container.all("li > input").getAttribute("type"));
        },

        testChoicesWithStrings: function() {
            /* The choices attribute should be an array, and it may
               contain unadorned strings. However, it always returns
               object choices in sorted order. */
            ArrayAssert.itemsAreSame(
                [], this.widget.get("choices"));
            this.widget.set("choices", ["foo", "bar"]);
            var choices = this.widget.get("choices");
            choices.forEach(function(choice) {
                Assert.isObject(choice);
                Assert.areSame(choice.text, choice.value);
            });
            ArrayAssert.itemsAreSame(
                ["bar", "foo"], attrselect("text")(choices));
            ArrayAssert.itemsAreSame(
                ["bar", "foo"], attrselect("value")(choices));
        },

        testChoicesWithObjects: function() {
            /* The choices attribute should be an array, and it may
               contain objects with text and value keys. It always
               returns object choices in order, sorted by text. */
            ArrayAssert.itemsAreSame(
                [], this.widget.get("choices"));
            this.widget.set("choices", [
                {text: "Bbb", value: "xxx"},
                {text: "Aaa", value: "zzz"}
                ]);
            var choices = this.widget.get("choices");
            choices.forEach(function(choice) {
                Assert.isObject(choice);
            });
            ArrayAssert.itemsAreSame(
                ["Aaa", "Bbb"], attrselect("text")(choices));
            ArrayAssert.itemsAreSame(
                ["zzz", "xxx"], attrselect("value")(choices));
        },

        testChoicesWithObjectsAndData: function() {
            /* The choices attribute should be an array. The objects
               it contains can optionally have a data key which is
               stored and returned when referencing the choices
               attribute. */
            ArrayAssert.itemsAreSame(
                [], this.widget.get("choices"));
            this.widget.set("choices", [
                {text: "Bbb", value: "xxx", data: 123},
                {text: "Aaa", value: "zzz", data: 456}
                ]);
            var choices = this.widget.get("choices");
            ArrayAssert.itemsAreSame(
                [456, 123], attrselect("data")(choices));
        },

        testChoicesPreservesSelection: function() {
            /* Setting new choices preserves, as much as possible, the
               existing selection. */
            this.widget.set("choices", ["a", "b", "c"]);
            this.widget.set("choice", ["a", "c"]);
            this.widget.set("choices", ["a", "b", "d"]);
            var choice = this.widget.get("choice");
            ArrayAssert.itemsAreSame(
                ["a"], attrselect("value")(choice));
        },

        testChoiceWithCheckBox: function() {
            this.widget
                .set("multiple", true)
                .set("choices", ["a", "b"]);
            ArrayAssert.itemsAreSame(
                [], this.widget.get("choice"));
            this.widget.fieldNode.one("input[value=a]")
                .set("checked", "checked");
            ArrayAssert.itemsAreSame(
                ["a"], attrselect("value")(this.widget.get("choice")));
        },

        testChoiceWithRadio: function() {
            // When both radio buttons are checked (this is possible in some
            // broken DOMs/JS engined), choice is undefined.
            this.widget
                .set("multiple", false)
                .set("choices", ["a", "b"]);
            Assert.isNull(this.widget.get("choice"));
            this.widget.fieldNode.one("input[value=a]")
                .set("checked", "checked");
            Assert.areSame("a", this.widget.get("choice").value);
            this.widget.fieldNode.one("input[value=b]")
                .set("checked", "checked");
            if (this.widget.fieldNode.one("input[value=a]").get("checked")) {
                // This assertion can only be made if the DOM/JS is broken
                // in the host browser.
                Assert.isUndefined(this.widget.get("choice"));
            }
            else {
                // The host browser's DOM/JS is sane.
                ArrayAssert.itemsAreSame(
                    ["b"], this.widget.get("choice").value);
            }
        },

        testSetChoiceWithCheckBox: function() {
            this.widget
                .set("multiple", true)
                .set("choices", ["a", "b"])
                .set("choice", "a");
            ArrayAssert.itemsAreSame(
                ["a"], attrselect("value")(this.widget.get("choice")));
            this.widget.set("choice", ["a"]);
            ArrayAssert.itemsAreSame(
                ["a"], attrselect("value")(this.widget.get("choice")));
            this.widget.set("choice", ["a", "b"]);
            ArrayAssert.itemsAreSame(
                ["a", "b"], attrselect("value")(this.widget.get("choice")));
            this.widget.set("choice", ["b", "c"]);
            ArrayAssert.itemsAreSame(
                ["b"], attrselect("value")(this.widget.get("choice")));
        },

        testSetChoiceWithRadio: function() {
            this.widget
                .set("multiple", false)
                .set("choices", ["a", "b"])
                .set("choice", "a");
            ArrayAssert.itemsAreSame(
                "a", this.widget.get("choice").value);
            this.widget.set("choice", ["a"]);
            ArrayAssert.itemsAreSame(
                "a", this.widget.get("choice").value);
            this.widget.set("choice", "b");
            ArrayAssert.itemsAreSame(
                "b", this.widget.get("choice").value);
        },

        testSetChoiceWithObjectChoice: function() {
            /* An object choice (i.e. an object with text, value and
               optional data members) can be passed into when setting
               the choice attribute. Only the value is considered. */
            this.widget
                .set("multiple", false)
                .set("choices", ["a", "b"])
                .set("choice", {text: "A", value: "a"});
            ArrayAssert.itemsAreSame(
                "a", this.widget.get("choice").value);
        },

        testAddChoicesEvents: function() {
            /* Calling add_choices() causes choicesChange and
               choiceChange events to fire. */
            var events = [], push = Y.bind(events.push, events);
            this.widget.after("choicesChange", push);
            this.widget.after("choiceChange", push);
            this.widget.add_choices(["a", "b"]);
            ArrayAssert.containsMatch(
                function(event) { return event.attrName == "choice"; },
                events);
            ArrayAssert.containsMatch(
                function(event) { return event.attrName == "choices"; },
                events);
        },

        testRemoveChoicesEvents: function() {
            /* Calling remove_choices() causes choicesChange and
               choiceChange events to fire. */
            var events = [], push = Y.bind(events.push, events);
            this.widget.after("choicesChange", push);
            this.widget.after("choiceChange", push);
            this.widget.remove_choices(["a", "b"]);
            ArrayAssert.containsMatch(
                function(event) { return event.attrName == "choice"; },
                events);
            ArrayAssert.containsMatch(
                function(event) { return event.attrName == "choices"; },
                events);
        }

    };

    testChoiceListWidget = Y.merge(
        testFormRowWidget, testChoiceListWidget);
    suite.add(new Y.Test.Case(testChoiceListWidget));

    var testSelectWidget = {
        name: 'TestSelectWidget',

        choices: [
            {value: "a", text: "A", data: 123},
            {value: "b", text: "B", data: 456},
            {value: "c", text: "C", data: 789}
        ],

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new widgets.SelectWidget();
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testNameChange: function() {
            this.widget
                .set("name", "foo")
                .set("choices", this.choices);
            var select = this.widget.fieldNode.one("select");
            Assert.areSame("foo", select.get("name"));
            this.widget
                .set("name", "bar");
            Assert.areSame("bar", select.get("name"));
        },

        testChoices: function() {
            this.widget.set("choices", this.choices);
            var choices_observed = this.widget.get("choices");
            /* We have to compare bit by bit ourselves because
               Javascript is a language born in hell. */
            ArrayAssert.itemsAreSame(
                attrselect("value")(this.choices),
                attrselect("value")(choices_observed));
            ArrayAssert.itemsAreSame(
                attrselect("text")(this.choices),
                attrselect("text")(choices_observed));
            ArrayAssert.itemsAreSame(
                attrselect("data")(this.choices),
                attrselect("data")(choices_observed));
        },

        testRenderChoices: function() {
            this.widget.set("choices", this.choices);
            this.widget.render(this.container);
            ArrayAssert.itemsAreSame(
                ["a", "b", "c"],
                this.container.all("select > option").get("value"));
            ArrayAssert.itemsAreSame(
                ["A", "B", "C"],
                this.container.all("select > option").get("text"));
        },

        testRenderEmptyChoices: function() {
            this.widget.fieldNode.append("something");
            this.widget.set("choices", []);
            this.widget.render(this.container);
            Assert.isNull(this.container.one("select"));
            Assert.isFalse(this.widget.fieldNode.hasChildNodes());
        },

        testRenderChoicesChange: function() {
            var choices1 = [
                {value: "a", text: "A", data: 123}
            ];
            this.widget.set("choices", choices1);
            this.widget.render(this.container);
            var choices2 = [
                {value: "b", text: "B", data: 456},
                {value: "c", text: "C", data: 789}
            ];
            this.widget.set("choices", choices2);
            ArrayAssert.itemsAreSame(
                ["b", "c"],
                this.container.all("select > option").get("value"));
            ArrayAssert.itemsAreSame(
                ["B", "C"],
                this.container.all("select > option").get("text"));
        },

        testChoice: function() {
            this.widget
                .set("choices", this.choices)
                .set("multiple", true);
            /* It would be better to deselect all options by default,
               but this appears impossible; the browser seems to
               select the first option when rendering. */
            this.widget.fieldNode.all("option").set("selected", false);
            ArrayAssert.itemsAreSame(
                [], this.widget.get("choice"));
            this.widget.fieldNode.one("option[value=a]")
                .set("selected", true);
            ArrayAssert.itemsAreSame(
                ["a"], this.widget.get("choice"));
            this.widget.fieldNode.one("option[value=c]")
                .set("selected", true);
            ArrayAssert.itemsAreSame(
                ["a", "c"], this.widget.get("choice"));
        },

        testSetChoice: function() {
            this.widget
                .set("multiple", true)
                .set("choices", this.choices)
                .set("choice", "a");
            ArrayAssert.itemsAreSame(
                ["a"], this.widget.get("choice"));
            this.widget.set("choice", ["a"]);
            ArrayAssert.itemsAreSame(
                ["a"], this.widget.get("choice"));
            this.widget.set("choice", ["a", "b"]);
            ArrayAssert.itemsAreSame(
                ["a", "b"], this.widget.get("choice"));
            this.widget.set("choice", ["b", "z"]);
            ArrayAssert.itemsAreSame(
                ["b"], this.widget.get("choice"));
        },

        testSize: function() {
            Assert.areSame(1, this.widget.get("size"));
        },

        testRenderSize: function() {
            this.widget
                .set("choices", this.choices)
                .set("size", 7)
                .render(this.container);
            Assert.areSame(
                7, this.widget.fieldNode.one("select").get("size"));
        },

        testRenderSizeChange: function() {
            this.widget
                .set("choices", this.choices)
                .set("size", 3)
                .render(this.container)
                .set("size", 5);
            Assert.areSame(
                5, this.widget.fieldNode.one("select").get("size"));
        },

        testAutoSize: function() {
            this.widget.set("choices", this.choices);
            /* Without argument, autoSize() sets the size to the same
               as the number of choices. */
            this.widget.autoSize();
            Assert.areSame(3, this.widget.get("size"));
        },

        testAutoSizeMoreChoicesThanMaxiumum: function() {
            this.widget.set("choices", this.choices);
            /* autoSize() sets the size to the same as the number of
               choices unless there are more than the specified
               maximum. */
            this.widget.autoSize(2);
            Assert.areSame(2, this.widget.get("size"));
        },

        testAutoSizeFewerChoicesThanMaxiumum: function() {
            this.widget.set("choices", this.choices);
            /* autoSize() sets the size to the same as the number of
               choices. */
            this.widget.autoSize(5);
            Assert.areSame(3, this.widget.get("size"));
        },

        testMultiple: function() {
            Assert.areSame(false, this.widget.get("multiple"));
        },

        testRenderMultiple: function() {
            this.widget
                .set("choices", this.choices)
                .set("multiple", true)
                .render(this.container);
            Assert.isTrue(
                this.widget.fieldNode.one("select")
                    .hasAttribute("multiple"));
        },

        testRenderMultipleChange: function() {
            this.widget
                .set("choices", this.choices)
                .set("multiple", true)
                .render(this.container)
                .set("multiple", false);
            Assert.isFalse(
                this.widget.fieldNode.one("select")
                    .hasAttribute("multiple"));
        }

    };

    testSelectWidget = Y.merge(
        testFormRowWidget, testSelectWidget);
    suite.add(new Y.Test.Case(testSelectWidget));

    var testFormActionsWidget = {
        name: 'TestFormActionsWidget',

        makeActionsDiv: function() {
            var submit = Y.Node.create("<input />")
                .set("type", "submit")
                .set("value", "Initialize Series");
            var cancel = Y.Node.create("<a>Cancel</a>");
            var div = Y.Node.create("<div />")
                .addClass("actions")
                .append(submit)
                .append(cancel);
            return div;
        },

        setUp: function() {
            this.actions = this.makeActionsDiv();
            this.widget = new widgets.FormActionsWidget(
                {srcNode: this.actions});
        },

        tearDown: function() {
            this.actions.remove(true);
        },

        testInitializer: function() {
            Assert.isTrue(
                this.actions.one("input").compareTo(
                    this.widget.submitButtonNode));
        },

        testSpinner: function() {
            Assert.isTrue(
                this.actions.contains(this.widget.submitButtonNode));
            Assert.isFalse(
                this.actions.contains(this.widget.spinnerNode));
            this.widget.showSpinner();
            Assert.isFalse(
                this.actions.contains(this.widget.submitButtonNode));
            Assert.isTrue(
                this.actions.contains(this.widget.spinnerNode));
            this.widget.hideSpinner();
            Assert.isTrue(
                this.actions.contains(this.widget.submitButtonNode));
            Assert.isFalse(
                this.actions.contains(this.widget.spinnerNode));
        },

        testShowError: function() {
            this.widget.showError("The Man From U.N.C.L.E.");
            Assert.areSame(
                "The Man From U.N.C.L.E.",
                this.actions.one("p.error.message").get("text"));
        },

        testHideErrors: function() {
            this.widget.showError("The Man From U.N.C.L.E.");
            this.widget.showError("The Woman From A.U.N.T.I.E.");
            this.widget.hideErrors();
            Assert.isNull(this.actions.one("p.error.message"));
        }

    };

    suite.add(new Y.Test.Case(testFormActionsWidget));

    // Exports.
    namespace.testFormRowWidget = testFormRowWidget;
    namespace.testChoiceListWidget = testChoiceListWidget;
    namespace.testSelectWidget = testSelectWidget;
    namespace.testFormActionsWidget = testFormActionsWidget;
    namespace.suite = suite;

}, "0.1", {"requires": [
               'test', 'console', 'node-event-simulate',
               'lp.app.formwidgets', 'lp.extras']});
