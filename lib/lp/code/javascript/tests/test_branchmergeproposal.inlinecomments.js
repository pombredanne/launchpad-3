/* Copyright 2014 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.code.branchmergeproposal.inlinecomments.test', function (Y) {

    var module = Y.lp.code.branchmergeproposal.inlinecomments;
    var tests = Y.namespace('lp.code.branchmergeproposal.inlinecomments.test');
    tests.suite = new Y.Test.Suite('branchmergeproposal.inlinecomments Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'code.branchmergeproposal.inlinecomments_tests',

        setUp: function () {
            // Loads testing values into LP.cache.
            LP.cache.context = {
                web_link: "https://launchpad.dev/~foo/bar/foobr/+merge/1",
                self_link: "https://code.launchpad.dev/api/devel/~foo/bar/foobr/+merge/1",
	    };

            LP.cache.inline_diff_comments = true;
	    module.current_diff_id = 1;
            module.inlinecomments = {};
        },

        tearDown: function () {},

        test_library_exists: function () {
            Y.Assert.isObject(
                module, "Could not locate the " +
                "lp.code.branchmergeproposal.inlinecomments module");
        },

        test_population: function () {
            // Mimics a person object as stored in LP.cache (unwrap).
            var person_obj = {
                "display_name": "Foo Bar",
                "name": "name16",
                "web_link": "http://launchpad.dev/~name16",
                "resource_type_link": "http://launchpad.dev/api/devel/#person",
            };

            // Overrides module LP client by one using 'mockio'.
            var mockio = new Y.lp.testing.mockio.MockIo();
            var ns = Y.namespace(
                'lp.code.branchmergeproposal.inlinecomments');
            ns.lp_client = new Y.lp.client.Launchpad({io_provider: mockio});

            // Populate the page.
            module.populate_existing_comments();

	    // LP was hit twice for fetching published and draft inline
	    // comments
            Y.Assert.areEqual(2, mockio.requests.length);

	    // Last request was for loading draft comments, let's
	    // respond it.
            Y.Assert.areSame(
                "ws.op=getDraftInlineComments&diff_id=1",
		mockio.requests[1].config.data);
            draft_comments = {'3': 'Zoing!'};
            mockio.success({
                responseText: Y.JSON.stringify(draft_comments),
                responseHeaders: {'Content-Type': 'application/json'}});

	    // First request was for loading published comments, let's
	    // respond it (mockio.last_request need a tweak to respond
	    // past requests)
            Y.Assert.areSame(
                "ws.op=getInlineComments&diff_id=1",
		mockio.requests[0].config.data);
	    mockio.last_request = mockio.requests[0];
            published_comments = [
                {'line_number': '2',
                 'person': person_obj,
                 'text': 'This is preloaded.',
                 'date': '2012-08-12 17:45'},
            ];
            mockio.success({
                responseText: Y.JSON.stringify(published_comments),
                responseHeaders: {'Content-Type': 'application/json'}});

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
            // Setup diff lines 'click' handlers.
            module.add_doubleclick_handler();

            // Overrides module LP client by one using 'mockio'.
            var mockio = new Y.lp.testing.mockio.MockIo();
            var ns = Y.namespace(
                'lp.code.branchmergeproposal.inlinecomments');
            ns.lp_client = new Y.lp.client.Launchpad({io_provider: mockio});

            // No draft comment in line 1.
            Y.Assert.isNull(Y.one('#ict-1-draft-header'));

            // Let's create one.
            var line  = Y.one('#diff-line-1');
            line.simulate('dblclick');
            var ic_area = line.next().next();
            ic_area.one('.yui3-ieditor-input>textarea').set('value', 'Go!');
            ic_area.one('.lazr-pos').simulate('click');

            // LP was hit and a comment was created.
            Y.Assert.areEqual(1, mockio.requests.length);
            Y.Assert.areEqual(
                'Draft comment.', Y.one('#ict-1-draft-header').get('text'));
            Y.Assert.areEqual(
                'Go!', ic_area.one('.yui3-editable_text-text').get('text'));

            // Cancelling a draft comment attempt ...
            line.simulate('dblclick');
            var ic_area = line.next().next();
            ic_area.one('.yui3-ieditor-input>textarea').set('value', 'No!');
            ic_area.one('.lazr-neg').simulate('click');

            // LP is not hit and the previous comment is preserved.
            Y.Assert.areEqual(1, mockio.requests.length);
            Y.Assert.areEqual(
                'Go!', ic_area.one('.yui3-editable_text-text').get('text'));

            // Removing a draft comment by submitting an emtpy text.
            line.simulate('dblclick');
            var ic_area = line.next().next();
            ic_area.one('.yui3-ieditor-input>textarea').set('value', '');
            ic_area.one('.lazr-pos').simulate('click');

            // LP is hit again and the previous comment is removed,
            // the next row diplayed is the next diff line.
            Y.Assert.areEqual(2, mockio.requests.length);
            Y.Assert.isNull(Y.one('#ict-1-draft-header'));
            Y.Assert.areEqual('diff-line-2', line.next().get('id'));
        },

        test_feature_flag_off: function() {
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;

            LP.cache.inline_diff_comments = false;
	    module.current_diff_id = null
            module.setup_inline_comments(1);

            Y.Assert.isFalse(called);
            Y.Assert.isNull(module.current_diff_id);
        },

        test_feature_flag: function() {
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;

	    module.current_diff_id = null
            module.setup_inline_comments(1);

            Y.Assert.isTrue(called);
            Y.Assert.areEqual(1, module.current_diff_id);
        }

    }));

}, '0.1', {
    requires: ['node-event-simulate', 'test', 'lp.testing.helpers',
               'console', 'lp.client', 'lp.testing.mockio',
               'lp.code.branchmergeproposal.inlinecomments']
});
