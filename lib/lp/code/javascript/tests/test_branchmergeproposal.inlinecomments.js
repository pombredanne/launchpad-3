/* Copyright 2013 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.code.branchmergeproposal.inlinecomments.test', function (Y) {

    var module = Y.lp.code.branchmergeproposal.inlinecomments;
    var tests = Y.namespace('lp.code.branchmergeproposal.inlinecomments.test');
    tests.suite = new Y.Test.Suite('branchmergeproposal.inlinecomments Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'code.branchmergeproposal.inlinecomments_tests',

        setUp: function () {},
        tearDown: function () {},

        test_library_exists: function () {
            Y.Assert.isObject(
                module, "Could not locate the " +
                "lp.code.branchmergeproposal.inlinecomments module");
        },

        test_populatation: function () {
            var published_inline_comments = [
                {'line': 2, 'person': {'display_name': 'Sample Person',
                'name': 'name12', 'web_link': 'http://launchpad.dev/~name12'},
                'comment': 'This is preloaded.', 'date': '2012-08-12 17:45'}];
            LP.cache.published_inline_comments = published_inline_comments;
            module.populate_existing_comments();
            Y.Assert.isObject(Y.one('#ict-2-name12-header'));
        },

        test_handler_normal: function() {
            module.add_doubleclick_handler();
            var line_2  = Y.one('#diff-line-2');
            line_2.simulate('dblclick');
            var comment = 'This is a comment.';
            Y.one('.yui3-ieditor-input>textarea').set('value', comment);
            Y.one('.lazr-pos').simulate('click');
            Y.Assert.areEqual(
                comment, Y.one('.yui3-editable_text-text').get('text'));
        },

        test_handler_cancel: function() {
            var line_2  = Y.one('#diff-line-2');
            line_2.simulate('dblclick');
            var comment = 'Cancelling test.';
            Y.one('.yui3-ieditor-input>textarea').set('value', comment);
            Y.one('.lazr-pos').simulate('click');
            line_2.simulate('dblclick');
            Y.one('.yui3-ieditor-input>textarea').set('value', 'Foobar!');
            Y.one('.lazr-neg').simulate('click');
            Y.Assert.areEqual(
                comment, Y.one('.yui3-editable_text-text').get('text'));
        },

        test_handler_cancel_immediately: function() {
            var line_1  = Y.one('#diff-line-1');
            line_1.simulate('dblclick');
            Y.one('.lazr-neg').simulate('click');
            Y.Assert.isNull(Y.one('#ict-1-draft-header'));
        },

        test_feature_flag_off: function() {
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;
            module.setup_inline_comments();
            Y.Assert.isFalse(called);
        },

        test_feature_flag: function() {
            LP.cache.published_inline_comments = [];
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;
            window.LP.cache.inline_diff_comments = true;
            module.setup_inline_comments();
            Y.Assert.isTrue(called);
        }

    }));

}, '0.1', {
    requires: ['node-event-simulate', 'test', 'lp.testing.helpers', 'console',
        'lp.code.branchmergeproposal.inlinecomments']
});
