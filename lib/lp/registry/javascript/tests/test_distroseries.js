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

    var testCheckBoxListWidget = {
        name: 'TestCheckBoxListWidget',

        setUp: function() {
            this.container = Y.Node.create("<div />");
            this.widget = new initseries.CheckBoxListWidget();
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
        },

        testRenderWithName: function() {
            this.widget.set("name", "field");
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            ArrayAssert.itemsAreEqual(
                ["field", "field"],
                this.container.all("li > input").get("name"));
        },

        testRenderWithNameChange: function() {
            this.widget.set("name", "field");
            this.widget.set("choices", ["a", "b"]);
            this.widget.render(this.container);
            this.widget.set("name", "plain");
            ArrayAssert.itemsAreEqual(
                ["plain", "plain"],
                this.container.all("li > input").get("name"));
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
        }

    };

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
                        widget.fieldNode.contains(widget.spinner));
                    config.on.start();
                    Assert.isTrue(
                        widget.fieldNode.contains(widget.spinner));
                    config.on.end();
                    Assert.isFalse(
                        widget.fieldNode.contains(widget.spinner));
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

    Y.Test.Runner.add(suite);

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
