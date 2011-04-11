/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use(
        'test', 'console', 'lp.registry.distroseries.initseries',
        function(Y) {

    var Assert = Y.Assert;
    var ArrayAssert = Y.ArrayAssert;

    var suite = new Y.Test.Suite("distroseries.initseries Tests");
    var initseries = Y.lp.registry.distroseries.initseries;

    var attrgetter = function(name) {
        return function(thing) {
            return thing[name];
        };
    };

    var attrselect = function(name) {
        return function(things) {
            return Y.Array(things).map(attrgetter(name));
        };
    };

    var testFormRowWidget = {
        name: 'TestFormRowWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.FormRowWidget();
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
            ArrayAssert.itemsAreEqual(
                ["field", "field"],
                this.container.all("input").get("name"));
        },

        testRenderWithNameChange: function() {
            this.widget.fieldNode.append(
                Y.Node.create("<input /><input />"));
            this.widget.set("name", "field");
            this.widget.render(this.container);
            this.widget.set("name", "plain");
            ArrayAssert.itemsAreEqual(
                ["plain", "plain"],
                this.container.all("input").get("name"));
        },

        testRenderLabel: function() {
            this.widget.set("label", "Test label");
            this.widget.render(this.container);
            Assert.areEqual(
                "Test label",
                this.container.one("label").get("text"));
        },

        testRenderLabelChange: function() {
            this.widget.set("label", "Test label");
            this.widget.render(this.container);
            this.widget.set("label", "Another label");
            Assert.areEqual(
                "Another label",
                this.container.one("label").get("text"));
        },

        testRenderDescription: function() {
            this.widget.set("description", "Test description.");
            this.widget.render(this.container);
            Assert.areEqual(
                "Test description.",
                this.container.one("p.formHelp").get("text"));
        },

        testRenderDescriptionChange: function() {
            this.widget.set("description", "Test description.");
            this.widget.render(this.container);
            this.widget.set("description", "Another description.");
            Assert.areEqual(
                "Another description.",
                this.container.one("p.formHelp").get("text"));
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
            Assert.areEqual(
                "Unrealistic expectations.",
                this.widget.fieldNode.one("p").get("text"));
        }

    };

    suite.add(new Y.Test.Case(testFormRowWidget));

    var testChoiceListWidget = {
        name: 'TestChoiceListWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.ChoiceListWidget();
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testRenderChoices: function() {
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            ArrayAssert.itemsAreEqual(
                ["a", "b"],
                this.container.all("li > input").get("value"));
            ArrayAssert.itemsAreEqual(
                ["a", "b"],
                this.container.all("li > label").get("text"));
            ArrayAssert.itemsAreEqual(
                ["checkbox", "checkbox"],
                this.container.all("li > input").getAttribute("type"));
        },

        testRenderChoicesChange: function() {
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            this.widget.set("choices", ["c", "d", "e"]);
            ArrayAssert.itemsAreEqual(
                ["c", "d", "e"],
                this.container.all("li > input").get("value"));
            ArrayAssert.itemsAreEqual(
                ["c", "d", "e"],
                this.container.all("li > label").get("text"));
        },

        testRenderChoicesChangeType: function() {
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            this.widget.set("type", "radio");
            ArrayAssert.itemsAreEqual(
                ["radio", "radio"],
                this.container.all("li > input").getAttribute("type"));

        },

        testChoiceWithCheckBox: function() {
            this.widget
                .set("type", "checkbox")
                .set("choices", ["a", "b"]);
            ArrayAssert.itemsAreEqual(
                [], this.widget.get("choice"));
            this.widget.fieldNode.one("input[value=a]")
                .set("checked", "checked");
            ArrayAssert.itemsAreEqual(
                ["a"], this.widget.get("choice"));
        },

        testChoiceWithRadio: function() {
            this.widget
                .set("type", "radio")
                .set("choices", ["a", "b"]);
            Assert.isNull(this.widget.get("choice"));
            this.widget.fieldNode.one("input[value=a]")
                .set("checked", "checked");
            Assert.areEqual("a", this.widget.get("choice"));
            /* When both radio buttons are checked (should that be
               possible?), choice is undefined. */
            this.widget.fieldNode.one("input[value=b]")
                .set("checked", "checked");
            Assert.isUndefined(this.widget.get("choice"));
        },

        testSetChoiceWithCheckBox: function() {
            this.widget
                .set("type", "checkbox")
                .set("choices", ["a", "b"])
                .set("choice", "a");
            ArrayAssert.itemsAreEqual(
                ["a"], this.widget.get("choice"));
            this.widget.set("choice", ["a"]);
            ArrayAssert.itemsAreEqual(
                ["a"], this.widget.get("choice"));
            this.widget.set("choice", ["a", "b"]);
            ArrayAssert.itemsAreEqual(
                ["a", "b"], this.widget.get("choice"));
            this.widget.set("choice", ["b", "c"]);
            ArrayAssert.itemsAreEqual(
                ["b"], this.widget.get("choice"));
        },

        testSetChoiceWithRadio: function() {
            this.widget
                .set("type", "radio")
                .set("choices", ["a", "b"])
                .set("choice", "a");
            ArrayAssert.itemsAreEqual(
                "a", this.widget.get("choice"));
            this.widget.set("choice", ["a"]);
            ArrayAssert.itemsAreEqual(
                "a", this.widget.get("choice"));
            this.widget.set("choice", "b");
            ArrayAssert.itemsAreEqual(
                "b", this.widget.get("choice"));
        }

    };

    testChoiceListWidget = Y.merge(
        testFormRowWidget, testChoiceListWidget);
    suite.add(new Y.Test.Case(testChoiceListWidget));

    var testArchitecturesChoiceListWidget = {
        name: 'TestArchitecturesChoiceListWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.ArchitecturesChoiceListWidget();
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testSetDistroArchSeriesesUpdatesChoices: function() {
            var distro_arch_serieses = [
                {architecture_tag: "i386"},
                {architecture_tag: "amd64"},
                {architecture_tag: "i386"}
            ];
            var distro_arch_serieses_collection =
                new Y.lp.client.Collection(
                    null, {entries: distro_arch_serieses}, null);
            this.widget.set(
                "distroArchSerieses",
                distro_arch_serieses_collection);
            ArrayAssert.itemsAreEqual(
                ["amd64", "i386"],
                this.widget.get("choices"));
        },

        testSetDistroSeriesInitiatesIO: function() {
            var io = false;
            this.widget.client = {
                get: function(path, config) {
                    io = true;
                    Assert.areEqual("ubuntu/hoary/architectures", path);
                    Assert.isObject(config.on);
                    Assert.isFunction(config.on.success);
                    Assert.isFunction(config.on.failure);
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
            Assert.isTrue(io, "No IO initiated.");
        },

        testSetDistroSeriesUpdatesDistroArchSeries: function() {
            var distro_arch_serieses = [
                {architecture_tag: "i386"},
                {architecture_tag: "amd64"},
                {architecture_tag: "i386"}
            ];
            var distro_arch_serieses_collection =
                new Y.lp.client.Collection(
                    null, {entries: distro_arch_serieses}, null);
            this.widget.client = {
                get: function(path, config) {
                    config.on.success(distro_arch_serieses_collection);
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
            ArrayAssert.itemsAreEqual(
                ["amd64", "i386"],
                this.widget.get("choices"));
        },

        testSetDistroSeriesSpinner: function() {
            var widget = this.widget;
            widget.client = {
                get: function(path, config) {
                    Assert.isFalse(
                        widget.fieldNode.contains(widget.spinnerNode));
                    config.on.start();
                    Assert.isTrue(
                        widget.fieldNode.contains(widget.spinnerNode));
                    config.on.end();
                    Assert.isFalse(
                        widget.fieldNode.contains(widget.spinnerNode));
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
        },

        testSetDistroSeriesError: function() {
            var widget = this.widget;
            widget.client = {
                get: function(path, config) {
                    config.on.failure(
                        null, {status: 404,
                               responseText: "Not found"});
                    Assert.areEqual(
                        "Not found",
                        widget.fieldNode.one("p").get("text"));
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
        }

    };

    testArchitecturesChoiceListWidget = Y.merge(
        testChoiceListWidget, testArchitecturesChoiceListWidget);
    suite.add(new Y.Test.Case(testArchitecturesChoiceListWidget));

    var testSelectWidget = {
        name: 'TestSelectWidget',

        choices: [
            {value: "a", text: "A", data: 123},
            {value: "b", text: "B", data: 456},
            {value: "c", text: "C", data: 789}
        ],

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.SelectWidget();
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testNameChange: function() {
            this.widget
                .set("name", "foo")
                .set("choices", this.choices);
            var select = this.widget.fieldNode.one("select");
            Assert.areEqual("foo", select.get("name"));
            this.widget
                .set("name", "bar");
            Assert.areEqual("bar", select.get("name"));
        },

        testChoices: function() {
            this.widget.set("choices", this.choices);
            var choices_observed = this.widget.get("choices");
            /* We have to compare bit by bit ourselves because
               Javascript is a language born in hell. */
            ArrayAssert.itemsAreEqual(
                attrselect("value")(this.choices),
                attrselect("value")(choices_observed));
            ArrayAssert.itemsAreEqual(
                attrselect("text")(this.choices),
                attrselect("text")(choices_observed));
            ArrayAssert.itemsAreEqual(
                attrselect("data")(this.choices),
                attrselect("data")(choices_observed));
        },

        testRenderChoices: function() {
            this.widget.set("choices", this.choices);
            this.widget.render(this.container);
            ArrayAssert.itemsAreEqual(
                ["a", "b", "c"],
                this.container.all("select > option").get("value"));
            ArrayAssert.itemsAreEqual(
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
            ArrayAssert.itemsAreEqual(
                ["b", "c"],
                this.container.all("select > option").get("value"));
            ArrayAssert.itemsAreEqual(
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
            ArrayAssert.itemsAreEqual(
                [], this.widget.get("choice"));
            this.widget.fieldNode.one("option[value=a]")
                .set("selected", true);
            ArrayAssert.itemsAreEqual(
                ["a"], this.widget.get("choice"));
            this.widget.fieldNode.one("option[value=c]")
                .set("selected", true);
            ArrayAssert.itemsAreEqual(
                ["a", "c"], this.widget.get("choice"));
        },

        testSetChoice: function() {
            this.widget
                .set("multiple", true)
                .set("choices", this.choices)
                .set("choice", "a");
            ArrayAssert.itemsAreEqual(
                ["a"], this.widget.get("choice"));
            this.widget.set("choice", ["a"]);
            ArrayAssert.itemsAreEqual(
                ["a"], this.widget.get("choice"));
            this.widget.set("choice", ["a", "b"]);
            ArrayAssert.itemsAreEqual(
                ["a", "b"], this.widget.get("choice"));
            this.widget.set("choice", ["b", "z"]);
            ArrayAssert.itemsAreEqual(
                ["b"], this.widget.get("choice"));
        },

        testSize: function() {
            Assert.areEqual(1, this.widget.get("size"));
        },

        testRenderSize: function() {
            this.widget
                .set("choices", this.choices)
                .set("size", 7)
                .render(this.container);
            Assert.areEqual(
                7, this.widget.fieldNode.one("select").get("size"));
        },

        testRenderSizeChange: function() {
            this.widget
                .set("choices", this.choices)
                .set("size", 3)
                .render(this.container)
                .set("size", 5);
            Assert.areEqual(
                5, this.widget.fieldNode.one("select").get("size"));
        },

        testAutoSize: function() {
            this.widget.set("choices", this.choices);
            /* Without argument, autoSize() sets the size to the same
               as the number of choices. */
            this.widget.autoSize();
            Assert.areEqual(3, this.widget.get("size"));
        },

        testAutoSizeMoreChoicesThanMaxiumum: function() {
            this.widget.set("choices", this.choices);
            /* autoSize() sets the size to the same as the number of
               choices unless there are more than the specified
               maximum. */
            this.widget.autoSize(2);
            Assert.areEqual(2, this.widget.get("size"));
        },

        testAutoSizeFewerChoicesThanMaxiumum: function() {
            this.widget.set("choices", this.choices);
            /* autoSize() sets the size to the same as the number of
               choices. */
            this.widget.autoSize(5);
            Assert.areEqual(3, this.widget.get("size"));
        },

        testMultiple: function() {
            Assert.areEqual(false, this.widget.get("multiple"));
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

    var testPackagesetPickerWidget = {
        name: 'TestPackagesetPickerWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.PackagesetPickerWidget();
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testSetPackageSetsUpdatesChoices: function() {
            var package_sets = [
                {name: "foo", description: "Foo"},
                {name: "bar", description: "Bar"},
                {name: "baz", description: "Baz"}
            ];
            var package_sets_collection =
                new Y.lp.client.Collection(
                    null, {entries: package_sets}, null);
            this.widget.set("packageSets", package_sets_collection);
            var choices = this.widget.get("choices");
            ArrayAssert.itemsAreEqual(
                ["foo", "bar", "baz"],
                attrselect("value")(choices));
        },

        testSetPackageSetsCallsAutoSize: function() {
            var package_sets = [
                {name: "foo", description: "Foo"},
                {name: "bar", description: "Bar"},
                {name: "baz", description: "Baz"}
            ];
            var package_sets_collection =
                new Y.lp.client.Collection(
                    null, {entries: package_sets}, null);
            var autoSized = false;
            this.widget.autoSize = function() { autoSized = true; };
            this.widget.set("packageSets", package_sets_collection);
            Assert.isTrue(autoSized);
        },

        testSetDistroSeriesInitiatesIO: function() {
            var io = false;
            this.widget.client = {
                named_get: function(path, operation, config) {
                    io = true;
                    Assert.areEqual("package-sets", path);
                    Assert.areEqual("getBySeries", operation);
                    Assert.isNotNull(
                        config.parameters.distroseries.match(
                            new RegExp("/ubuntu/hoary$")));
                    Assert.isObject(config.on);
                    Assert.isFunction(config.on.success);
                    Assert.isFunction(config.on.failure);
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
            Assert.isTrue(io, "No IO initiated.");
        },

        testSetDistroSeriesUpdatesPackageSets: function() {
            var package_sets = [
                {name: "foo", description: "Foo"},
                {name: "bar", description: "Bar"},
                {name: "baz", description: "Baz"}
            ];
            var package_sets_collection =
                new Y.lp.client.Collection(
                    null, {entries: package_sets}, null);
            this.widget.client = {
                named_get: function(path, operation, config) {
                    config.on.success(package_sets_collection);
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
            ArrayAssert.itemsAreEqual(
                ["foo", "bar", "baz"],
                attrselect("value")(this.widget.get("choices")));
        },

        testSetDistroSeriesSpinner: function() {
            var widget = this.widget;
            widget.client = {
                named_get: function(path, operation, config) {
                    Assert.isFalse(
                        widget.fieldNode.contains(widget.spinnerNode));
                    config.on.start();
                    Assert.isTrue(
                        widget.fieldNode.contains(widget.spinnerNode));
                    config.on.end();
                    Assert.isFalse(
                        widget.fieldNode.contains(widget.spinnerNode));
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
        },

        testSetDistroSeriesError: function() {
            var widget = this.widget;
            widget.client = {
                named_get: function(path, operation, config) {
                    config.on.failure(
                        null, {status: 404,
                               responseText: "Not found"});
                    Assert.areEqual(
                        "Not found",
                        widget.fieldNode.one("p").get("text"));
                }
            };
            this.widget.set("distroSeries", "ubuntu/hoary");
        }

    };

    testPackagesetPickerWidget = Y.merge(
        testSelectWidget, testPackagesetPickerWidget);
    suite.add(new Y.Test.Case(testPackagesetPickerWidget));

    var testFormActionsWidget = {
        name: 'TestFormActionsWidget',

        makeActionsDiv: function() {
            var submit = Y.Node.create("<input />")
                .set("type", "submit")
                .set("value", "Initialize series");
            var cancel = Y.Node.create("<a>Cancel</a>");
            var div = Y.Node.create("<div />")
                .addClass("actions")
                .append(submit)
                .append(cancel);
            return div;
        },

        setUp: function() {
            this.actions = this.makeActionsDiv();
            this.widget = new initseries.FormActionsWidget(
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
            Assert.areEqual(
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

    var testDeriveDistroSeriesActionsWidget = {
        name: 'TestDeriveDistroSeriesActionsWidget',

        setUp: function() {
            this.actions = this.makeActionsDiv();
            this.widget = new initseries.DeriveDistroSeriesActionsWidget({
                srcNode: this.actions,
                context: {
                    name: "hagfish",
                    displayname: "Horrid Hagfish",
                    distribution_link: "http://example.com/deribuntu/snaggle"
                },
                deriveFromChoice: {
                    get: function(name) {
                        Assert.areEqual("value", name);
                        return "ubuntu/hoary";
                    }
                },
                architectureChoice: {
                    get: function(name) {
                        Assert.areEqual("choice", name);
                        return ["i386", "sparc"];
                    }
                },
                packagesetChoice: {
                    get: function(name) {
                        Assert.areEqual("choice", name);
                        return ["foo", "bar"];
                    }
                },
                packageCopyOptions: {
                    get: function(name) {
                        Assert.areEqual("choice", name);
                        return "Copy Source and Rebuild";
                    }
                }
            });
            this.form = Y.Node.create("<form />");
            this.form.append(this.actions);
            this.container = Y.Node.create("<div />");
            this.container.append(this.form);
            this.body = Y.one("body");
            this.body.append(this.container);
        },

        tearDown: function() {
            this.container.remove(true);
        },

        testSuccess: function() {
            Assert.isTrue(this.container.contains(this.form));
            Assert.isNull(this.body.one("p.informational.message"));
            this.widget.success();
            Assert.areEqual(
                ("The initialization of Horrid Hagfish " +
                 "has been scheduled and should run shortly."),
                this.body.one("p.informational.message").get("text"));
            // The form is slowly evaporated.
            this.wait(function() {
                Assert.isFalse(
                    this.container.contains(this.form));
            }, 1100);
        },

        testSubmit: function() {
            var io = false;
            this.widget.client = {
                named_post: function(path, operation, config) {
                    io = true;
                    Assert.areEqual("ubuntu/hoary", path);
                    Assert.areEqual("deriveDistroSeries", operation);
                    Assert.areEqual(
                        "http://example.com/deribuntu/snaggle",
                        config.parameters.distribution);
                    ArrayAssert.itemsAreEqual(
                        ["i386", "sparc"],
                        config.parameters.architectures);
                    ArrayAssert.itemsAreEqual(
                        ["foo", "bar"],
                        config.parameters.packagesets);
                    Assert.isTrue(config.parameters.rebuild);
                    Assert.isObject(config.on);
                    Assert.isFunction(config.on.success);
                    Assert.isFunction(config.on.failure);
                }
            };
            this.widget.submit();
            Assert.isTrue(io, "No IO initiated.");
        }

    };

    testDeriveDistroSeriesActionsWidget = Y.merge(
        testFormActionsWidget, testDeriveDistroSeriesActionsWidget);
    suite.add(new Y.Test.Case(testDeriveDistroSeriesActionsWidget));

    // Lock, stock, and two smoking barrels.
    var handle_complete = function(data) {
        status_node = Y.Node.create(
            '<p id="complete">Test status: complete</p>');
        Y.one('body').appendChild(status_node);
        };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});
