/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../icing/yui/current/build/',
    filter: 'raw',
    combine: false
    }).use('yuitest', 'console', 'lp', function(Y) {

    var Assert = Y.Assert;  // For easy access to isTrue(), etc.

    Y.Test.Runner.add(new Y.Test.Case({
        name: "activate_collapsibles",

        setUp: function() {
            this.container = Y.get('#container-of-stuff');

            // Reset the container to its default contents.
            this.container.set('innerHTML',
                '<div id="container-of-stuff">\n' +
                '  <fieldset class="collapsible collapsed">\n' +
                '    <legend>My expander, let me collapse it</legend>\n' +
                '    <p>Here\'s some content</p>\n' +
                '  </fieldset>\n' +
                '</div>'
            );
        },

        test_activate_collapsibles_creates_anchor: function() {
            // activate_collapsibles() creates an anchor to handle the
            // business of toggling the collapsible open and shut.
            Y.lp.activate_collapsibles();

            var anchor = this.container.query('a');
            Assert.isNotNull(
                anchor, "activate_collapsibles() should create an anchor");

            // The anchor is for decoration only, so its URL is a simple
            // placeholder.
            Assert.areEqual(
                anchor.get('href'), window.location + '#');
        },

        test_activate_collapsibles_removes_legend: function() {
            // activate_collapsibles() removes the legend when it
            // creates the anchor.
            Y.lp.activate_collapsibles();

            Assert.isNull(
                this.container.query('legend'),
                "activate_collapsibles() should remove <legend>s");
        },

        test_activate_collapsibles_adds_icon_to_anchor: function() {
            // activate_collapsibles() adds an icon to the anchor it
            // creates.
            Y.lp.activate_collapsibles();

            var anchor = this.container.query('a');
            var icon = anchor.query('img');

            Assert.isNotNull(
                icon,
                "activate_collapsibles() should add an icon to the anchor " +
                "it creates")

            // By default, the icon is the treeExpanded icon.
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeExpanded'));
            Assert.isTrue(icon.hasClass('collapseIcon'));
        },
    }));

    var yconsole = new Y.Console({
        newestOnTop: false
    });
    yconsole.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
