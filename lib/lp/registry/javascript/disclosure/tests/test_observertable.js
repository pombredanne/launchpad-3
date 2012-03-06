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
             'self_link': '~fred',
             'permissions': {'P1': 's1', 'P2': 's2'}},
            {'name': 'john', 'display_name': 'John Smith',
             'role': '', web_link: '~smith', 'self_link': '~smith',
            'permissions': {'P1': 's1', 'P3': 's3'}}
            ];
            this.sharing_permissions = [
                {'value': 's1', 'title': 'S1',
                 'description': 'Sharing 1'},
                {'value': 's2', 'title': 'S2',
                 'description': 'Sharing 2'}
            ];
            this.access_policies = {
                'P1': 'Policy 1',
                'P2': 'Policy 2',
                'P3': 'Policy 3'
            };
        },

        tearDown: function () {
            Y.one('#observer-table').empty(true);
        },

        _create_Widget: function() {
            var ns = Y.lp.registry.disclosure.observertable;
            return new ns.ObserverTableWidget({
                anim_duration: 0.001,
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

        // The given observer is correctly rendered.
        _test_observer_rendered: function(observer) {
            // The observer row
            Y.Assert.isNotNull(
                Y.one('#observer-table tr[id=permission-'
                      + observer.name + ']'));
            // The delete link
            Y.Assert.isNotNull(
                Y.one('#observer-table td[id=remove-'
                      + observer.name + '] a'));
            // The access policy sharing permissions
            var permission;
            for (permission in observer.permissions) {
                if (observer.permissions.hasOwnProperty(permission)) {
                    Y.Assert.isNotNull(
                        Y.one('#observer-table td[id=td-permission-'
                              + observer.name + '] ul li '
                              + 'span[id='+permission+'-permission] '
                              + 'span.value'));
                }
            }
        },

        // The observer table is correctly rendered.
        test_render: function() {
            this.observer_table = this._create_Widget();
            this.observer_table.render();
            var self = this;
            Y.Array.each(this.observer_data, function(observer) {
                self._test_observer_rendered(observer);
            });
        },

        // The add_observer call adds the observer to the table.
        test_observer_add: function() {
            this.observer_table = this._create_Widget();
            this.observer_table.render();
            var new_observer = {
                'name': 'joe', 'display_name': 'Joe Smith',
                'role': '(Maintainer)', web_link: '~joe',
                'self_link': '~joe',
                'permissions': {'P1': 's2'}};
            this.observer_table.add_observer(new_observer);
            var self = this;
            this.wait(function() {
                    self._test_observer_rendered(new_observer);
                }, 60
            );
        },

        // When the delete link is clicked, the correct event is published.
        test_observer_delete_click: function() {
            this.observer_table = this._create_Widget();
            this.observer_table.render();
            var event_fired = false;
            var ns = Y.lp.registry.disclosure.observertable;
            this.observer_table.subscribe(
                ns.ObserverTableWidget.REMOVE_OBSERVER, function(e) {
                    var delete_link = e.details[0];
                    var observer_uri = e.details[1];
                    Y.Assert.areEqual('~fred', observer_uri);
                    Y.Assert.areEqual(delete_link_to_click, delete_link);
                    event_fired = true;
                }
            );
            var delete_link_to_click =
                Y.one('#observer-table td[id=remove-fred] a');
            delete_link_to_click.simulate('click');
            Y.Assert.isTrue(event_fired);
        },

        // The delete_observer call removes the observer from the table.
        test_observer_delete: function() {
            this.observer_table = this._create_Widget();
            this.observer_table.render();
            var row_selector = '#observer-table tr[id=permission-fred]';
            Y.Assert.isNotNull(Y.one(row_selector));
            this.observer_table.delete_observer(this.observer_data[0]);
            this.wait(function() {
                    Y.Assert.isNull(Y.one(row_selector));
                }, 60
            );
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.registry.disclosure.observertable',
        'lp.registry.disclosure.observerpicker']});
