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
            // Create some individual Nodes that we can work with in
            // tests.
            this.default_legend_node = Y.Node.create(
                "<legend>My expander, let me collapse it</legend>");
            this.default_fieldset_node = Y.Node.create(
                '<fieldset class="collapsible collapsed" />');
            this.default_fieldset_content_node = Y.Node.create(
                "<p>Here's some content for ya.</p>");

            // Build the fieldset that we want to make collapsible.
            this.default_fieldset_node.appendChild(
                this.default_legend_node.cloneNode(
                    this.default_legend_node));

            this.default_fieldset_node.appendChild(
                this.default_fieldset_content_node);

            // Reset the container to its default contents.
            this.container = Y.get('#container-of-stuff');
            this.container.set('innerHTML', '');
            this.container.appendChild(this.default_fieldset_node);
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

        test_activate_collapsibles_adds_span_to_anchor: function() {
            // activate_collapsibles() adds a span to the anchor it creates.
            Y.lp.activate_collapsibles();

            var anchor = this.container.query('a');
            var span = anchor.query('span');

            Assert.isNotNull(
                span,
                "activate_collapsibles() should add a span to the anchor");

            // The span's contents will be the same as the original
            // legend's contents.
            Assert.areEqual(
                this.default_legend_node.get('innerHTML'),
                span.get('innerHTML'));
        }
    }));

    var yconsole = new Y.Console({
        newestOnTop: false
    });
    yconsole.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
