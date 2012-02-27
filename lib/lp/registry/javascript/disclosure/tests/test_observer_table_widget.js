/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.disclosure.observertable.test', function (Y) {

    var tests = Y.namespace('lp.registry.disclosure.observertable.test');
    tests.suite = new Y.Test.Suite(
        'lp.registry.disclosure.observertable Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.registry.disclosure.observertable_tests',

        setUp: function () {
            this.observer_data = [
            {'name': 'fred', 'display_name': 'Fred Bloggs',
             'role': '(Maintainer)', web_link: '~fred',
             'permissions': {'P1': 's1', 'P2': 's2'}},
            {'name': 'john', 'display_name': 'John Smith',
             'role': '', web_link: '~smith',
            'permissions': {'P1': 's1', 'P3': 's3'}}
            ];
            this.sharing_permissions = [
                {'value': 's1', 'name': 'S1',
                 'title': 'Sharing 1'},
                {'value': 's2', 'name': 'S2',
                 'title': 'Sharing 2'}
            ];
            this.access_policies = {
                'P1': 'Policy 1',
                'P2': 'Policy 2',
                'P3': 'Policy 3'
            };
        },

        tearDown: function () {
            if (Y.Lang.isObject(this.observer_table)) {
                this.cleanup_widget(this.observer_table);
            }
            Y.one('#observer-table').empty();
        },

        /* Helper function to clean up a dynamically added widget instance. */
        cleanup_widget: function(widget) {
            // Nuke the boundingBox, but only if we've touched the DOM.
            if (widget.get('rendered')) {
                var bb = widget.get('boundingBox');
                bb.get('parentNode').removeChild(bb);
            }
            // Kill the widget itself.
            widget.destroy();
        },

        _create_Widget: function() {
            var ns = Y.lp.registry.disclosure.observertable;
            return new ns.ObserverTableWidget({
                observers: this.observer_data,
                sharing_permissions: this.sharing_permissions,
                access_policy_types: this.access_policies
            });
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.disclosure.observertable,
                "We should be able to locate the " +
                "lp.registry.disclosure.observertable module");
        },

        test_widget_can_be_instantiated: function() {
            this.observer_table = this._create_Widget();
            Y.Assert.isInstanceOf(
                Y.lp.registry.disclosure.observertable.ObserverTableWidget,
                this.observer_table,
                "Observer table failed to be instantiated");
        },

        test_observers_render: function() {
            this.observer_table = this._create_Widget();
            this.observer_table.render();
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.registry.disclosure.observertable']});
