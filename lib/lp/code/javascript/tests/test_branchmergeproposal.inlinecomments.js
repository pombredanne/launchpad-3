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
                preview_diff_link: "https://code.launchpad.dev/api/devel/~foo/bar/foobr/+merge/1/preview_diff",
                preview_diffs_collection_link: "https://code.launchpad.dev/api/devel/~foo/bar/foobr/+merge/1/preview_diffs"
            };

            LP.cache.inline_diff_comments = true;
            module.current_previewdiff_id = 1;
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
                "resource_type_link": "http://launchpad.dev/api/devel/#person"
            };

            // Overrides module LP client by one using 'mockio'.
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.lp_client = new Y.lp.client.Launchpad(
                {io_provider: mockio});

            // Populate the page.
            module.populate_existing_comments();

            // LP was hit twice for fetching published and draft inline
            // comments
            Y.Assert.areEqual(2, mockio.requests.length);

            // Last request was for loading draft comments, let's
            // respond it.
            Y.Assert.areSame(
                "ws.op=getDraftInlineComments&previewdiff_id=1",
                mockio.requests[1].config.data);
            draft_comments = {'3': 'Zoing!'};
            mockio.success({
                responseText: Y.JSON.stringify(draft_comments),
                responseHeaders: {'Content-Type': 'application/json'}});

            // First request was for loading published comments, let's
            // respond it (mockio.last_request need a tweak to respond
            // past requests)
            Y.Assert.areSame(
                "ws.op=getInlineComments&previewdiff_id=1",
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
                'Comment by Foo Bar (name16) on 2012-08-12',
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
            module.lp_client = new Y.lp.client.Launchpad(
                {io_provider: mockio});

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
            module.current_previewdiff_id = null

            LP.cache.inline_diff_comments = false;
            module.current_previewdiff_id = null
            module.setup_inline_comments(1);

            Y.Assert.isFalse(called);
            Y.Assert.isNull(module.current_previewdiff_id);
        },

        test_feature_flag: function() {
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;
            module.current_previewdiff_id = null

            module.setup_inline_comments(1);

            Y.Assert.isTrue(called);
            Y.Assert.areEqual(1, module.current_previewdiff_id);
        },

        test_diff_nav_feature_flag_disabled: function() {
            // Disable feature flag.
            LP.cache.inline_diff_comments = false;
            // Overrides module LP client by one using 'mockio'.
            var mockio = new Y.lp.testing.mockio.MockIo();
            lp_client = new Y.lp.client.Launchpad({io_provider: mockio});
            // Create a fake setup_inline_comments for testing purposes.
            var called_diff_id = null;
            fake_setup = function(diff_id) {
                called_diff_id = diff_id;
            };
            module.setup_inline_comments = fake_setup;
            // Render DiffNav widget..
            (new module.DiffNav(
                 {srcNode: Y.one('#review-diff'), lp_client: lp_client}
            )).render();
            // Nothing actually happens.
            Y.Assert.areEqual(0, mockio.requests.length);
            Y.Assert.isNull(called_diff_id);
        },

        test_diff_nav: function() {
            // Overrides module LP client by one using 'mockio'.
            var mockio = new Y.lp.testing.mockio.MockIo();
            lp_client = new Y.lp.client.Launchpad(
                {io_provider: mockio});
            // Create a fake setup_inline_comments for testing purposes.
            var called_diff_id = null;
            fake_setup = function(diff_id) {
                called_diff_id = diff_id;
            };
            module.setup_inline_comments = fake_setup;
            // Render DiffNav widget on the test HTML content.
            (new module.DiffNav(
                 {srcNode: Y.one('#review-diff'), lp_client: lp_client}
            )).render();
            // diff-navigator section content is rendered based on the
            // preview_diffs API object.
            Y.Assert.areEqual(1, mockio.requests.length);
            Y.Assert.areSame(
                "/api/devel/~foo/bar/foobr/+merge/1/preview_diffs",
                mockio.last_request.url);
            var preview_diffs = {
                total_size: 2,
                start: 0,
                entries: [
                    {title: 'r2 into r2', id: 202,
                     date_created: '2014-02-22T10:00:00.00001+00:00',
                     self_link: 'something-else'},
                    {title: 'r1 into r1', id: 101,
                     date_created: '2014-02-20T18:07:38.678947+00:00',
                     self_link: LP.cache.context.preview_diff_link}
                ]
            }
            mockio.success({
                responseText: Y.JSON.stringify(preview_diffs),
                responseHeaders: {'Content-Type': 'application/json'}});
            // The local (fake) setup_inline_comments function
            // was called with the selected diff_id value.
            Y.Assert.areEqual(101, called_diff_id);
            // The option corresponding to the current 'preview_diff'
            // is selected and contains the expected text (title and
            // formatted date_created). 
            Y.Assert.areEqual(1, Y.one('select').get('selectedIndex'));
            Y.Assert.areEqual(
                'r1 into r1 on 2014-02-20',
                Y.one('select').get('options').item(1).get('text'));
            // Simulate a change in the diff navigator.
            Y.one('select').set('value', 202);
            Y.one('select').simulate('change');
            // diff content was updated with the selected diff_id content.
            Y.Assert.areEqual(2, mockio.requests.length);
            Y.Assert.areSame(
                "/~foo/bar/foobr/+merge/1/+preview-diff/202/+diff",
                mockio.last_request.url);
            // remove NumberToggle content before reusing 'diff-content'
            // content, so we do not have it rendered twice.
            Y.one('.diff-content div div ul.horizontal').empty();
            mockio.success({
                responseText: Y.one('.diff-content').get('innerHTML'),
                responseHeaders: {'Content-Type': 'text/html'}});
            Y.Assert.areEqual(202, called_diff_id);
        }

    }));

}, '0.1', {
    requires: ['node-event-simulate', 'test', 'lp.testing.helpers',
               'console', 'lp.client', 'lp.testing.mockio', 'widget',
               'lp.code.branchmergeproposal.inlinecomments',
               'lp.code.branchmergeproposal.reviewcomment']
});
