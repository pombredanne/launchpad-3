/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use(
        'test', 'console', 'lp.registry.distroseries.initseries',
        function(Y) {

    var initseries = Y.lp.registry.distroseries.initseries;
    var suite = new Y.Test.Suite("distroseries.initseries Tests");

    var Assert = Y.Assert;

    suite.add(new Y.Test.Case({
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
        }

        }));

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
