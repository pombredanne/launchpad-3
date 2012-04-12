/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.sharing.shareetable.test', function (Y) {

    var tests = Y.namespace('lp.registry.sharing.shareetable.test');
    tests.suite = new Y.Test.Suite(
        'lp.registry.sharing.shareetable Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.registry.sharing.shareetable_tests',

        setUp: function () {
            window.LP = {
                links: {},
                cache: {
                    context: {self_link: "~pillar" },
                    sharee_data: [
                    {'name': 'fred', 'display_name': 'Fred Bloggs',
                     'role': '(Maintainer)', web_link: '~fred',
                     'self_link': '~fred',
                     'permissions': {'P1': 's1', 'P2': 's2'}},
                    {'name': 'john.smith', 'display_name': 'John Smith',
                     'role': '', web_link: '~smith', 'self_link': '~smith',
                     'shared_items_exist': true,
                    'permissions': {'P1': 's1', 'P3': 's3'}}
                    ]
                }
            };
            this.sharing_permissions = {
                s1: 'S1',
                s2: 'S2'
            };
            this.information_types = {
                P1: 'Policy 1',
                P2: 'Policy 2',
                P3: 'Policy 3'
            };
            this.fixture = Y.one('#fixture');
            var sharee_table = Y.Node.create(
                    Y.one('#sharee-table-template').getContent());
            this.fixture.appendChild(sharee_table);

        },

        tearDown: function () {
            if (this.fixture !== null) {
                this.fixture.empty(true);
            }
            delete this.fixture;
            delete window.LP;
        },

        _create_Widget: function(overrides) {
            if (!Y.Lang.isValue(overrides)) {
                overrides = {};
            }
            var config = Y.merge({
                sharee_table: Y.one('#sharee-table'),
                anim_duration: 0,
                sharees: window.LP.cache.sharee_data,
                sharing_permissions: this.sharing_permissions,
                information_types: this.information_types,
                write_enabled: true
            }, overrides);
            window.LP.cache.sharee_data = config.sharees;
            var ns = Y.lp.registry.sharing.shareetable;
            return new ns.ShareeTableWidget(config);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.sharing.shareetable,
                "Could not locate the " +
                "lp.registry.sharing.shareetable module");
        },

        test_widget_can_be_instantiated: function() {
            this.sharee_table = this._create_Widget();
            Y.Assert.isInstanceOf(
                Y.lp.registry.sharing.shareetable.ShareeTableWidget,
                this.sharee_table,
                "Sharee table failed to be instantiated");
        },

        // Read only mode disables the correct things.
        test_readonly: function() {
            this.sharee_table = this._create_Widget({
                write_enabled: false
            });
            this.sharee_table.render();
            Y.all('#sharee-table ' +
                  '.sprite.add, .sprite.edit, .sprite.remove a')
                .each(function(link) {
                    Y.Assert.isTrue(link.hasClass('unseen'));
            });
        },

        // When there are no sharees, the table contains an informative message.
        test_no_sharee_message: function() {
            this.sharee_table = this._create_Widget({
                sharees: []
            });
            this.sharee_table.render();
            Y.Assert.areEqual(
                "This project's private information is not shared " +
                "with anyone.",
                Y.one('#sharee-table tr td').getContent());
        },

        // When the first sharee is added, the "No sharees" row is removed.
        test_first_sharee_added: function() {
            this.sharee_table = this._create_Widget({
                sharees: []
            });
            this.sharee_table.render();
            Y.Assert.isNotNull(Y.one('tr#sharee-table-not-shared'));
            var new_sharee = {
                'name': 'joe', 'display_name': 'Joe Smith',
                'role': '(Maintainer)', web_link: '~joe',
                'self_link': '~joe',
                'permissions': {'P1': 's2'}};
            this.sharee_table.update_sharees([new_sharee]);
            Y.Assert.isNull(Y.one('tr#sharee-table-not-shared'));
        },

        // The given sharee is correctly rendered.
        _test_sharee_rendered: function(sharee) {
            // The sharee row
            var sharee_row = Y.one('#sharee-table tr[id=permission-'
                + sharee.name + ']');
            Y.Assert.isNotNull(sharee_row);
            // The update link
            Y.Assert.isNotNull(
                Y.one('#sharee-table span[id=update-'
                      + sharee.name + '] a'));
            // The delete link
            Y.Assert.isNotNull(
                Y.one('#sharee-table span[id=remove-'
                      + sharee.name + '] a'));
            // The sharing permissions
            var self = this;
            Y.each(sharee.permissions, function(permission, info_type) {
                var permission_node =
                    Y.one('#sharee-table td[id=td-permission-'
                          + sharee.name + '] ul li '
                          + 'span[id=' + info_type + '-permission-'
                          + sharee.name + '] span.value');
                Y.Assert.isNotNull(permission_node);
                var expected_content =
                    self.information_types[info_type] + ': ' +
                    self.sharing_permissions[permission];
                Y.Assert.areEqual(
                    expected_content, permission_node.get('text'));
            });
            // The shared items link.
            var shared_items_cell = sharee_row.one('td+td+td+td+td');
            if (sharee.shared_items_exist) {
                Y.Assert.isNotNull(
                    shared_items_cell.one(
                        'a[href=+sharing/' + sharee.name + ']'));
            } else {
                Y.Assert.areEqual(
                    'No items shared through subscriptions.',
                    Y.Lang.trim(shared_items_cell.get('text')));
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

        // When the update link is clicked, the correct event is published.
        test_sharee_update_click: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var event_fired = false;
            var ns = Y.lp.registry.sharing.shareetable;
            this.sharee_table.subscribe(
                ns.ShareeTableWidget.UPDATE_SHAREE, function(e) {
                    var update_link = e.details[0];
                    var sharee_uri = e.details[1];
                    var person_name = e.details[2];
                    Y.Assert.areEqual('~fred', sharee_uri);
                    Y.Assert.areEqual('Fred Bloggs', person_name);
                    Y.Assert.areEqual(update_link_to_click, update_link);
                    event_fired = true;
                }
            );
            var update_link_to_click =
                Y.one('#sharee-table span[id=update-fred] a');
            update_link_to_click.simulate('click');
            Y.Assert.isTrue(event_fired);
        },

        // The update_sharees call adds new sharees to the table.
        test_sharee_add: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var new_sharee = {
                'name': 'joe', 'display_name': 'Joe Smith',
                'role': '(Maintainer)', web_link: '~joe',
                'self_link': '~joe',
                'permissions': {'P1': 's2'}};
            this.sharee_table.update_sharees([new_sharee]);
            this._test_sharee_rendered(new_sharee);
        },

        // The update_sharees call updates existing sharees in the table.
        test_sharee_update: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var updated_sharee = {
                'name': 'fred', 'display_name': 'Fred Bloggs',
                'role': '(Maintainer)', web_link: '~fred',
                'self_link': '~fred',
                'permissions': {'P1': 's2', 'P2': 's1'}};
            this.sharee_table.update_sharees([updated_sharee]);
            this._test_sharee_rendered(updated_sharee);
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
                Y.one('#sharee-table span[id=remove-fred] a');
            delete_link_to_click.simulate('click');
            Y.Assert.isTrue(event_fired);
        },

        // The delete_sharees call removes the sharees from the table.
        test_sharee_delete: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var row_selector = '#sharee-table tr[id=permission-fred]';
            Y.Assert.isNotNull(Y.one(row_selector));
            this.sharee_table.delete_sharees(
                [window.LP.cache.sharee_data[0]]);
            Y.Assert.isNull(Y.one(row_selector));
        },

        // When the permission popup is clicked, the correct event is published.
        test_permission_update_click: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var event_fired = false;
            var ns = Y.lp.registry.sharing.shareetable;
            this.sharee_table.subscribe(
                ns.ShareeTableWidget.UPDATE_PERMISSION, function(e) {
                    var sharee_uri = e.details[0];
                    var policy = e.details[1];
                    var permission = e.details[2];
                    Y.Assert.areEqual('~fred', sharee_uri);
                    Y.Assert.areEqual('P1', policy);
                    Y.Assert.areEqual(permission, 's2');
                    event_fired = true;
                }
            );
            var permission_popup =
                Y.one('#sharee-table span[id=P1-permission-fred] a');
            permission_popup.simulate('click');
            var permission_choice = Y.one(
                '.yui3-ichoicelist-content a[href=#s2]');
            permission_choice.simulate('click');
            Y.Assert.isTrue(event_fired);
        },

        // Model changes are rendered correctly when syncUI() is called.
        test_syncUI: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            // We manipulate the cached model data - delete, add and update
            var sharee_data = window.LP.cache.sharee_data;
            // Delete the first record.
            sharee_data.splice(0, 1);
            // Insert a new record.
            var new_sharee = {
                'name': 'joe', 'display_name': 'Joe Smith',
                'role': '(Maintainer)', web_link: '~joe',
                'self_link': '~joe',
                'permissions': {'P1': 's2'}};
            sharee_data.splice(0, 0, new_sharee);
            // Update a record.
            sharee_data[1].permissions = {'P1': 's2', 'P2': 's1'};
            this.sharee_table.syncUI();
            // Check the results.
            var self = this;
            Y.Array.each(sharee_data, function(sharee) {
                self._test_sharee_rendered(sharee);
            });
            var deleted_row = '#sharee-table tr[id=permission-fred]';
            Y.Assert.isNull(Y.one(deleted_row));
        },

        // The navigator model total attribute is updated when the currently
        // displayed sharee data changes.
        test_navigation_totals_updated: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            // We manipulate the cached model data - delete, add and update
            var sharee_data = window.LP.cache.sharee_data;
            // Insert a new record.
            var new_sharee = {
                'name': 'joe', 'display_name': 'Joe Smith',
                'role': '(Maintainer)', web_link: '~joe',
                'self_link': '~joe',
                'permissions': {'P1': 's2'}};
            sharee_data.splice(0, 0, new_sharee);
            this.sharee_table.syncUI();
            // Check the results.
            Y.Assert.areEqual(
                3, this.sharee_table.navigator.get('model').get('total'));
        },

        // When all rows are deleted, the table contains an informative message.
        test_delete_all: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            // We manipulate the cached model data.
            var sharee_data = window.LP.cache.sharee_data;
            // Delete all the records.
            sharee_data.splice(0, 2);
            this.sharee_table.syncUI();
            // Check the results.
            Y.Assert.areEqual(
                "This project's private information is not shared " +
                "with anyone.",
                Y.one('#sharee-table tr#sharee-table-not-shared td')
                    .getContent());
        },

        // A batch update is correctly rendered.
        test_navigator_content_update: function() {
            this.sharee_table = this._create_Widget();
            this.sharee_table.render();
            var new_sharee = {
                'name': 'joe', 'display_name': 'Joe Smith',
                'role': '(Maintainer)', web_link: '~joe',
                'self_link': '~joe',
                'permissions': {'P1': 's2'}};
            this.sharee_table.navigator.fire('updateContent', [new_sharee]);
            this._test_sharee_rendered(new_sharee);
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.registry.sharing.shareetable',
        'lp.registry.sharing.shareepicker']});
