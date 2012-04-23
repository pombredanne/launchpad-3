/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.bugs.information_type_choice.test', function (Y) {

    var tests = Y.namespace('lp.bugs.information_type_choice.test');
    tests.suite = new Y.Test.Suite('lp.bugs.information_type_choice Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.bugs.information_type_choice_tests',

        setUp: function() {
            window.LP = {
                cache: {
                    context: {
                        bug_link: '/bug/1',
                        web_link: '/base'
                    },
                    bug: {
                        information_type: 'Public'
                    },
                    show_information_type_in_ui: true,
                    private_types: ['Private'],
                    information_types: [
                        {'description': 'Public', 'name': 'Public'},
                        {'description': 'Private', 'name': 'Private'}
                    ]
                }
            };
        },
        tearDown: function () {},

        test_perform_update_information_type: function() {
            var mockio = new Y.lp.testing.mockio.MockIO();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: mockio
            });
            var privacy_link = Y.one('.privacy-link');
            var ns = Y.lp.bugs.information_type_choice;
            var view = ns.setup_information_type_choice(privacy_link);
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'lp.bugs.information_type_choice']});
