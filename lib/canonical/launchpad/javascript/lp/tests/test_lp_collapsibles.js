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
            '<fieldset class="collapsible" />');
        this.default_fieldset_content_node = Y.Node.create(
            "<p>Here's some content for ya.</p>");

        // Build the fieldset that we want to make collapsible.
        this.default_fieldset_node.appendChild(
            this.default_legend_node.cloneNode(
                this.default_legend_node));

        this.default_fieldset_node.appendChild(
            this.default_fieldset_content_node.cloneNode(
                this.default_fieldset_content_node));

        // Reset the container to its default contents.
        this.container = Y.get('#container-of-stuff');
        this.container.set('innerHTML', '');
        this.container.appendChild(
            this.default_fieldset_node.cloneNode(
                this.default_fieldset_node));
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
    },

    test_activate_collapsibles_adds_wrapper: function() {
        // activate_collapsibles() wraps the fieldset contents
        // (other than the legend) in a div which can then be
        // collapsed.
        Y.lp.activate_collapsibles();

        var wrapper_div = this.container.get('.collapseWrapper');
        Assert.isNotNull(
            wrapper_div,
            "activate_collapsibles() should add a wrapper div");

        var collapsible = this.container.query('.collapsible')
        Assert.isNotNull(
            collapsible.query('.collapseWrapper'),
            "The collapseWrapper div should be within the collapsible.");
    },

    test_activate_collapsibles_collapses_collapsed: function() {
        // If a collapsible has the class 'collapsed',
        // activate_collapsibles() will pre-collapse it.
        var collapsible = this.container.query('.collapsible');
        collapsible.addClass('collapsed');

        Y.lp.activate_collapsibles();

        var icon = collapsible.query('img');
        var wrapper_div = collapsible.query('.collapseWrapper');
        this.wait(function() {
            Assert.isTrue(wrapper_div.hasClass('lazr-closed'));
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeCollapsed'));
        }, 500);
    },

    test_activate_collapsibles_doesnt_collapse_uncollapsed: function() {
        // If a collapsible doesn't have the 'collapsed' class it
        // won't be pre-collapsed.
        Y.lp.activate_collapsibles();

        var collapsible = this.container.query('.collapsible');
        var icon = collapsible.query('img');
        var wrapper_div = collapsible.query('.collapseWrapper');
        this.wait(function() {
            Assert.isFalse(wrapper_div.hasClass('lazr-closed'));
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeExpanded'));
        }, 500);
    },

    test_toggle_collapsible_opens_collapsed_collapsible: function() {
        // Calling toggle_collapsible() on a collapsed collapsible will
        // toggle its state to open.
        var collapsible = this.container.query('.collapsible');
        collapsible.addClass('collapsed');

        Y.lp.activate_collapsibles();
        this.wait(function() {
            Y.lp.toggle_collapsible(collapsible);
        }, 500);

        // The collapsible's wrapper div will now be open.
        var wrapper_div = collapsible.query('.collapseWrapper');
        this.wait(function() {
            Assert.isTrue(wrapper_div.hasClass('lazr-open'));
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeExpanded'));
        }, 500);
    },

    test_toggle_collapsible_closes_open_collapsible: function() {
        // Calling toggle_collapsible() on an open collapsible will
        // toggle its state to closed.
        var collapsible = this.container.query('.collapsible');

        Y.lp.activate_collapsibles();
        this.wait(function() {
            Y.lp.toggle_collapsible(collapsible);
        }, 500);

        // The collapsible's wrapper div will now be closed.
        var wrapper_div = collapsible.query('.collapseWrapper');
        this.wait(function() {
            Assert.isTrue(wrapper_div.hasClass('lazr-closed'));
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeCollapsed'));
        }, 500);
    },
}));

var yui_console = new Y.Console({
    newestOnTop: false
});
yui_console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
