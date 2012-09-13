/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.app.information_type.test', function (Y) {

    var tests = Y.namespace('lp.app.information_type.test');
    var ns = Y.lp.app.information_type;
    tests.suite = new Y.Test.Suite('lp.app.information_type Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.app.information_type_tests',

        setUp: function() {
            window.LP = {
                cache: {
                    context: {
                        web_link: ''
                    },
                    notifications_text: {
                        muted: ''
                    },
                    bug: {
                        information_type: 'Public',
                        self_link: '/bug/1'
                    },
                    private_types: ['PROPRIETARY', 'USERDATA'],
                    information_type_data: [
                        {'value': 'PUBLIC', 'name': 'Public',
                            'description': 'Public Description'},
                        {'value': 'PUBLICSECURITY', 'name': 'Public Security',
                            'description': 'Public Security Description'},
                        {'value': 'PROPRIETARY', 'name': 'Proprietary',
                            'description': 'Private Description'},
                        {'value': 'USERDATA', 'name': 'Private',
                            'description': 'Private Description'}
                    ]
                }
            };
            this.fixture = Y.one('#fixture');
            var portlet = Y.Node.create(
                    Y.one('#portlet-template').getContent());
            this.fixture.appendChild(portlet);
            this.mockio = new Y.lp.testing.mockio.MockIo();
            this.lp_client = new Y.lp.client.Launchpad({
                io_provider: this.mockio
            });

            Y.lp.bugs.subscribers.createBugSubscribersLoader({
                container_box: '#other-bug-subscribers',
                subscribers_details_view:
                    '/+bug-portlet-subscribers-details'});

        },

        tearDown: function () {
            if (this.fixture !== null) {
                this.fixture.empty(true);
            }
            delete this.fixture;
            delete this.mockio;
            delete this.lp_client;
            delete window.LP;
        },

        makeWidget: function() {
            var privacy_link = Y.one('#privacy-link');
            this.widget = ns.setup_information_type_choice(
                privacy_link, this.lp_client, LP.cache.bug, null, true);
        },

        _shim_privacy_banner: function () {
            var old_func = Y.lp.app.banner.privacy.getPrivacyBanner;
            Y.lp.app.banner.privacy.getPrivacyBanner = function () {
                return {
                    show: function () { Y.fire('test:banner:show'); },
                    hide: function () { Y.fire('test:banner:hide'); },
                    updateText: function () { Y.fire('test:banner:update'); }
                };
            };
            return old_func;
        },

        _unshim_privacy_banner: function (old_func) {
            Y.lp.app.banner.privacy.getPrivacyBanner = old_func;
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.app.information_type,
                "Cannot locate the lp.app.information_type module");
        },

        // The save XHR call works as expected.
        test_save_information_type: function() {
            this.makeWidget();
            var orig_save_success = ns.information_type_save_success;
            var save_success_called = false;
            ns.information_type_save_success = function(widget, context, value,
                                                   subscribers_list,
                                                   subscribers_data) {
                Y.Assert.areEqual('USERDATA', value);
                Y.Assert.areEqual(
                    'subscribers', subscribers_data.subscription_data);
                Y.Assert.areEqual(
                    'value', subscribers_data.cache_data.item);
                save_success_called = true;
            };
            ns.save_information_type(
                    this.widget, 'PUBLIC', 'USERDATA', this.lp_client,
                    LP.cache.bug, null, true);
            this.mockio.success({
                responseText: '{"subscription_data": "subscribers",' +
                    '"cache_data": {"item": "value"}}',
                responseHeaders: {'Content-Type': 'application/json'}});
            Y.Assert.areEqual(
                document.URL + '/+secrecy', this.mockio.last_request.url);
            Y.Assert.areEqual(
                'field.actions.change=Change&' +
                'field.information_type=USERDATA&' +
                'field.validate_change=on',
                this.mockio.last_request.config.data);
            Y.Assert.isTrue(save_success_called);
            ns.information_type_save_success = orig_save_success;
        },

        // Setting a private type shows the privacy banner.
        test_information_type_save_success_private: function() {
            this.makeWidget();
            var old_func = this._shim_privacy_banner();
            var hide_flag = false;
            var update_flag = false;
            Y.on('test:banner:show', function() {
                hide_flag = true;
            });
            Y.on('test:banner:update', function() {
                update_flag = true;
            });

            ns.information_type_save_success(this.widget, LP.cache.bug,
                                             'PROPRIETARY');
            var body = Y.one('body');
            Y.Assert.isTrue(body.hasClass('private'));
            Y.Assert.isTrue(hide_flag);
            Y.Assert.isTrue(update_flag);
            Y.Assert.areEqual(
                'Proprietary', LP.cache.bug.information_type);
            this._unshim_privacy_banner(old_func);
        },

        // Setting a private type hides the privacy banner.
        test_information_type_save_success_public: function() {
            this.makeWidget();
            var old_func = this._shim_privacy_banner();
            var flag = false;
            Y.on('test:banner:hide', function() {
                flag = true;
            });
            var summary = Y.one('#information-type-summary');
            summary.replaceClass('public', 'private');

            ns.information_type_save_success(this.widget, 'PUBLIC');
            var body = Y.one('body');
            Y.Assert.isTrue(body.hasClass('public'));
            Y.Assert.isTrue(flag);
            Y.Assert.areEqual('Public', LP.cache.bug.information_type);
            this._unshim_privacy_banner(old_func);
        },

        // A successful save updates the subscribers portlet.
        test_information_type_save_success_with_subscribers_data: function() {
            this.makeWidget();
            var old_func = this._shim_privacy_banner();
            var flag = false;
            Y.on('test:banner:hide', function() {
                flag = true;
            });
            var summary = Y.one('#information-type-summary');
            summary.replaceClass('public', 'private');

            var load_subscribers_called = false;
            var subscribers_list = {
                _loadSubscribersFromList: function(subscription_data) {
                    Y.Assert.areEqual('subscriber', subscription_data);
                    load_subscribers_called = true;
                }
            };
            var subscribers_data = {
                subscription_data: 'subscriber',
                cache_data: {
                    item1: 'value1',
                    item2: 'value2'
                }
            };
            ns.information_type_save_success(
                this.widget, LP.cache.bug, 'PUBLIC', subscribers_list,
                subscribers_data);
            Y.Assert.isTrue(load_subscribers_called);
            Y.Assert.areEqual('value1', window.LP.cache.item1);
            Y.Assert.areEqual('value2', window.LP.cache.item2);
            this._unshim_privacy_banner(old_func);
        },

        // Select a new information type and respond with a validation error.
        _assert_save_with_validation_error: function() {
            this.makeWidget();
            var privacy_link = Y.one('#privacy-link');
            privacy_link.simulate('click');
            var private_choice = Y.one(
                '.yui3-ichoicelist-content a[href="#USERDATA"]');
            private_choice.simulate('click');
            // Check the save and respond with a status of 400.
            Y.Assert.areEqual(
                document.URL + '/+secrecy', this.mockio.last_request.url);
            Y.Assert.areEqual(
                'field.actions.change=Change&' +
                'field.information_type=USERDATA&' +
                'field.validate_change=on',
                this.mockio.last_request.config.data);
            this.mockio.respond({
                status: 400,
                statusText: 'Bug Visibility'});
        },

        // Selecting a new private information type shows the
        // confirmation dialog and calls save correctly when user says 'yes'.
        test_perform_update_information_type_to_private: function() {
            this._assert_save_with_validation_error();
            this.makeWidget();
            // The confirmation popup should be shown so stub out the save
            // method and check the behaviour.
            var orig_save_information_type = ns.save_information_type;
            var function_called = false;
            ns.save_information_type =
                    function(widget, initial_value, value, lp_client,
                             context, subscribers_list, validate_change) {
                // We only care if the function is called with
                // validate_change = false
                Y.Assert.areEqual('PUBLIC', initial_value);
                Y.Assert.areEqual('USERDATA', value);
                Y.Assert.isFalse(validate_change);
                function_called = true;
            };
            // We click 'yes' on the confirmation dialog.
            var co = Y.one('.yui3-overlay.yui3-lp-app-confirmationoverlay');
            var div = co.one('.yui3-lazr-formoverlay-actions');
            var ok = div.one('.ok-btn');
            ok.simulate('click');
            var description_node = Y.one('#information-type-description');
            Y.Assert.areEqual(
                    'Private Description', description_node.get('text'));
            var summary = Y.one('#information-type-summary');
            Y.Assert.isTrue(summary.hasClass('private'));
            Y.Assert.isTrue(function_called);
            ns.save_information_type = orig_save_information_type;
        },

        // Selecting a new private information type shows the
        // confirmation dialog and doesn't call save when user says 'no'.
        test_perform_update_information_type_to_private_no: function() {
            this._assert_save_with_validation_error();
            // The confirmation popup should be shown so stub out the save
            // method and check the behaviour.
            var orig_save_information_type = ns.save_information_type;
            var function_called = false;
            ns.save_information_type =
                    function(widget, initial_value, value, lp_client,
                             context, subscribers_list, validate_change) {
                // We only care if the function is called with
                // validate_change = false
                function_called = !validate_change;
            };
            // We click 'no' on the confirmation dialog.
            var co = Y.one('.yui3-overlay.yui3-lp-app-confirmationoverlay');
            var div = co.one('.yui3-lazr-formoverlay-actions');
            var ok = div.one('.cancel-btn');
            ok.simulate('click');
            // Original widget value, description etc should be retained.
            Y.Assert.areEqual('PUBLIC', this.widget.get('value'));
            var description_node = Y.one('#information-type-description');
            Y.Assert.areEqual(
                    'Public Description', description_node.get('text'));
            var summary = Y.one('#information-type-summary');
            Y.Assert.isFalse(summary.hasClass('private'));
            Y.Assert.isFalse(function_called);
            ns.save_information_type = orig_save_information_type;
        },

        // Test error handling when a save fails.
        test_information_type_save_error: function() {
            this.makeWidget();
            this.widget.set('value', 'USERDATA');
            ns.save_information_type(
                    this.widget, 'PUBLIC', 'USERDATA', this.lp_client,
                    LP.cache.bug);
            this.mockio.last_request.respond({
                status: 500,
                statusText: 'An error occurred'
            });
            // The original info type value from the cache should have been
            // set back into the widget.
            Y.Assert.areEqual('PUBLIC', this.widget.get('value'));
            var description_node = Y.one('#information-type-description');
            Y.Assert.areEqual(
                'Public Description', description_node.get('text'));
            var summary = Y.one('#information-type-summary');
            Y.Assert.isTrue(summary.hasClass('public'));
            // The error was displayed.
            Y.Assert.isNotNull(Y.one('.yui3-lazr-formoverlay-errors'));
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.client', 'lp.app.information_type',
        'lp.bugs.subscribers']});
