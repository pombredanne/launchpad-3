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
                    context: {
                        self_link: "~pillar", display_name: 'Pillar'},
                    sharee_data: [
                    {'name': 'fred', 'display_name': 'Fred Bloggs',
                     'role': '(Maintainer)', web_link: '~fred',
                     'self_link': '~fred',
                     'permissions': {'P1': 'ALL', 'P2': 'SOME'},
                     'shared_artifact_types': []},
                    {'name': 'john', 'display_name': 'John Smith',
                     'role': '', web_link: '~john',
                     'self_link': 'file:///api/devel/~john',
                     'permissions': {'P1': 'ALL', 'P3': 'SOME'},
                     'shared_artifact_types': ['P3']}
                    ],
                    sharing_permissions: [
                        {'value': 'ALL', 'title': 'All',
                         'description': 'Everything'},
                        {'value': 'NOTHING', 'title': 'Nothing',
                         'description': 'Nothing'},
                        {'value': 'SOME', 'title': 'Some',
                         'description': 'Some'}
                    ],
                    information_types: [
                        {index: '0', value: 'P1', title: 'Policy 1',
                         description: 'Policy 1 description'},
                        {index: '1', value: 'P2', title: 'Policy 2',
                         description: 'Policy 2 description'},
                        {index: '2', value: 'P3', title: 'Policy 3',
                         description: 'Policy 3 description'}
                    ],
                    sharing_write_enabled: true
                }
            };
        },

        tearDown: function () {
            Y.one('#fixture').empty(true);
            delete window.LP;
        },

        _create_Widget: function(cfg) {
            var config = Y.merge(cfg, {
                header: "Grant access",
                steptitle: "Select user",
                vocabulary: "SharingVocab"
            });
            var ns = Y.lp.registry.sharing.pillarsharingview;
            return new ns.PillarSharingView(config);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.sharing.pillarsharingview,
                "Could not locate the " +
                "lp.registry.sharing.pillarsharingview module");
        },

        test_widget_can_be_instantiated: function() {
            this.view = this._create_Widget();
            Y.Assert.isInstanceOf(
                Y.lp.registry.sharing.pillarsharingview.PillarSharingView,
                this.view,
                "Sharee table failed to be instantiated");
            // Check the picker config.
            var sharee_picker = this.view.get('sharee_picker');
            Y.Assert.areEqual(
                sharee_picker.get('headerContent')
                    .get('text'), 'Grant access');
            Y.Assert.areEqual(sharee_picker.get('steptitle'), 'Select user');
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

        // Read only mode disables the correct things.
        test_readonly: function() {
            window.LP.cache.sharing_write_enabled = false;
            this.view = this._create_Widget();
            this.view.render();
            Y.Assert.isTrue(Y.one('#add-sharee-link').hasClass('hidden'));
            Y.Assert.isFalse(
                this.view.get('sharee_table').get('write_enabled'));
        },

        // Clicking a update sharee sharee link calls
        // the update_sharee_interaction method with the correct parameters.
        test_update_sharee_click: function() {
            this.view = this._create_Widget();
            this.view.render();
            var update_sharee_called = false;
            this.view.update_sharee_interaction = function(
                    update_link, person_uri, person_name) {
                Y.Assert.areEqual('~fred', person_uri);
                Y.Assert.areEqual('Fred Bloggs', person_name);
                Y.Assert.areEqual(update_link_to_click, update_link);
                update_sharee_called = true;

            };
            var update_link_to_click =
                Y.one('#sharee-table span[id=update-fred] a');
            update_link_to_click.simulate('click');
            Y.Assert.isTrue(update_sharee_called);
        },

        // The update_sharee_interaction method shows the correctly
        // configured sharing picker.
        test_update_sharee_interaction: function() {
            this.view = this._create_Widget();
            this.view.render();
            var show_picker_called = false;
            var sharee_picker = this.view.get('sharee_picker');
            sharee_picker.show = function(config) {
                Y.Assert.areEqual(2, config.first_step);
                Y.Assert.areEqual('~john', config.sharee.person_uri);
                Y.Assert.areEqual('John', config.sharee.person_name);
                Y.Assert.areEqual(2, Y.Object.size(config.sharee_permissions));
                Y.Assert.areEqual('ALL', config.sharee_permissions.P1);
                Y.Assert.areEqual('SOME', config.sharee_permissions.P3);
                Y.ArrayAssert.itemsAreEqual(
                    ['ALL', 'NOTHING', 'SOME'],
                    config.allowed_permissions);
                Y.ArrayAssert.itemsAreEqual(
                    ['P1', 'P2'], config.disabled_some_types);
                show_picker_called = true;
            };
            var update_link =
                Y.one('#sharee-table span[id=update-smith] a');
            this.view.update_sharee_interaction(update_link, '~john', 'John');
            Y.Assert.isTrue(show_picker_called);
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
                Y.one('#sharee-table span[id=remove-fred] a');
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
                Y.one('#sharee-table span[id=remove-fred] a');
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

        // The removeSharee callback updates the model and syncs the UI.
        test_remove_sharee_success: function() {
            this.view = this._create_Widget({anim_duration: 0.001});
            this.view.render();
            var syncUI_called = false;
            this.view.syncUI = function() {
                syncUI_called = true;
            };
            this.view.remove_sharee_success('~fred');
            Y.Assert.isTrue(syncUI_called);
            Y.Array.each(window.LP.cache.sharee_data,
                function(sharee) {
                    Y.Assert.areNotEqual('fred', sharee.name);
            });
        },

        // XHR calls display errors correctly.
        _assert_error_displayed_on_failure: function(invoke_operation) {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            this.view = this._create_Widget({
                lp_client: lp_client
            });
            this.view.render();
            var display_error_called = false;
            var sharee_table = this.view.get('sharee_table');
            sharee_table.display_error = function(sharee_name, error_msg) {
                Y.Assert.areEqual('fred', sharee_name);
                Y.Assert.areEqual(
                    'Server error, please contact an administrator.',
                    error_msg);
                display_error_called = true;
            };
            invoke_operation(this.view);
            mockio.last_request.respond({
                status: 500,
                statusText: 'An error occurred'
            });
            Y.Assert.isTrue(display_error_called);
        },

        // The perform_remove_sharee method handles errors correctly.
        test_perform_remove_sharee_error: function() {
            var invoke_remove = function(view) {
                var delete_link =
                    Y.one('#sharee-table span[id=remove-fred] a');
                view.perform_remove_sharee(delete_link, '~fred');
            };
            this._assert_error_displayed_on_failure(invoke_remove);
        },

        // When a sharee is added, the expected XHR calls are made.
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
            // All sharing permissions should initially be set to nothing.
            step_two_content.all('input[name^=field.permission]')
                    .each(function(radio_button) {
                if (radio_button.get('checked')) {
                    Y.Assert.areEqual('NOTHING', radio_button.get('value'));
                }
            });
            step_two_content
                .one('input[name=field.permission.P2][value="ALL"]')
                .simulate('click');
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
                expected_url, 'permissions', 'Policy 1,Nothing');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'permissions', 'Policy 2,All');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'permissions', 'Policy 3,Nothing');
            Y.Assert.areEqual(expected_url, mockio.last_request.config.data);
            mockio.last_request.successJSON({
                'name': 'joe',
                'self_link': '~joe'});
            Y.Assert.isTrue(save_sharing_selection_success_called);
        },

        // When a permission is updated, the expected XHR calls are made.
        test_perform_update_permission: function() {
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
            this.view.save_sharing_selection_success = function(sharee) {
                Y.Assert.areEqual('fred', sharee.name);
                save_sharing_selection_success_called = true;
            };
            // Use permission popup to select a new value.
             var permission_popup =
                Y.one('#sharee-table span[id=P1-permission-fred] a');
            permission_popup.simulate('click');
            var permission_choice = Y.one(
                '.yui3-ichoicelist-content a[href=#SOME]');
            permission_choice.simulate('click');

            // Selection made, now check the results.
            Y.Assert.areEqual(
                '/api/devel/+services/sharing',
                mockio.last_request.url);
            var person_uri = Y.lp.client.normalize_uri('~fred');
            person_uri = Y.lp.client.get_absolute_uri(person_uri);
            var expected_url;
            expected_url = Y.lp.client.append_qs(
                expected_url, 'ws.op', 'sharePillarInformation');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'pillar', '~pillar');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'sharee', person_uri);
            expected_url = Y.lp.client.append_qs(
                expected_url, 'permissions', 'Policy 1,Some');
            Y.Assert.areEqual(expected_url, mockio.last_request.config.data);
            mockio.last_request.successJSON({
                'name': 'fred',
                'self_link': '~fred'});
            Y.Assert.isTrue(save_sharing_selection_success_called);
        },

        // The save_sharing_selection_success callback updates the model and
        // syncs the UI.
        test_save_sharing_selection_success: function() {
            this.view = this._create_Widget({anim_duration: 0.001});
            this.view.render();
            var new_sharee = {
                'name': 'joe'
            };
            var syncUI_called = false;
            this.view.syncUI = function() {
                syncUI_called = true;
            };
            this.view.save_sharing_selection_success(new_sharee);
            Y.Assert.isTrue(syncUI_called);
            var model_updated = false;
            Y.Array.some(window.LP.cache.sharee_data,
                function(sharee) {
                    model_updated = 'joe' === sharee.name;
                    return model_updated;
            });
            Y.Assert.isTrue(model_updated);
        },

        // The save_sharing_selection method handles errors correctly.
        test_save_sharing_selection_error: function() {
            var invoke_save = function(view) {
                view.save_sharing_selection("~fred", ["P1,All"]);
            };
            this._assert_error_displayed_on_failure(invoke_save);
        },

        // If the XHR result of a sharePillarInformation call is null, the user
        // is to be deleted.
        test_save_sharing_selection_null_result: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            this.view = this._create_Widget({
                lp_client: lp_client,
                anim_duration: 0
            });
            this.view.render();
            var remove_sharee_success_called = false;
            this.view.remove_sharee_success = function(sharee_uri) {
                Y.Assert.areEqual('file:///api/devel/~fred', sharee_uri);
                remove_sharee_success_called = true;
            };
            this.view.save_sharing_selection("~fred", ["P1,All"]);
            mockio.last_request.successJSON(null);
            Y.Assert.isTrue(remove_sharee_success_called);
        },

        // Test that syncUI works as expected.
        test_syncUI: function() {
            this.view = this._create_Widget();
            this.view.render();
            var sharee_table = this.view.get('sharee_table');
            var table_syncUI_called = false;
            sharee_table.syncUI = function() {
                table_syncUI_called = true;
            };
            this.view.syncUI();
            Y.Assert.isTrue(table_syncUI_called);
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.registry.sharing.shareepicker',
        'lp.registry.sharing.shareetable',
        'lp.registry.sharing.pillarsharingview']});
