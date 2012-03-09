/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.sharing.pillarsharingview.test', function (Y) {

    var tests = Y.namespace('lp.registry.sharing.pillarsharingview.test');
    tests.suite = new Y.Test.Suite(
        'lp.registry.sharing.sharing Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.registry.sharing.sharing_tests',

        setUp: function () {
            Y.one('#fixture').appendChild(
                Y.Node.create(Y.one('#test-fixture').getContent()));
            window.LP = {
                links: {},
                cache: {
                    context: {self_link: "~pillar" },
                    sharee_data: [
                    {'name': 'fred', 'display_name': 'Fred Bloggs',
                     'role': '(Maintainer)', web_link: '~fred',
                     'self_link': '~fred',
                     'permissions': {'P1': 's1', 'P2': 's2'}},
                    {'name': 'john', 'display_name': 'John Smith',
                     'role': '', web_link: '~smith', 'self_link': '~smith',
                    'permissions': {'P1': 's1', 'P3': 's3'}}
                    ],
                    sharing_permissions: [
                        {'value': 's1', 'title': 'S1',
                         'description': 'Sharing 1'},
                        {'value': 's2', 'title': 'S2',
                         'description': 'Sharing 2'}
                    ],
                    information_types: [
                        {index: '0', value: 'P1', title: 'Policy 1',
                         description: 'Policy 1 description'},
                        {index: '1', value: 'P2', title: 'Policy 2',
                         description: 'Policy 2 description'},
                        {index: '2', value: 'P3', title: 'Policy 3',
                         description: 'Policy 3 description'}
                    ]
                }
            };
        },

        tearDown: function () {
            Y.one('#fixture').empty(true);
            delete window.LP;
        },

        _create_Widget: function(cfg) {
            var ns = Y.lp.registry.sharing.pillarsharingview;
            return new ns.PillarSharingView(cfg);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.sharing.pillarsharingview,
                "We should be able to locate the " +
                "lp.registry.sharing.pillarsharingview module");
        },

        test_widget_can_be_instantiated: function() {
            this.view = this._create_Widget();
            Y.Assert.isInstanceOf(
                Y.lp.registry.sharing.pillarsharingview.PillarSharingView,
                this.view,
                "Sharee table failed to be instantiated");
        },

        // The view is correctly rendered.
        test_render: function() {
            this.view = this._create_Widget();
            this.view.render();
            // The sharee table - we'll just check one row
            Y.Assert.isNotNull(
                Y.one('#sharee-table tr[id=permission-fred]'));
            // The sharing picker
            Y.Assert.isNotNull(Y.one('.yui3-sharee_picker'));
        },

        // Clicking the sharing link opens the sharing picker
        test_sharing_link_click: function() {
            this.view = this._create_Widget();
            this.view.render();
            Y.one('#add-sharee-link').simulate('click');
            Y.Assert.isFalse(
                Y.one('.yui3-sharee_picker')
                    .hasClass('yui3-sharee_picker-hidden'));
        },

        // Clicking a delete sharee link calls the confirm_sharee_removal
        // method with the correct parameters.
        test_delete_sharee_click: function() {
            this.view = this._create_Widget();
            this.view.render();
            var confirmRemove_called = false;
            this.view.confirm_sharee_removal = function(
                    delete_link, person_uri, person_name) {
                Y.Assert.areEqual('~fred', person_uri);
                Y.Assert.areEqual('Fred Bloggs', person_name);
                Y.Assert.areEqual(delete_link_to_click, delete_link);
                confirmRemove_called = true;

            };
            var delete_link_to_click =
                Y.one('#sharee-table td[id=remove-fred] a');
            delete_link_to_click.simulate('click');
            Y.Assert.isTrue(confirmRemove_called);
        },

        //Test the behaviour of the removal confirmation dialog.
        _test_confirm_sharee_removal: function(click_ok) {
            this.view = this._create_Widget();
            this.view.render();
            var performRemove_called = false;
            this.view.perform_remove_sharee = function(
                    delete_link, person_uri) {
                Y.Assert.areEqual('~fred', person_uri);
                Y.Assert.areEqual(delete_link, delete_link);
                performRemove_called = true;

            };
            var delete_link =
                Y.one('#sharee-table td[id=remove-fred] a');
            this.view.confirm_sharee_removal(
                delete_link, '~fred', 'Fred Bloggs');
            var co = Y.one('.yui3-overlay.yui3-lp-app-confirmationoverlay');
            var actions = co.one('.yui3-lazr-formoverlay-actions');
            var btn_style;
            if (click_ok) {
                btn_style = '.ok-btn';
            } else {
                btn_style = '.cancel-btn';
            }
            var button = actions.one(btn_style);
            button.simulate('click');
            Y.Assert.areEqual(click_ok, performRemove_called);
            Y.Assert.isTrue(
                    co.hasClass('yui3-lp-app-confirmationoverlay-hidden'));
        },

        //Test the remove confirmation dialog when the user clicks Ok.
        test_confirm_sharee_removal_ok: function() {
            this._test_confirm_sharee_removal(true);
        },

        //Test the remove confirmation dialog when the user clicks Cancel.
        test_confirm_sharee_removal_cancel: function() {
            this._test_confirm_sharee_removal(false);
        },

        // The perform_remove_sharee method makes the expected XHR calls.
        test_perform_remove_sharee: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            this.view = this._create_Widget({
                lp_client: lp_client
            });
            this.view.render();
            var remove_sharee_success_called = false;
            var self = this;
            this.view.remove_sharee_success = function(person_uri) {
                Y.Assert.areEqual('~fred', person_uri);
                remove_sharee_success_called = true;
            };
            var delete_link =
                Y.one('#sharee-table td[id=remove-fred] a');
            this.view.perform_remove_sharee(delete_link, '~fred');
            Y.Assert.areEqual(
                '/api/devel/+services/sharing',
                mockio.last_request.url);
            Y.Assert.areEqual(
                'ws.op=deletePillarSharee&pillar=~pillar' +
                    '&sharee=~fred',
                mockio.last_request.config.data);
            mockio.last_request.successJSON({});
            Y.Assert.isTrue(remove_sharee_success_called);
        },

        // The removeSharee callback updates the model and table.
        test_remove_sharee_success: function() {
            this.view = this._create_Widget({anim_duration: 0.001});
            this.view.render();
            var delete_sharee_called = false;
            var expected_sharee = window.LP.cache.sharee_data[0];
            var sharee_table = this.view.get('sharee_table');
            sharee_table.delete_sharee = function(sharee) {
                Y.Assert.areEqual(expected_sharee, sharee);
                delete_sharee_called = true;
            };
            this.view.remove_sharee_success('~fred');
            Y.Assert.isTrue(delete_sharee_called);
            Y.Array.each(window.LP.cache.sharee_data,
                function(sharee) {
                    Y.Assert.areNotEqual('fred', sharee.name);
            });
        },

        // The perform_add_sharee method makes the expected XHR calls.
        test_perform_add_sharee: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            this.view = this._create_Widget({
                lp_client: lp_client,
                anim_duration: 0
            });
            this.view.render();
            var save_sharing_selection_success_called = false;
            var self = this;
            this.view.save_sharing_selection_success = function(sharee) {
                Y.Assert.areEqual('joe', sharee.name);
                save_sharing_selection_success_called = true;
            };
            // Use the picker to select a new sharee and information type.
            var sharee_picker = this.view.get('sharee_picker');
            var picker_results = [
                {"value": "joe", "title": "Joe", "css": "sprite-person",
                    "description": "joe@example.com", "api_uri": "~/joe",
                    "metadata": "person"}];
            Y.one('#add-sharee-link').simulate('click');
            sharee_picker.set('results', picker_results);
            sharee_picker.get('boundingBox').one(
                '.yui3-picker-results li:nth-child(1)').simulate('click');
            var cb = sharee_picker.get('contentBox');
            var step_two_content = cb.one('.picker-content-two');
            step_two_content.one('input[value="Policy 2"]').simulate('click');
            var select_link = step_two_content.one('a.next');
            select_link.simulate('click');
            // Selection made using the picker, now check the results.
            Y.Assert.areEqual(
                '/api/devel/+services/sharing',
                mockio.last_request.url);
            var person_uri = Y.lp.client.normalize_uri('~/joe');
            person_uri = Y.lp.client.get_absolute_uri(person_uri);
            var expected_url;
            expected_url = Y.lp.client.append_qs(
                expected_url, 'ws.op', 'sharePillarInformation');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'pillar', '~pillar');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'sharee', person_uri);
            expected_url = Y.lp.client.append_qs(
                expected_url, 'information_types', ['Policy 2']);
            Y.Assert.areEqual(expected_url, mockio.last_request.config.data);
            mockio.last_request.successJSON({
                'resource_type_link': 'entity',
                'name': 'joe',
                'self_link': '~joe'});
            Y.Assert.isTrue(save_sharing_selection_success_called);
        },

        // The save_sharing_selection_success callback updates the model and
        // table.
        test_save_sharing_selection_success: function() {
            this.view = this._create_Widget({anim_duration: 0.001});
            this.view.render();
            var add_sharee_called = false;
            var new_sharee = {
                'name': 'joe'
            };
            var sharee_table = this.view.get('sharee_table');
            sharee_table.add_sharee = function(sharee) {
                Y.Assert.areEqual(new_sharee, sharee);
                add_sharee_called = true;
            };
            this.view.save_sharing_selection_success(new_sharee);
            Y.Assert.isTrue(add_sharee_called);
            var model_updated = false;
            Y.Array.some(window.LP.cache.sharee_data,
                function(sharee) {
                    model_updated = 'joe' === sharee.name;
                    return model_updated;
            });
            Y.Assert.isTrue(model_updated);
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.registry.sharing.shareepicker',
        'lp.registry.sharing.shareetable',
        'lp.registry.sharing.pillarsharingview']});
