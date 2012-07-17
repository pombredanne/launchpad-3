/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.bugs.information_type_choice.test', function (Y) {

    var tests = Y.namespace('lp.bugs.information_type_choice.test');
    var ns = Y.lp.bugs.information_type_choice;
    tests.suite = new Y.Test.Suite('lp.bugs.information_type_choice Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.bugs.information_type_choice_tests',

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
                        {'value': 'PROPRIETARY', 'name': 'Proprietary',
                            'description': 'Private User Description'},
                        {'value': 'USERDATA', 'name': 'Private User',
                            'description': 'Private Description'}
                    ]
                }
            };
            this.fixture = Y.one('#fixture');
            var portlet = Y.Node.create(
                    Y.one('#portlet-template').getContent());
            this.fixture.appendChild(portlet);

            var lp_client = new Y.lp.client.Launchpad();
            var privacy_link = Y.one('#privacy-link');
            this.widget = ns.setup_information_type_choice(
                privacy_link, lp_client, true);
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
            delete window.LP;
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
            Y.Assert.isObject(Y.lp.bugs.information_type_choice,
                "Cannot locate the lp.bugs.information_type_choice module");
        },

        // The save XHR call works as expected.
        test_save_information_type: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            var orig_save_success = ns.information_type_save_success;
            var save_success_called = false;
            ns.information_type_save_success = function(widget, value,
                                                   subscribers_list,
                                                   subscribers_data) {
                Y.Assert.areEqual('USERDATA', value);
                Y.Assert.areEqual(
                    'subscribers', subscribers_data.subscription_data);
                Y.Assert.areEqual(
                    'value', subscribers_data.cache_data.item);
                save_success_called = true;
            };
            ns.save_information_type(this.widget, 'USERDATA', lp_client);
            mockio.success({
                responseText: '{"subscription_data": "subscribers",' +
                    '"cache_data": {"item": "value"}}',
                responseHeaders: {'Content-Type': 'application/json'}});
            Y.Assert.areEqual('/+secrecy', mockio.last_request.url);
            Y.Assert.areEqual(
                'field.actions.change=Change&' +
                'field.information_type=USERDATA',
                mockio.last_request.config.data);
            Y.Assert.isTrue(save_success_called);
            ns.information_type_save_success = orig_save_success;
        },

        // Setting a private type shows the privacy banner.
        test_information_type_save_success_private: function() {
            var old_func = this._shim_privacy_banner();
            var hide_flag = false;
            var update_flag = false;
            Y.on('test:banner:show', function() {
                hide_flag = true;
            });
            Y.on('test:banner:update', function() {
                update_flag = true;
            });

            ns.information_type_save_success(this.widget, 'PROPRIETARY');
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
                this.widget, 'PUBLIC', subscribers_list, subscribers_data);
            Y.Assert.isTrue(load_subscribers_called);
            Y.Assert.areEqual('value1', window.LP.cache.item1);
            Y.Assert.areEqual('value2', window.LP.cache.item2);
            this._unshim_privacy_banner(old_func);
        },

        // Selecting a new information type calls save correctly.
        test_perform_update_information_type: function() {
            var privacy_link = Y.one('#privacy-link');
            privacy_link.simulate('click');
            var private_choice = Y.one(
                '.yui3-ichoicelist-content a[href="#USERDATA"]');
            var orig_save_information_type = ns.save_information_type;
            var function_called = false;
            ns.save_information_type = function(widget, value, lp_client) {
                Y.Assert.areEqual(
                    'USERDATA', value); function_called = true; };
            private_choice.simulate('click');
            var description_node = Y.one('#information-type-description');
            Y.Assert.areEqual(
                'Private Description', description_node.get('text'));
            var summary = Y.one('#information-type-summary');
            Y.Assert.isTrue(summary.hasClass('private'));
            Y.Assert.isTrue(function_called);
            ns.save_information_type = orig_save_information_type;
        },

        // Test error handling when a save fails.
        test_information_type_save_error: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            this.widget.set('value', 'USERDATA');
            ns.save_information_type(this.widget, 'USERDATA', lp_client);
            mockio.last_request.respond({
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
        'lp.testing.mockio', 'lp.client','lp.bugs.subscribers',
        'lp.bugs.information_type_choice']});
