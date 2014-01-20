/* Copyright 2013 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.code.branchmergeproposal.inlinecomments.test', function (Y) {

    var module = Y.lp.code.branchmergeproposal.inlinecomments;
    var tests = Y.namespace('lp.code.branchmergeproposal.inlinecomments.test');
    tests.suite = new Y.Test.Suite('branchmergeproposal.inlinecomments Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'code.branchmergeproposal.inlinecomments_tests',

        setUp: function () {
            LP.cache.published_inline_comments = [];
            LP.cache.draft_inline_comments = {};
            LP.cache.inline_diff_comments = true;
        },
        tearDown: function () {},

        test_library_exists: function () {
            Y.Assert.isObject(
                module, "Could not locate the " +
                "lp.code.branchmergeproposal.inlinecomments module");
        },

        test_population: function () {
            // Mimic a person object as stored in LP.cache (unwrap).
            var person_obj = {
                "display_name": "Foo Bar",
                "name": "name16",
                "web_link": "http://launchpad.dev/~name16",
                "resource_type_link": "http://launchpad.dev/api/devel/#person",
            };

            // Create a published and a draft inline comments.
            LP.cache.published_inline_comments = [
                {'line_number': '2',
                 'person': person_obj,
                 'text': 'This is preloaded.',
                 'date': '2012-08-12 17:45'},
            ];
            LP.cache.draft_inline_comments = {'3': 'Zoing!'};

            // Populate the page.
            module.populate_existing_comments();

            // Published comment is displayed.
            var header = Y.one('#diff-line-2').next();
            Y.Assert.areEqual(
                'Comment by Foo Bar (name16) on 2012-08-12 17:45',
                header.get('text'));
            var text = header.next();
            Y.Assert.areEqual('This is preloaded.', text.get('text'));

            // Draft comment is displayed.
            var header = Y.one('#diff-line-3').next();
            Y.Assert.areEqual('Draft comment.', header.get('text'));
            var text = header.next();
            Y.Assert.areEqual('Zoing!', text.get('text'));
        },

        test_draft_handler: function() {
            module.add_doubleclick_handler();

            Y.Assert.isNull(Y.one('#ict-1-draft-header'));

            var line  = Y.one('#diff-line-1');

            line.simulate('dblclick');
            var ic_area = line.next().next();
            ic_area.one(
                '.yui3-ieditor-input>textarea').set('value', 'Go!');
            ic_area.one('.lazr-pos').simulate('click');

            Y.Assert.areEqual(
                'Go!', ic_area.one('.yui3-editable_text-text').get('text'));
        },

        test_feature_flag_off: function() {
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;

            LP.cache.inline_diff_comments = false;
            module.setup_inline_comments();
            Y.Assert.isFalse(called);
        },

        test_feature_flag: function() {
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;
            module.setup_inline_comments();
            Y.Assert.isTrue(called);
        }

    }));

}, '0.1', {
    requires: ['node-event-simulate', 'test', 'lp.testing.helpers', 'console',
               'lp.client', 'lp.code.branchmergeproposal.inlinecomments']
});
