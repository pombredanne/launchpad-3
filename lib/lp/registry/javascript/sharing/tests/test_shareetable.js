/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.sharing.shareetable.test', function (Y) {

    var tests = Y.namespace('lp.registry.sharing.shareetable.test');
    tests.suite = new Y.Test.Suite(
        'lp.registry.sharing.shareetable Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.registry.sharing.shareetable_tests',

        setUp: function () {
            this.sharee_data = [
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
            this.information_types = {
                'P1': 'Policy 1',
                'P2': 'Policy 2',
                'P3': 'Policy 3'
            };
        },

        tearDown: function () {
            Y.one('#sharee-table').empty(true);
        },

        _create_Widget: function() {
            var ns = Y.lp.registry.sharing.shareetable;
            return new ns.ShareeTableWidget({
                anim_duration: 0.001,
                sharees: this.sharee_data,
                sharing_permissions: this.sharing_permissions,
                information_types: this.information_types
            });
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.sharing.shareetable,
                "We should be able to locate the " +
                "lp.registry.sharing.shareetable module");
        },

        test_widget_can_be_instantiated: function() {
            this.sharee_table = this._create_Widget();
            Y.Assert.isInstanceOf(
                Y.lp.registry.sharing.shareetable.ShareeTableWidget,
                this.sharee_table,
                "Sharee table failed to be instantiated");
        },

        // The given sharee is correctly rendered.
        _test_sharee_rendered: function(sharee) {
            // The sharee row
            Y.Assert.isNotNull(
                Y.one('#sharee-table tr[id=permission-'
                      + sharee.name + ']'));
            // The delete link
            Y.Assert.isNotNull(
                Y.one('#sharee-table td[id=remove-'
                      + sharee.name + '] a'));
            // The sharing permissions
            var permission;
            for (permission in sharee.permissions) {
                if (sharee.permissions.hasOwnProperty(permission)) {
                    Y.Assert.isNotNull(
                        Y.one('#sharee-table td[id=td-permission-'
                              + sharee.name + '] ul li '
                              + 'span[id='+permission+'-permission-'
                              + sharee.name + '] span.value'));
                }
            }
        },

        // The sharee table is correctly rendered.
        test_render: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var self = this;
            Y.Array.each(this.sharee_data, function(sharee) {
                self._test_sharee_rendered(sharee);
            });
        },

        // The add_sharee call adds the sharee to the table.
        test_sharee_add: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var new_sharee = {
                'name': 'joe', 'display_name': 'Joe Smith',
                'role': '(Maintainer)', web_link: '~joe',
                'self_link': '~joe',
                'permissions': {'P1': 's2'}};
            this.sharee_table.add_sharee(new_sharee);
            var self = this;
            this.wait(function() {
                    self._test_sharee_rendered(new_sharee);
                }, 60
            );
        },

        // When the delete link is clicked, the correct event is published.
        test_sharee_delete_click: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var event_fired = false;
            var ns = Y.lp.registry.sharing.shareetable;
            this.sharee_table.subscribe(
                ns.ShareeTableWidget.REMOVE_SHAREE, function(e) {
                    var delete_link = e.details[0];
                    var sharee_uri = e.details[1];
                    var person_name = e.details[2];
                    Y.Assert.areEqual('~fred', sharee_uri);
                    Y.Assert.areEqual('Fred Bloggs', person_name);
                    Y.Assert.areEqual(delete_link_to_click, delete_link);
                    event_fired = true;
                }
            );
            var delete_link_to_click =
                Y.one('#sharee-table td[id=remove-fred] a');
            delete_link_to_click.simulate('click');
            Y.Assert.isTrue(event_fired);
        },

        // When the update link is clicked, the correct event is published.
        test_sharee_update_click: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var event_fired = false;
            var ns = Y.lp.registry.sharing.shareetable;
            this.sharee_table.subscribe(
                ns.ShareeTableWidget.UPDATE_SHAREE, function(e) {
                    var delete_link = e.details[0];
                    var sharee_uri = e.details[1];
                    var person_name = e.details[2];
                    Y.Assert.areEqual('~fred', sharee_uri);
                    Y.Assert.areEqual('Fred Bloggs', person_name);
                    Y.Assert.areEqual(update_link_to_click, delete_link);
                    event_fired = true;
                }
            );
            var update_link_to_click =
                Y.one('#sharee-table td[id=update-fred] a');
            update_link_to_click.simulate('click');
            Y.Assert.isTrue(event_fired);
        },

        // The delete_sharee call removes the sharee from the table.
        test_sharee_delete: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var row_selector = '#sharee-table tr[id=permission-fred]';
            Y.Assert.isNotNull(Y.one(row_selector));
            this.sharee_table.delete_sharee(this.sharee_data[0]);
            this.wait(function() {
                    Y.Assert.isNull(Y.one(row_selector));
                }, 60
            );
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.registry.sharing.shareetable',
        'lp.registry.sharing.shareepicker']});
