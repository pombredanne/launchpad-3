/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.app.inlinehelp.test', function (Y) {

    var suite = new Y.Test.Suite('InlineHelp Tests');
    var Assert = Y.Assert;
    var test_module = Y.namespace('lp.app.inlinehelp.test');

    suite.add(new Y.Test.Case({
        name: 'inlinehelp.init_help',

        setUp: function () {
            var link_html = Y.Node.create('<a href="" target="help"/>');
            Y.one('body').appendChild(link_html);
        },

        tearDown: function () {
            Y.all('a[target="help"]').remove();
            Y.one('body').detach('click');
        },

        test_adding_css_class: function () {
            // calling init help should add a help css class to all links with
            // target=help
            var called = false;
            Y.lp.app.inlinehelp.init_help();
            Y.all('a[target="help"]').each(function (node) {
                called = true;
                Y.Assert.isTrue(node.hasClass('help'),
                    'Each link should have the class "help"');
            });

            Y.Assert.isTrue(called, 'We should have called our class check');
        },

        test_binding_click_link: function () {
            // calling init help should a delegated click handler for the help
            // links

            // we need to mock out the inlinehelp.show_help function to add a
            // callable to run tests for us when clicked
            var orig_show_help = Y.lp.app.show_help;
            var called = false;

            Y.lp.app.inlinehelp.show_help = function (e) {
                e.preventDefault();
                called = true;

                Y.Assert.areEqual(e.target.get('target'), 'help',
                    'The event target should be our <a> with target = help');
            };

            Y.lp.app.inlinehelp.init_help();

            Y.one('a[target="help"]').simulate('click');
            Y.Assert.isTrue(
                called,
                'We should have called our show_help function'
            );

            // restore the original show_help method for future tests
            Y.lp.app.inlinehelp.show_help = orig_show_help;
        },

        test_binding_click_only_once: function () {
            //verify that multiple calls to init_help only causes one click
            //event to fire
            //
            var orig_show_help = Y.lp.app.show_help;
            var called = 0;

            Y.lp.app.inlinehelp.show_help = function (e) {
                e.preventDefault();
                called = called + 1;
            };

            Y.lp.app.inlinehelp.init_help();
            Y.lp.app.inlinehelp.init_help();
            Y.lp.app.inlinehelp.init_help();
            Y.lp.app.inlinehelp.init_help();

            Y.one('a[target="help"]').simulate('click');
            Y.Assert.areEqual(
                called,
                1,
                'We should have called our show_help function only once'
            );


            // restore the original show_help method for future tests
            Y.lp.app.inlinehelp.show_help = orig_show_help;
        }
    }));

test_module.suite = suite;

}, '0.1', {'requires': ['node', 'console', 'test', 'lp.app.inlinehelp', 'node-event-simulate']});
