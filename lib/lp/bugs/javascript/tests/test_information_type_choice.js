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
                    show_information_type_in_ui: true,
                    private_types: ['Private'],
                    information_types: [
                        {'value': 'Public', 'description': 'Public',
                            'name': 'Public'},
                        {'value': 'Private', 'description': 'Private',
                            'name': 'Private'}
                    ]
                }
            };
        },
        tearDown: function () {},

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.bugs.information_type_choice,
                "Cannot locate the lp.bugs.information_type_choice module");
        },

        test_save_information_type: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            ns.save_information_type('User Data', lp_client);
            Y.Assert.areEqual('/api/devel/bug/1', mockio.last_request.url);
            Y.Assert.areEqual(
                'ws.op=transitionToInformationType&' +
                'information_type=User%20Data',
                mockio.last_request.config.data);
        },

        _shim_privacy: function() {
            var prototype = Y.lp.app.banner.privacy.PrivacyBanner.prototype;  
            var orig_hide = prototype.hide,
                orig_show = prototype.show,
                orig_render = prototype.render;

            prototype.render = function () {};
            prototype.show = function () {
                Y.fire('show');
            }
            prototype.hide = function () {
                Y.fire('hide');
            }
            return {
                hide: orig_hide,
                render: orig_render,
                show: orig_show
            }
        },

        _unshim_privacy: function (old_funcs) {
            this._banner_show_called = false;
            this._banner_hide_called = false;
            var prototype = Y.lp.app.banner.privacy.PrivacyBanner.prototype;  

            prototype.render = old_funcs.render;
            prototype.hide = old_funcs.hide;
            prototype.show = old_funcs.show;
        },

        test_information_type_save_success_private: function() {
            funcs = this._shim_privacy();
            var flag = false;
            Y.on('show', function() {
                flag = true; 
            });

            ns.information_type_save_success('Private');
            var body = Y.one('body');
            Y.Assert.isTrue(body.hasClass('private'));
            Y.Assert.isTrue(flag);

            this._unshim_privacy(funcs);
        },

        test_information_type_save_success_public: function() {
            funcs = this._shim_privacy();
            var flag = false;
            Y.on('hide', function() {
                flag = true; 
            });

            ns.information_type_save_success('Public');
            var body = Y.one('body');
            Y.Assert.isTrue(body.hasClass('public'));
            Y.Assert.isTrue(flag);

            this._unshim_privacy(funcs);
        },

        test_perform_update_information_type: function() {
            var lp_client = new Y.lp.client.Launchpad();
            var privacy_link = Y.one('#privacy-link');
            var information_type = Y.one('#information-type');
            ns.setup_information_type_choice(privacy_link, lp_client);
            privacy_link.simulate('click');
            var private_choice = Y.one(
                '.yui3-ichoicelist-content a[href=#Private]');
            var orig_save_information_type = ns.save_information_type;
            var function_called = false;
            ns.save_information_type = function(value, lp_client) {
                Y.Assert.areEqual('User Data', value); function_called = true; };
            private_choice.simulate('click');
            Y.Assert.isTrue(function_called);
            ns.save_information_type = orig_save_information_type;
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.client', 'lp.bugs.information_type_choice',
        'lp.app.banner.privacy']});
