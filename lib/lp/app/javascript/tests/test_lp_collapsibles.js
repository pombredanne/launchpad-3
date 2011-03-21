/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'lp', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("Collapsibles Tests");
suite.add(new Y.Test.Case({
    name: "activate_collapsibles",

    _should: {
        fail: {
            test_toggle_collapsible_fails_on_wrapperless_collapsible: true,
            test_toggle_collapsible_fails_on_iconless_collapsible: true,
        }
    },

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
        this.container = Y.one('#container-of-stuff');
        this.container.set('innerHTML', '');
        this.container.appendChild(
            this.default_fieldset_node.cloneNode(
                this.default_fieldset_node));
    },

    test_activate_collapsibles_creates_anchor: function() {
        // activate_collapsibles() creates an anchor to handle the
        // business of toggling the collapsible open and shut.
        Y.lp.activate_collapsibles();

        var anchor = this.container.one('a');
        Assert.isNotNull(
            anchor, "activate_collapsibles() should create an anchor");

        // The anchor is for decoration only, so its URL is a simple
        // placeholder.
        Assert.areEqual('javascript:void(0);', anchor.get('href'));
    },

    test_activate_collapsibles_adds_icon_to_anchor: function() {
        // activate_collapsibles() adds an icon to the anchor it
        // creates.
        Y.lp.activate_collapsibles();

        var anchor = this.container.one('a');
        var icon = anchor.one('img');

        Assert.isNotNull(
            icon,
            "activate_collapsibles() should add an icon to the anchor " +
            "it creates");

        // By default, the icon is the treeExpanded icon.
        Assert.areNotEqual(
            -1, icon.get('src').indexOf('/@@/treeExpanded'));
        Assert.isTrue(icon.hasClass('collapseIcon'));
    },

    test_activate_collapsibles_adds_span_to_anchor: function() {
        // activate_collapsibles() adds a span to the anchor it creates.
        Y.lp.activate_collapsibles();

        var anchor = this.container.one('a');
        var span = anchor.one('span');

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

        var collapsible = this.container.one('.collapsible');
        Assert.isNotNull(
            collapsible.one('.collapseWrapper'),
            "The collapseWrapper div should be within the collapsible.");
    },

    test_activate_collapsibles_collapses_collapsed: function() {
        // If a collapsible has the class 'collapsed',
        // activate_collapsibles() will pre-collapse it.
        var collapsible = this.container.one('.collapsible');
        collapsible.addClass('collapsed');

        Y.lp.activate_collapsibles();

        var icon = collapsible.one('img');
        var wrapper_div = collapsible.one('.collapseWrapper');
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

        var collapsible = this.container.one('.collapsible');
        var icon = collapsible.one('img');
        var wrapper_div = collapsible.one('.collapseWrapper');
        this.wait(function() {
            Assert.isFalse(wrapper_div.hasClass('lazr-closed'));
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeExpanded'));
        }, 500);
    },

    test_toggle_collapsible_opens_collapsed_collapsible: function() {
        // Calling toggle_collapsible() on a collapsed collapsible will
        // toggle its state to open.
        Y.lp.activate_collapsibles();
        var collapsible = this.container.one('.collapsible');
        var wrapper_div = collapsible.one('.collapseWrapper');
        wrapper_div.addClass('lazr-closed');

        Y.lp.toggle_collapsible(collapsible);
        this.wait(function() {
            // The collapsible's wrapper div will now be open.
            var icon = collapsible.one('img');
            Assert.isFalse(wrapper_div.hasClass('lazr-closed'));
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeExpanded'));
        }, 500);
    },

    test_toggle_collapsible_closes_open_collapsible: function() {
        // Calling toggle_collapsible() on an open collapsible will
        // toggle its state to closed.
        var collapsible = this.container.one('.collapsible');

        Y.lp.activate_collapsibles();
        Y.lp.toggle_collapsible(collapsible);

        this.wait(function() {
            // The collapsible's wrapper div will now be closed.
            var icon = collapsible.one('img');
            var wrapper_div = collapsible.one('.collapseWrapper');
            Assert.isTrue(wrapper_div.hasClass('lazr-closed'));
            Assert.areNotEqual(
                -1, icon.get('src').indexOf('/@@/treeCollapsed'));
        }, 500);

    },

    test_toggle_collapsible_fails_on_wrapperless_collapsible: function() {
        // If the collapsible passed to toggle_collapsible() has no
        // wrapper div, toggle_collapsible() will raise an error.
        var invalid_collapsible = Y.Node.create(
            '<fieldset class="collapsible"> ' +
            '    <img src="#" class="collapseIcon" />' +
            '    <p>No contents!</p>' +
            '</fieldset>');

        Y.lp.toggle_collapsible(invalid_collapsible);
    },

    test_toggle_collapsible_fails_on_iconless_collapsible: function() {
        // If the collapsible passed to toggle_collapsible() has no
        // icon, toggle_collapsible() will raise an error.
        var invalid_collapsible = Y.Node.create(
            '<fieldset class="collapsible"> ' +
            '    <div class="collapseWrapper">' +
            '        <p>No icon!</p>' +
            '    </div>' +
            '</fieldset>');

        Y.lp.toggle_collapsible(invalid_collapsible);
    },

    test_activate_collapsibles_doesnt_fail_on_legendless_collapsible:
        function() {
        // If a collapsible doesn't have a wrapper div,
        // activate_collapsibles() won't fail, since there might be
        // other collapsibles on the page.
        var invalid_collapsible = Y.Node.create(
            '<fieldset class="collapsible"> ' +
            '    <img src="#" class="collapseIcon" />' +
            '    <p>No legend!</p>' +
            '</fieldset>');

        var valid_collapsible = this.container.one('.collapsible');
        this.container.insertBefore(invalid_collapsible, valid_collapsible);
        Y.lp.activate_collapsibles();

        // The standard, valid collapsible is still set up correctly.
        Assert.isNotNull(
            valid_collapsible.one('.collapseWrapper'),
            "activate_collapsibles() should have added a wrapper div for " +
            "the valid collapsible.");
    },

    test_activate_collapsibles_sets_up_multiple_collapsibles: function() {
        // If there are several collapsibles on a page,
        // activate_collapsibles() will activate them all.
        for (i = 0; i < 5; i++) {
            var new_collapsible =
                this.default_fieldset_node.cloneNode(
                    this.default_fieldset_node);

            this.container.appendChild(new_collapsible);
        }

        Y.lp.activate_collapsibles();
        Y.all('.collapsible').each(function(collapsible) {
            Assert.isNotNull(
                collapsible.one('.collapseWrapper'),
                "activate_collapsibles() should have added a wrapper div " +
                "to all collapsibles.");
        });
    },

    test_activate_collapsibles_handles_no_collapsibles: function() {
        // If there are no collapsibles in a page,
        // activate_collapsibles() will still complete successfully.
        this.container.set('innerHTML', '');
        Y.lp.activate_collapsibles();
    },

    test_activate_collapsibles_removes_existing_anchors: function() {
        // If there's already an anchor within a collapsible fieldset's
        // legend it will be removed before its contents are moved into
        // the new anchor created by activate_collapsibles(). This is to
        // avoid leaving clickable-through links in the collapsible
        // header.
        var new_collapsible = Y.Node.create(
            '<fieldset class="collapsible"> ' +
            '   <legend>' +
            '       <a id="should-be-removed"' +
            '           href="http://launchpad.net">' +
            '         With a link in it' +
            '       </a>' +
            '   </legend>' +
            '   <p>Some contents</p>' +
            '</fieldset>');

        this.container.set('innerHTML', '');
        this.container.appendChild(new_collapsible);
        Y.lp.activate_collapsibles();

        var collapsible = this.container.one('.collapsible');
        Assert.isNull(
            this.container.one('#should-be-removed'),
            "The should-be-removed link should have been removed");
    },

    test_activate_collapsibles_doesnt_reactivate_collapsibles: function() {
        // If activate_collapsibles() has already been called, calling
        // it again won't break the existing collapsibles.
        Y.lp.activate_collapsibles();
        var collapsible = this.container.one('.collapsible');
        var anchor = collapsible.one('a');
        var span = anchor.one('span');
        var original_span_contents = span.get('innerHTML');
        var wrapper = collapsible.one('.collapseWrapper');
        var original_wrapper_contents = wrapper.get('innerHTML');

        // Calling activate_collapsibles() shouldn't break things.
        Y.lp.activate_collapsibles();
        collapsible = this.container.one('.collapsible');
        anchor = collapsible.one('a');
        span = anchor.one('span');
        wrapper = collapsible.one('.collapseWrapper');

        Assert.isNotNull(
            anchor, "Existing collapsibles' anchors should be intact.");

        var icon = anchor.one('img');
        Assert.isNotNull(
            icon,
            "Existing collapsibles' icons should be intact.");

        Assert.areEqual(
            original_span_contents, span.get('innerHTML'),
            "Existing collapsibles' spans should be intact.");

        Assert.isNotNull(
            wrapper,
            "Existing collapsibles' wrapper divs should be intact.");
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

var yui_console = new Y.Console({
    newestOnTop: false
});
yui_console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
