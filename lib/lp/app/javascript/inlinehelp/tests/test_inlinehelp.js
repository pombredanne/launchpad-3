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
        },

        test_adding_css_class: function () {
            var called = false;
            Y.lp.app.inlinehelp.init_help();
            Y.all('a[target="help"]').each(function (node) {
                called = true;
                Y.Assert.isTrue(node.hasClass('help'),
                    'Each link should have the class "help"');
            });

            Y.Assert.isTrue(called, 'We should have called our class check');
        }
    }));

test_module.suite = suite;

}, '0.1', {'requires': ['node', 'console', 'test', 'lp.app.inlinehelp']});
