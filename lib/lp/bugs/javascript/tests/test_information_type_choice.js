/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.bugs.information_type_choice.test', function (Y) {

    var tests = Y.namespace('lp.bugs.information_type_choice.test');
    tests.suite = new Y.Test.Suite('lp.bugs.information_type_choice Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.bugs.information_type_choice_tests',

        setUp: function() {
            window.LP = {
                cache: {
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

        test_perform_update_information_type: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            var privacy_link = Y.one('#privacy-link');
            var information_type = Y.one('#information-type');
            var ns = Y.lp.bugs.information_type_choice;
            ns.setup_information_type_choice(privacy_link, lp_client);
            privacy_link.simulate('click');
            var private_choice = Y.one(
                '.yui3-ichoicelist-content a[href=#Private]');
            private_choice.simulate('click');
            Y.Assert.areEqual('Private', information_type.get('text'));
            Y.Assert.areEqual('/api/devel/bug/1', mockio.last_request.url);
            Y.Assert.areEqual(
                'ws.op=transitionToInformationType&' +
                'information_type=User%20Data',
                mockio.last_request.config.data);
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.client', 'lp.bugs.information_type_choice']});
