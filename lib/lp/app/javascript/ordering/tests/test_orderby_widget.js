/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.orderbybar.test', function(Y) {

var basic_test = Y.namespace('lp.orderbybar.test');

var suite = new Y.Test.Suite('OrderByBar Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;

suite.add(new Y.Test.Case({

    name: 'orderbybar_widget_tests',

    _should: {
        error: {
            test_sort_order_validator:
                new Error('sort_order must be either "asc" or "desc"'),
            test_active_sort_validator:
                new Error('active attribute was not found in sort_keys')
        }
    },

    /**
     * Unpack a list of key, name pairs into individual lists.
     *
     * [[Foo, 'Foo Item'], ['Bar', 'Bar item']] becomes
     * ['Foo', 'Bar'] and ['Foo Item', 'Bar Item'].
     */
    getIdsAndNames: function(keys) {
        var ids = [];
        var names = [];
        var len = keys.length;
        var i;
        for (i=0; i<len; i++) {
            ids.push(keys[i][0]);
            names.push(keys[i][1]);
        }
        return [ids, names];
    },

    /*
     * Helper function to create the srcNode on the page.  Widgets
     * will append to the body tag if srcNode is not supplied.
     */
    makeSrcNode: function(id) {
        // Calling the widget's destroy method will clean this up.
        var parent_node = Y.Node.create('<div></div>');
        parent_node.set('id', id);
        Y.one('body').appendChild(parent_node);
    },

    test_default_sort_keys: function() {
        // The default sort keys should exist in a newly created widget.
        var orderby = new Y.lp.ordering.OrderByBar();
        var expected_sort_keys = [
            ['bugnumber', 'Bug number'],
            ['bugtitle', 'Bug title'],
            ['status', 'Status'],
            ['importance', 'Importance'],
            ['bug-heat-icons', 'Bug heat'],
            ['package', 'Package name'],
            ['milestone', 'Milestone'],
            ['assignee', 'Assignee'],
            ['bug-age', 'Bug age']
        ];
        var expected = this.getIdsAndNames(expected_sort_keys);
        var actual = this.getIdsAndNames(orderby.get('sort_keys'));
        ArrayAssert.itemsAreSame(expected[0], actual[0]);
        ArrayAssert.itemsAreSame(expected[1], actual[1]);
    },

    test_user_supplied_sort_keys: function() {
        // Call sites can supply their own sort keys to a widget.
        var user_supplied_sort_keys = [
            ['foo', 'Foo item'],
            ['bar', 'Bar item'],
            ['baz', 'Baz item']
        ];
        var orderby = new Y.lp.ordering.OrderByBar({
            sort_keys: user_supplied_sort_keys});
        var expected = this.getIdsAndNames(user_supplied_sort_keys);
        var actual = this.getIdsAndNames(orderby.get('sort_keys'));
        ArrayAssert.itemsAreSame(expected[0], actual[0]);
        ArrayAssert.itemsAreSame(expected[1], actual[1]);
    },

    test_rendered_items_html: function() {
        // We should be able to get a node from the DOM via an ID
        // created from sort keys, and the name should be used as
        // a button display name in HTML.
        var test_sort_keys = [
            ['foo', 'Foo item'],
            ['bar', 'Bar item']
        ];
        this.makeSrcNode('test-div');
        var orderby = new Y.lp.ordering.OrderByBar({
            sort_keys: test_sort_keys,
            srcNode: Y.one('#test-div'),
            active: 'foo'
        });
        orderby.render();
        var foo_node = Y.one('#sort-foo');
        Assert.isNotNull(foo_node);
        Assert.areEqual(foo_node.get('firstChild').get('text'), 'Foo item');
        var bar_node = Y.one('#sort-bar');
        Assert.isNotNull(bar_node);
        Assert.areEqual(bar_node.get('firstChild').get('text'), 'Bar item');
        orderby.destroy();
    },

    test_render_active_sort_default: function() {
        // Confirm that there is a default active sort class applied.
        this.makeSrcNode('test-div');
        var orderby = new Y.lp.ordering.OrderByBar({
            srcNode: Y.one('#test-div')
        });
        orderby.render();
        var li_node = Y.one('#sort-importance');
        Assert.isTrue(li_node.hasClass('active-sort'));
        orderby.destroy();
    },

    test_render_active_sort_user_supplied: function() {
        // The active sort class is also set when "active"
        // is supplied via config.
        this.makeSrcNode('test-div');
        var orderby = new Y.lp.ordering.OrderByBar({
            srcNode: Y.one('#test-div'),
            active: 'status'
        });
        orderby.render();
        var li_node = Y.one('#sort-status');
        Assert.isTrue(li_node.hasClass('active-sort'));
        orderby.destroy();
    },

    test_active_sort_arrow_display_asc: function() {
        // Buttons using "asc" order get a down arrow added to the li.
        this.makeSrcNode('test-div');
        var orderby = new Y.lp.ordering.OrderByBar({
            srcNode: Y.one('#test-div'),
            sort_order: 'asc'
        });
        orderby.render();
        var arrow_span = Y.one('.active-sort span');
        var expected_text = Y.Node.create('&darr;').get('text');
        Assert.areEqual(expected_text, arrow_span.get('innerHTML'));
        orderby.destroy();
    },

    test_active_sort_arrow_display_desc: function() {
        // Buttons using "desc" order get an up arrow added to the li.
        this.makeSrcNode('test-div');
        var orderby = new Y.lp.ordering.OrderByBar({
            srcNode: Y.one('#test-div'),
            sort_order: 'desc'
        });
        orderby.render();
        var arrow_span = Y.one('.active-sort span');
        var expected_text = Y.Node.create('&uarr;').get('text');
        Assert.areEqual(expected_text, arrow_span.get('innerHTML'));
        orderby.destroy();
    },

    test_active_sort_validator: function() {
        // This should fail because we do not allow
        // a "active" value not found in sort_keys.
        var test_sort_keys = [
            ['foo', 'Foo item'],
            ['bar', 'Bar item']
        ];
        var orderby = new Y.lp.ordering.OrderByBar({
            sort_keys: test_sort_keys,
            active: 'foobarbazdonotexists',
        });
        orderby.render();
    },

    test_sort_order_validator: function() {
        // This should fail when using a sort order
        // other than "asc" or "desc".
        var orderby = new Y.lp.ordering.OrderByBar({
            sort_order: 'foobar'
        });
        orderby.render();
    },

    test_click_current_sort_arrow_changes: function() {
        // Clicking the currently sorted on button should change
        // the arrow and widget state to show a sort change should
        // happen.
        this.makeSrcNode('test-div');
        var test_sort_keys = [
            ['foo', 'Foo item'],
            ['bar', 'Bar item']
        ];
        var orderby = new Y.lp.ordering.OrderByBar({
            srcNode: Y.one('#test-div'),
            sort_keys: test_sort_keys,
            active: 'foo',
            sort_order: 'asc'
        });
        orderby.render();
        var foo_node = Y.one('#sort-foo');
        var expected_starting_text = Y.Node.create('&darr;').get('text');
        var expected_ending_text = Y.Node.create('&uarr;').get('text');
        Assert.areEqual(
            expected_starting_text, foo_node.one('span').get('innerHTML'));
        Assert.isTrue(foo_node.one('span').hasClass('asc'));
        foo_node.simulate('click');
        Assert.areEqual(
            expected_ending_text, foo_node.one('span').get('innerHTML'));
        Assert.isTrue(foo_node.one('span').hasClass('desc'));
        orderby.destroy();
    },

    test_click_different_sort_arrows_change: function() {
        // Clicking a button other than the currently sorted on button
        // should change the arrow and widget state to show a sort
        // change should happen.
        this.makeSrcNode('test-div');
        var test_sort_keys = [
            ['foo', 'Foo item'],
            ['bar', 'Bar item']
        ];
        var orderby = new Y.lp.ordering.OrderByBar({
            srcNode: Y.one('#test-div'),
            sort_keys: test_sort_keys,
            active: 'foo',
            sort_order: 'asc'
        });
        orderby.render();
        var bar_node = Y.one('#sort-bar');
        bar_node.simulate('click');
        var expected_arrow = Y.Node.create('&darr;').get('text');
        Assert.areEqual(
            expected_arrow, bar_node.one('span').get('innerHTML'));
        Assert.isTrue(bar_node.one('span').hasClass('asc'));
        // Ensure the original button doesn't have sort classes.
        Assert.isFalse(Y.one('#sort-foo').one('span').hasClass('asc'));
        Assert.isFalse(Y.one('#sort-foo').one('span').hasClass('desc'));
        orderby.destroy();
    },

    test_sort_event_fires_with_data: function() {
        // A custom sort event fires from the widget to signal a
        // sort order change should happen in the page.  The
        // callback receives the objects sort_clause for use in
        // a URL.
        this.makeSrcNode('test-div');
        var test_sort_keys = [
            ['foo', 'Foo item'],
            ['bar', 'Bar item']
        ];
        var orderby = new Y.lp.ordering.OrderByBar({
            srcNode: Y.one('#test-div'),
            sort_keys: test_sort_keys,
            active: 'foo',
            sort_order: 'asc'
        });
        orderby.render();
        var foo_node = Y.one('#sort-foo');
        var event_fired = false;
        Y.on('orderbybar:sort', function(e) {
            event_fired = true;
            // Confirm that we get the sort statement we expect, too.
            Assert.areEqual('-foo', e);
        });
        foo_node.simulate('click');
        Assert.isTrue(event_fired);
        orderby.destroy();
    }

}));

basic_test.suite = suite;

}, '0.1', {'requires': ['test', 'node-event-simulate', 'lp.ordering']});
