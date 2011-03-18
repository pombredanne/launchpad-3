/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use(
        'test', 'console', 'lp.registry.distroseries.initseries',
        function(Y) {

    var Assert = Y.Assert;

    var suite = new Y.Test.Suite("distroseries.initseries Tests");
    var initseries = Y.lp.registry.distroseries.initseries;
    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

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

    Y.Test.Runner.add(suite);

    Y.Test.Runner.on('complete', function() {
        Y.one('body').append(
            '<p id="complete">Test status: complete</p>');
    });

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
