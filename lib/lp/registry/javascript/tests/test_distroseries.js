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
    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

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
            this.container.remove();
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

    var testCheckBoxListWidget = {
        name: 'TestCheckBoxListWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.CheckBoxListWidget();
        },

        tearDown: function() {
            this.container.remove();
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
        }

    };

    testCheckBoxListWidget = Y.merge(
        testFormRowWidget, testCheckBoxListWidget);
    suite.add(new Y.Test.Case(testCheckBoxListWidget));

    var testArchitecturesCheckBoxListWidget = {
        name: 'TestArchitecturesCheckBoxListWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.ArchitecturesCheckBoxListWidget();
        },

        tearDown: function() {
            this.container.remove();
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

    testArchitecturesCheckBoxListWidget = Y.merge(
        testCheckBoxListWidget, testArchitecturesCheckBoxListWidget);
    suite.add(new Y.Test.Case(testArchitecturesCheckBoxListWidget));

    var testSelectWidget = {
        name: 'TestSelectWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.SelectWidget();
        },

        tearDown: function() {
            this.container.remove();
        },

        testChoices: function() {
            var choices = [
                {value: "a", text: "A", data: 123},
                {value: "b", text: "B", data: 456},
                {value: "c", text: "C", data: 789}
            ];
            this.widget.set("choices", choices);
            var choices_observed = this.widget.get("choices");
            /* We have to compare bit by bit ourselves because
               Javascript is a language born in hell. */
            ArrayAssert.itemsAreEqual(
                attrselect("value")(choices),
                attrselect("value")(choices_observed));
            ArrayAssert.itemsAreEqual(
                attrselect("text")(choices),
                attrselect("text")(choices_observed));
            ArrayAssert.itemsAreEqual(
                attrselect("data")(choices),
                attrselect("data")(choices_observed));
        },

        testRenderChoices: function() {
            var choices = [
                {value: "a", text: "A", data: 123},
                {value: "b", text: "B", data: 456},
                {value: "c", text: "C", data: 789}
            ];
            this.widget.set("choices", choices);
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

        testSize: function() {
            Assert.areEqual(1, this.widget.get("size"));
        },

        testRenderSize: function() {
            var choices = [
                {value: "a", text: "A", data: 123},
                {value: "b", text: "B", data: 456},
                {value: "c", text: "C", data: 789}
            ];
            this.widget
                .set("choices", choices)
                .set("size", 7)
                .render(this.container);
            Assert.areEqual(
                7, this.widget.fieldNode.one("select").get("size"));
        },

        testRenderSizeChange: function() {
            var choices = [
                {value: "a", text: "A", data: 123},
                {value: "b", text: "B", data: 456},
                {value: "c", text: "C", data: 789}
            ];
            this.widget
                .set("choices", choices)
                .set("size", 3)
                .render(this.container)
                .set("size", 5);
            Assert.areEqual(
                5, this.widget.fieldNode.one("select").get("size"));
        },

        testMultiple: function() {
            Assert.areEqual(false, this.widget.get("multiple"));
        },

        testRenderMultiple: function() {
            var choices = [
                {value: "a", text: "A", data: 123},
                {value: "b", text: "B", data: 456},
                {value: "c", text: "C", data: 789}
            ];
            this.widget
                .set("choices", choices)
                .set("multiple", true)
                .render(this.container);
            Assert.isTrue(
                this.widget.fieldNode.one("select")
                    .hasAttribute("multiple"));
        },

        testRenderMultipleChange: function() {
            var choices = [
                {value: "a", text: "A", data: 123},
                {value: "b", text: "B", data: 456},
                {value: "c", text: "C", data: 789}
            ];
            this.widget
                .set("choices", choices)
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
            this.container.remove();
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
            this.widget.set(
                "packageSets",
                package_sets_collection);
            var choices = this.widget.get("choices");
            ArrayAssert.itemsAreEqual(
                ["foo", "bar", "baz"],
                attrselect("value")(choices));
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

    Y.Test.Runner.add(suite);

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
