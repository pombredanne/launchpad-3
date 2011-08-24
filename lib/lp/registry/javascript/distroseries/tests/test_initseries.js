/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Tests for DistroSeries Initialization.
 *
 * @module lp.registry.distroseries.initseries
 * @submodule test
 */

YUI.add('lp.registry.distroseries.initseries.test', function(Y) {

    var namespace = Y.namespace('lp.registry.distroseries.initseries.test');

    var Assert = Y.Assert,
        ArrayAssert = Y.ArrayAssert,
        attrselect = Y.lp.extras.attrselect;

    var suite = new Y.Test.Suite("distroseries.initseries Tests");
    var initseries = Y.lp.registry.distroseries.initseries;

    var testDeriveDistroSeriesActionsWidget = {
        name: 'TestDeriveDistroSeriesActionsWidget',

        setUp: function() {
            this.actions = this.makeActionsDiv();
            this.widget = new initseries.DeriveDistroSeriesActionsWidget({
                duration: 0,
                srcNode: this.actions,
                context: {
                    name: "hagfish",
                    displayname: "Horrid Hagfish",
                    self_link: "http://ex.com/api/devel/deribuntu/snaggle"
                },
                deriveFromChoices: {
                    get: function(name) {
                        if (name === "parents") {
                            return ["4", "5"];
                        }
                        else if (name === "overlays") {
                            return [true, false];
                        }
                        else if (name === "overlay_pockets") {
                            return ['Updates', null];
                        }
                        else if (name === "overlay_components") {
                            return ['restricted', null];
                        }
                        else {
                            Assert.fail("Unrecognized property: " + name);
                            return null; // Keep lint quiet.
                        }
                    }
                },
                architectureChoice: {
                    get: function(name) {
                        Assert.areEqual("choice", name);
                        return [
                            {value: "i386", text: "i386"},
                            {value: "sparc", text: "sparc"}
                        ];
                    }
                },
                packagesetChoice: {
                    get: function(name) {
                        Assert.areEqual("choice", name);
                        return [
                            {value: "4", text: "FooSet"},
                            {value: "5", text: "BarSet"}
                        ];
                    }
                },
                packageCopyOptions: {
                    get: function(name) {
                        Assert.areEqual("choice", name);
                        return {
                            value: "rebuild",
                            text: "Copy Source and Rebuild"
                        };
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
            }, 90);
        },

        testSubmit: function() {
            var io = false;
            this.widget.client = {
                named_post: function(path, operation, config) {
                    io = true;
                    Assert.areEqual(
                        "http://ex.com/api/devel/deribuntu/snaggle",
                        path);
                    Assert.areEqual("initDerivedDistroSeries", operation);
                    ArrayAssert.itemsAreEqual(
                        ["4", "5"],
                        config.parameters.parents);
                    ArrayAssert.itemsAreEqual(
                        [true, false],
                        config.parameters.overlays);
                    ArrayAssert.itemsAreEqual(
                        ['Updates', null],
                        config.parameters.overlay_pockets);
                    ArrayAssert.itemsAreEqual(
                        ['restricted', null],
                        config.parameters.overlay_components);
                    ArrayAssert.itemsAreEqual(
                        ["i386", "sparc"],
                        config.parameters.architectures);
                    ArrayAssert.itemsAreEqual(
                        ["4", "5"],
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
        Y.lp.app.formwidgets.test.testFormActionsWidget,
        testDeriveDistroSeriesActionsWidget);
    suite.add(new Y.Test.Case(testDeriveDistroSeriesActionsWidget));

    var testDeriveDistroSeriesSetup = {
        name: 'TestDeriveDistroSeriesSetup',

        setUp: function() {
            var node = Y.Node.create(
                '<div style="display:none;"' +
                '  class="unseen" id="initseries-form-container">' +
                '  <div>' +
                '    <form action="">' +
                '      <table class="form" id="launchpad-form-widgets">' +
                '      </table>' +
                '      <div class="actions" id="launchpad-form-actions">' +
                '        <input type="submit" id="field.actions.initialize"' +
                '          name="field.actions.initialize" ' +
                '          value="Initialize Series" class="button" />' +
                '      </div>' +
                '    </form>' +
                '  </div>' +
                '</div>');
            Y.one('body').appendChild(node);
        },

        testIsFirstDerivation: function() {
            var cache = {is_first_derivation: true};
            var form_actions = initseries.setupWidgets(cache);
            initseries.setupInteraction(form_actions, cache);

            // No pre-populated parent.
            ArrayAssert.itemsAreEqual(
                [],
                form_actions.deriveFromChoices.get("parents"));
        },

        testDefaultRebuildChoice: function() {
            var cache = {is_first_derivation: true};
            var form_actions = initseries.setupWidgets(cache);
            Assert.areEqual(
                "copy",
                form_actions.packageCopyOptions.get('choice').value);
        },

        testIsNotFirstDerivation: function() {
            var cache = {
                is_first_derivation: false,
                previous_series: {
                    api_uri: '/ubuntu/natty',
                    value: '3',
                    title: 'Ubunty: Natty'
                },
                previous_parents: [
                    {api_uri: '/debian/sid',
                     value: '4', title: 'Debian: Sid'},
                    {api_uri: '/zz/aa',
                     value: '5', title: 'ZZ: aa'}
                ]
            };
            var form_actions = initseries.setupWidgets(cache);
            // Monkeypatch LP client.
            var client = {
                get: function(path, config) {
                    Assert.areEqual(
                        "/ubuntu/natty/architectures",
                        path);
                    // Return previous_series' architectures.
                    var arches = new Y.lp.client.Collection(
                        null,
                        {entries: [
                            {'architecture_tag': 'hppa'},
                            {'architecture_tag': 'i386'}]},
                        null);
                    config.on.success(arches);
                }
            };
            form_actions.architectureChoice.client = client;
            initseries.setupInteraction(form_actions, cache);

            // Parents are populated.
            ArrayAssert.itemsAreEqual(
                ['4', '5'],
                form_actions.deriveFromChoices.get("parents"));
            // No packageset choice widget.
            Assert.isNull(form_actions.packagesetChoice);
            // The architecture picker features the architectures
            // from the previous series.
            ArrayAssert.itemsAreEqual(
                ['hppa', 'i386'], attrselect("value")(
                    form_actions.architectureChoice.get("choices")));
         }
    };

    suite.add(new Y.Test.Case(testDeriveDistroSeriesSetup));
    namespace.suite = suite;

}, "0.1", {"requires": [
               'test', 'console', 'node-event-simulate',
               'lp.app.formwidgets.test', 'lp.extras',
               'lp.registry.distroseries.initseries']});
