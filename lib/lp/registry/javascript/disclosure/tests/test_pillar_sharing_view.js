/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.disclosure.sharing.test', function (Y) {

    var tests = Y.namespace('lp.registry.disclosure.sharing.test');
    tests.suite = new Y.Test.Suite(
        'lp.registry.disclosure.sharing Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.registry.disclosure.sharing_tests',

        setUp: function () {
            Y.one('#fixture').appendChild(
                Y.Node.create(Y.one('#test-fixture').getContent()));
            window.LP = {
                links: {},
                cache: {
                    context: {self_link: "~pillar" },
                    observer_data: [
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
                    access_policies: [
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
            var ns = Y.lp.registry.disclosure.sharing;
            return new ns.PillarSharingView(cfg);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.disclosure.sharing,
                "We should be able to locate the " +
                "lp.registry.disclosure.sharing module");
        },

        test_widget_can_be_instantiated: function() {
            this.view = this._create_Widget();
            Y.Assert.isInstanceOf(
                Y.lp.registry.disclosure.sharing.PillarSharingView,
                this.view,
                "Observer table failed to be instantiated");
        },

        // The view is correctly rendered.
        test_render: function() {
            this.view = this._create_Widget();
            this.view.render();
            // The observer table - we'll just check one row
            Y.Assert.isNotNull(
                Y.one('#observer-table tr[id=permission-fred]'));
            // The disclosure picker
            Y.Assert.isNotNull(Y.one('.yui3-disclosure_picker'));
        },

        // Clicking the sharing link opens the disclosure picker
        test_sharing_link_click: function() {
            this.view = this._create_Widget();
            this.view.render();
            Y.one('#add-observer-link').simulate('click');
            Y.Assert.isFalse(
                Y.one('.yui3-disclosure_picker')
                    .hasClass('yui3-disclosure_picker-hidden'));
        },

        // Clicking a delete observer link calls the performRemoveObserver
        // method with the correct parameters.
        test_delete_observer_click: function() {
            this.view = this._create_Widget();
            this.view.render();
            var performRemove_called = false;
            var self = this;
            this.view.performRemoveObserver = function(
                    delete_link, person_uri) {
                Y.Assert.areEqual('~fred', person_uri);
                Y.Assert.areEqual(delete_link_to_click, delete_link);
                performRemove_called = true;

            };
            var delete_link_to_click =
                Y.one('#observer-table td[id=remove-fred] a');
            delete_link_to_click.simulate('click');
            Y.Assert.isTrue(performRemove_called);
        },

        // The performRemoveObserver method makes the expected XHR calls.
        test_performRemoveObserver: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            this.view = this._create_Widget({
                lp_client: lp_client
            });
            this.view.render();
            var removeObserverSuccess_called = false;
            var self = this;
            this.view.removeObserverSuccess = function(person_uri) {
                Y.Assert.areEqual('~fred', person_uri);
                removeObserverSuccess_called = true;
            };
            var delete_link =
                Y.one('#observer-table td[id=remove-fred] a');
            this.view.performRemoveObserver(delete_link, '~fred');
            Y.Assert.areEqual(
                '/api/devel/+services/accesspolicy',
                mockio.last_request.url);
            Y.Assert.areEqual(
                'ws.op=deletePillarObserver&pillar=~pillar' +
                    '&observer=~fred',
                mockio.last_request.config.data);
            mockio.last_request.successJSON({});
            Y.Assert.isTrue(removeObserverSuccess_called);
        },

        // The removeObserver callback updates the model and table.
        test_removeObserverSuccess: function() {
            this.view = this._create_Widget({anim_duration: 0.001});
            this.view.render();
            var deleteObserver_called = false;
            var expected_observer = window.LP.cache.observer_data[0];
            var observer_table = this.view.get('observer_table');
            observer_table.deleteObserver = function(observer) {
                Y.Assert.areEqual(expected_observer, observer);
                deleteObserver_called = true;
            };
            this.view.removeObserverSuccess('~fred');
            Y.Assert.isTrue(deleteObserver_called);
            Y.Array.each(window.LP.cache.observer_data,
                function(observer) {
                    Y.Assert.areNotEqual('fred', observer.name);
            });
        },

        // The performAddObserver method makes the expected XHR calls.
        test_performAddObserver: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            this.view = this._create_Widget({
                lp_client: lp_client,
                anim_duration: 0
            });
            this.view.render();
            var saveSharingSelectionSuccess_called = false;
            var self = this;
            this.view.saveSharingSelectionSuccess = function(observer) {
                Y.Assert.areEqual('joe', observer.name);
                saveSharingSelectionSuccess_called = true;
            };
            // Use the picker to select a new observer and access policy.
            var disclosure_picker = this.view.get('disclosure_picker');
            var picker_results = [
                {"value": "joe", "title": "Joe", "css": "sprite-person",
                    "description": "joe@example.com", "api_uri": "~/joe",
                    "metadata": "person"}];
            Y.one('#add-observer-link').simulate('click');
            disclosure_picker.set('results', picker_results);
            disclosure_picker.get('boundingBox').one(
                '.yui3-picker-results li:nth-child(1)').simulate('click');
            var cb = disclosure_picker.get('contentBox');
            var step_two_content = cb.one('.picker-content-two');
            step_two_content.one('input[value="Policy 2"]').simulate('click');
            var select_link = step_two_content.one('a.next');
            select_link.simulate('click');
            // Selection made using the picker, now check the results.
            Y.Assert.areEqual(
                '/api/devel/+services/accesspolicy',
                mockio.last_request.url);
            var person_uri = Y.lp.client.normalize_uri('~/joe');
            person_uri = Y.lp.client.get_absolute_uri(person_uri);
            var expected_url;
            expected_url = Y.lp.client.append_qs(
                expected_url, 'ws.op', 'addPillarObserver');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'pillar', '~pillar');
            expected_url = Y.lp.client.append_qs(
                expected_url, 'observer', person_uri);
            expected_url = Y.lp.client.append_qs(
                expected_url, 'access_policy_type', 'Policy 2');
            Y.Assert.areEqual(expected_url, mockio.last_request.config.data);
            mockio.last_request.successJSON({
                'resource_type_link': 'entity',
                'name': 'joe',
                'self_link': '~joe'});
            Y.Assert.isTrue(saveSharingSelectionSuccess_called);
        },

        // The saveSharingSelectionSuccess callback updates the model and table.
        test_saveSharingSelectionSuccess: function() {
            this.view = this._create_Widget({anim_duration: 0.001});
            this.view.render();
            var addObserver_called = false;
            var new_observer = {
                'name': 'joe'
            };
            var observer_table = this.view.get('observer_table');
            observer_table.addObserver = function(observer) {
                Y.Assert.areEqual(new_observer, observer);
                addObserver_called = true;
            };
            this.view.saveSharingSelectionSuccess(new_observer);
            Y.Assert.isTrue(addObserver_called);
            var model_updated = false;
            Y.Array.some(window.LP.cache.observer_data,
                function(observer) {
                    model_updated = 'joe' === observer.name;
                    return model_updated;
            });
            Y.Assert.isTrue(model_updated);
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.registry.disclosure',
        'lp.registry.disclosure.sharing',
        'lp.registry.disclosure.observertable']});
