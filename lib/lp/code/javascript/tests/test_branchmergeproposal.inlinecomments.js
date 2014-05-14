/* Copyright 2014 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.code.branchmergeproposal.inlinecomments.test', function (Y) {

    var module = Y.lp.code.branchmergeproposal.inlinecomments;
    var tests = Y.namespace('lp.code.branchmergeproposal.inlinecomments.test');
    tests.suite = new Y.Test.Suite('branchmergeproposal.inlinecomments Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'code.branchmergeproposal.inlinecomments_comments_tests',

        setUp: function () {
            // Loads testing values into LP.cache.
            LP.cache.context = {
                self_link: ("https://code.launchpad.dev/api/devel/" +
                            "~foo/bar/foobr/+merge/1")
            };
            LP.links = {
                me : 'something'
            };
            LP.cache.inline_diff_comments = true;
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
            module.current_previewdiff_id = 1;
            module.populate_comments();
            module.populate_drafts();

            // LP was hit twice for fetching published and draft inline
            // comments
            Y.Assert.areEqual(2, mockio.requests.length);

            // Last request was for loading draft comments, let's
            // respond it.
            Y.Assert.areSame(
                "ws.op=getDraftInlineComments&previewdiff_id=1",
                mockio.requests[1].config.data);
            draft_comments = {'2': 'Boing!', '3': 'Zoing!'};
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
                 'date': '2012-08-12T10:00:00.00001+00:00'}
            ];
            mockio.success({
                responseText: Y.JSON.stringify(published_comments),
                responseHeaders: {'Content-Type': 'application/json'}});

            // Published comment is displayed.
            var comments = Y.one('#diff-line-2').next().one('div');
            // XXX cprov 20140226: test disabled due to ES4 lack of
            // ISO8601 support. Although the vast majority of production
            // clients run ES5.
            //Y.Assert.areEqual(
            //    'Comment by Foo Bar (name16) on 2012-08-12',
            //    header.get('text'));
            var first = comments.one('div:first-child')
            Y.Assert.areEqual(
                'This is preloaded.',
                first.one('.boardCommentBody').get('text'));

            // Draft comment for line 2 is displayed after all published
            // comments.
            var second = first.next()
            Y.Assert.areEqual(
                'Draft comment',
                second.one('.boardCommentDetails').get('text'));
            Y.Assert.areEqual(
                'Boing!', second.one('.boardCommentBody').get('text'));

            // Draft comment for line 3 is displayed.
            var third = Y.one('#diff-line-3').next();
            Y.Assert.areEqual(
                'Draft comment',
                third.one('.boardCommentDetails').get('text'));
            Y.Assert.areEqual(
                'Zoing!', third.one('.boardCommentBody').get('text'));
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
            var ic_area = line.next();
            ic_area.one('.yui3-ieditor-input>textarea').set('value', 'Go!');
            ic_area.one('.lazr-pos').simulate('click');

            // LP was hit and a comment was created.
            Y.Assert.areEqual(1, mockio.requests.length);
            Y.Assert.areEqual(
                'Draft comment',
                ic_area.one('.boardCommentDetails').get('text'));
            Y.Assert.areEqual(
                'Go!', ic_area.one('.yui3-editable_text-text').get('text'));

            // Cancelling a draft comment attempt ...
            line.simulate('dblclick');
            ic_area = line.next();
            ic_area.one('.yui3-ieditor-input>textarea').set('value', 'No!');
            ic_area.one('.lazr-neg').simulate('click');

            // LP is not hit and the previous comment is preserved.
            Y.Assert.areEqual(1, mockio.requests.length);
            Y.Assert.areEqual(
                'Go!', ic_area.one('.yui3-editable_text-text').get('text'));

            // Removing a draft comment by submitting an emtpy text.
            line.simulate('dblclick');
            ic_area = line.next();
            ic_area.one('.yui3-ieditor-input>textarea').set('value', '');
            ic_area.one('.lazr-pos').simulate('click');

            // LP is hit again and the previous comment is removed,
            // the next row diplayed is the next diff line.
            Y.Assert.areEqual(2, mockio.requests.length);
            Y.Assert.isNull(Y.one('#ict-1-draft'));
            Y.Assert.areEqual('diff-line-2', line.next().get('id'));
        },

        test_edit_cancelling: function() {
            // Cancelling a inline comment attempt on a row with
            // no comments does not leave an empty row behind.
            module.add_doubleclick_handler();
            var line  = Y.one('#diff-line-1');
            line.simulate('dblclick');
            ic_area = line.next();
            ic_area.one('.yui3-ieditor-input>textarea').set('value', '');
            ic_area.one('.lazr-neg').simulate('click');
            Y.Assert.areEqual('diff-line-2', line.next().get('id'));
        },

        test_feature_flag_off: function() {
            var called = false;
            add_doubleclick_handler = function() {
                called = true;
            };
            module.add_doubleclick_handler = add_doubleclick_handler;
            module.current_previewdiff_id = null;

            LP.cache.inline_diff_comments = false;
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
            module.current_previewdiff_id = null;

            module.setup_inline_comments(1);

            Y.Assert.isTrue(called);
            Y.Assert.areEqual(1, module.current_previewdiff_id);
        },

        test_feature_not_logged_in: function() {
            // Draft inline-comments are not loaded and doubleclick-handlers
            // are not set for anonymous requests.
            var doubleclick_called = false;
            var draft_called = false;
            module.add_doubleclick_handler = function() {
                doubleclick_called = true;
            };
            module.populate_draft = function() {
                draft_called = true;
            };
            module.current_previewdiff_id = null;

            LP.links = {};
            module.setup_inline_comments(1);

            Y.Assert.isFalse(doubleclick_called);
            Y.Assert.isFalse(draft_called);
            Y.Assert.areEqual(1, module.current_previewdiff_id);
        }

    }));

    tests.suite.add(new Y.Test.Case({
        name: 'code.branchmergeproposal.inlinecomments_diffnav_tests',

        setUp: function () {
            // Loads testing values into LP.cache.
            LP.cache.context = {
                web_link: "https://launchpad.dev/~foo/bar/foobr/+merge/1",
                self_link: ("https://code.launchpad.dev/api/devel/" +
                            "~foo/bar/foobr/+merge/1"),
                preview_diff_link: ("https://code.launchpad.dev/api/devel/" +
                                    "~foo/bar/foobr/+merge/1/preview_diff"),
                preview_diffs_collection_link: (
                    "https://code.launchpad.dev/api/devel/" +
                    "~foo/bar/foobr/+merge/1/preview_diffs")
            };

            LP.cache.inline_diff_comments = true;
            // Disable/Instrument inlinecomments hook.
            var self = this;
            self.inline_comments_requested_id = null;
            module.setup_inline_comments = function(previewdiff_id) {
                self.inline_comments_requested_id = previewdiff_id;
            };
            // Create an instrument DiffNav instance.
            lp_client = new Y.lp.client.Launchpad(
                 {io_provider: new Y.lp.testing.mockio.MockIo()});
            this.diffnav = new module.DiffNav(
                 {srcNode: Y.one('#review-diff'), lp_client: lp_client}
            );

        },

        tearDown: function () {},

        reply_previewdiffs: function() {
            // test helper to reply 'available_diffs' collection via mockio.
            var mockio = this.diffnav.get('lp_client').io_provider;
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
            };
            mockio.success({
                responseText: Y.JSON.stringify(preview_diffs),
                responseHeaders: {'Content-Type': 'application/json'}});
        },

        reply_diffcontent: function() {
            // test helper to reply 'diff' content via mockio.
            // it reuses the existing test template contents, but
            // empties the page before replying it.
            Y.one('.diff-content div div ul.horizontal').empty();
            var diff_content = Y.one('.diff-content').get('innerHTML');
            var mockio = this.diffnav.get('lp_client').io_provider;
            Y.one('.diff-content').empty();
            mockio.success({
                responseText: diff_content,
                responseHeaders: {'Content-Type': 'text/html'}});
        },

        test_diff_nav_feature_flag_disabled: function() {
            // When rendered with the corresponding feature-flag disabled,
            // Diff Navigator only updates the diff content with the latest
            // previewdiff and does not create the navigator (<select>),
            // does not fetch the inline comments nor render the
            // InlineToggle (show/hide inline comments) widget.
            LP.cache.inline_diff_comments = false;
            this.diffnav.render();
            mockio = this.diffnav.get('lp_client').io_provider;
            Y.Assert.areEqual(1, mockio.requests.length);
            Y.Assert.areSame(
                "/~foo/bar/foobr/+merge/1/++diff",
                mockio.last_request.url);
            this.reply_diffcontent();
            Y.Assert.isNull(this.diffnav.get('previewdiff_id'));
            Y.Assert.isNull(Y.one('.diff-content').one('#show-ic'));
        },

        test_diff_nav_rendering: function() {
            // When rendered the Diff Navigator fetches the available diffs
            // collection and builds the selector, fetches and displays
            // the diff contents for the most recent previewdiff and also
            // fetches and displays the related inline comments.
            this.diffnav.render();
            // diff-navigator section content is rendered based on the
            // preview_diffs API object.
            var mockio = this.diffnav.get('lp_client').io_provider;
            Y.Assert.areEqual(1, mockio.requests.length);
            Y.Assert.areSame(
                "/api/devel/~foo/bar/foobr/+merge/1/preview_diffs",
                mockio.last_request.url);
            this.reply_previewdiffs();
            // The selected preview_diff content is retrieved.
            Y.Assert.areEqual(2, mockio.requests.length);
            Y.Assert.areSame(
                "/~foo/bar/foobr/+merge/1/+preview-diff/101/+diff",
                mockio.last_request.url);
            this.reply_diffcontent();
            // The local (fake) setup_inline_comments function
            // was called with the selected diff_id value.
            Y.Assert.areEqual(101, this.inline_comments_requested_id);
            // Diff content is rendered/updated.
            var comment = Y.one(
                '.diff-content table tbody tr td').next()
            Y.Assert.areSame(
                 "foo bar", comment.get('text'));
            // The option corresponding to the current 'preview_diff'
            // is selected and contains the expected text (title and
            // formatted date_created).
            Y.Assert.areEqual(1, Y.one('select').get('selectedIndex'));
            // XXX cprov 20140226: test disabled due to ES4 lack of
            // ISO8601 support. Although the vast majority of production
            // clients run ES5.
            //Y.Assert.areEqual(
            //    'r1 into r1 on 2014-02-20',
            //    Y.one('select').get('options').item(1).get('text'));
        },

        test_diff_nav_changes: function() {
            // Changes on the DiffNav selector result in diff content
            // and inline comments updates.
            this.diffnav.render();
            this.reply_previewdiffs();
            this.reply_diffcontent();
            var mockio = this.diffnav.get('lp_client').io_provider;
            Y.Assert.areEqual(2, mockio.requests.length);

            Y.one('select').set('value', 202);
            Y.one('select').simulate('change');
            Y.Assert.areEqual(3, mockio.requests.length);
            Y.Assert.areSame(
                "/~foo/bar/foobr/+merge/1/+preview-diff/202/+diff",
                mockio.last_request.url);
            this.reply_diffcontent();
            Y.Assert.areEqual(202, this.diffnav.get('previewdiff_id'));
            Y.Assert.areEqual(202, this.inline_comments_requested_id);
        },

        test_diff_lineno_show_hide: function() {
            // NumberToggle widget is rendered as a checked checkbox.
            // Checking/Unchecking it show or hide the diff
            // line-numbers cells.
            var line_no_check = Y.one('.diff-content').one('#show-no');
            Y.Assert.isTrue(line_no_check.get('checked'));
            Y.Assert.areEqual(
                'table-cell', Y.one('td.line-no').getStyle('display'));
            line_no_check.set('checked', false);
            line_no_check.simulate('change');
            // XXX cprov 20140414: a tiny/empty wait seems to be
            // required for the DOM changes become accessible.
            this.wait(function() {}, 1);
            Y.Assert.areEqual(
                'none', Y.one('td.line-no').getStyle('display'));
            line_no_check.set('checked', true);
            line_no_check.simulate('change');
            this.wait(function() {}, 1);
            Y.Assert.areEqual(
                'block', Y.one('td.line-no').getStyle('display'));
        },

        test_diff_inline_show_hide: function() {
            // InlineCommentToggle widget is rendered as a checked
            // checkbox. Checking/Unchecking it show or hide all
            // rendered inline comments.
            var ic_check = Y.one('.diff-content').one('#show-ic');
            Y.Assert.isTrue(ic_check.get('checked'));
            // Render a draft comment for tests.
            module.create_row({'line_number': '1', 'text': 'inline'});
            Y.Assert.areEqual(
                'table-row', Y.one('.inline-comments').getStyle('display'));
            ic_check.set('checked', false);
            ic_check.simulate('change');
            this.wait(function() {}, 1);
            Y.Assert.areEqual(
                'none', Y.one('.inline-comments').getStyle('display'));
            ic_check.set('checked', true);
            ic_check.simulate('change');
            this.wait(function() {}, 1);
            Y.Assert.areEqual(
                'table-row', Y.one('.inline-comments').getStyle('display'));
        },

        test_diff_nav_scrollers: function() {
            // The Diff Navigator review comment *scrollers* are connected
            // upon widget rendering and when clicked trigger the diff
            // content update.
            this.diffnav.render();
            this.reply_previewdiffs();
            this.reply_diffcontent();
            var mockio = this.diffnav.get('lp_client').io_provider;
            Y.Assert.areEqual(2, mockio.requests.length);
            // We need to re-instrument the scroller in other to
            // instantly fire the 'end' event (which runs the code
            // that matters to us).
            scroller = Y.one('#scroll-two');
            scroller.on('click', function() {
                var rc = Y.lp.code.branchmergeproposal.reviewcomment;
                rc.window_scroll_anim.fire('end');
            });
            // Click the scroller results in a diff update.
            scroller.simulate('click');
            Y.Assert.areEqual(3, mockio.requests.length);
            Y.Assert.areSame(
                "/~foo/bar/foobr/+merge/1/+preview-diff/202/+diff",
                mockio.last_request.url);
            this.reply_diffcontent();
            Y.Assert.areEqual(202, this.diffnav.get('previewdiff_id'));
            Y.Assert.areEqual(202, this.inline_comments_requested_id);
            // If the scroller target diff is already displayed, the diff
            // content is not refreshed.
            scroller.simulate('click');
            Y.Assert.areEqual(3, mockio.requests.length);
        },

        test_update_on_new_comment: function() {
            // When a new comment is added to the page, it triggers
            // a Diff Navigator action to update the inline comments and
            // hook new inline-comment scroller links.
            this.diffnav.set('navigator', Y.one('select'));
            // Let's create add a new scroller to the page.
            var new_scroller = Y.Node.create(
                '<a id="scroll-three" class="inline-comment-scroller" ' +
                'href="" data-previewdiff-id="202">Another scroller</a>');
            Y.one('#scroll-two').insert(new_scroller, 'after');
            // and instrument the inline-comment updated function.
            var populated = false;
            module.populate_comments = function () {
                populated = true;
            };
            // Once called, update_on_new_comment() integrates the
            // just-added scroller and updates the inline comments.
            this.diffnav.update_on_new_comment();
            Y.Assert.isTrue(new_scroller.hasClass('js-action'));
            Y.Assert.isTrue(populated);
            // Instrument the new scroller, so it will instantly fire
            // the diff navigator hook and register the requested diff.
            new_scroller.on('click', function() {
                var rc = Y.lp.code.branchmergeproposal.reviewcomment;
                rc.window_scroll_anim.fire('end');
            });
            var called_pd_id = null;
            this.diffnav._showPreviewDiff = function (pd_id) {
                called_pd_id = pd_id;
            };
            // the new scroller works, it has requested and diff update
            // to the encoded data-previewdiff-id.
            new_scroller.simulate('click');
            Y.Assert.areEqual(202, called_pd_id);
        },

        test_diff_nav_failed_diff_content: function() {
            // An error message is presented when the Diff Navigator
            // fails to fetch the selected diff contents.
            this.diffnav.render();
            this.reply_previewdiffs();
            Y.one('select').set('value', 2);
            Y.one('select').simulate('change');
            var mockio = this.diffnav.get('lp_client').io_provider;
            mockio.failure();
            Y.Assert.areEqual(
                'Failed to fetch diff content.',
                Y.one('.diff-content').get('text'));
        },

        test_diff_nav_failed_available_diffs: function() {
            // An error message is presented with the Diff Navigator
            // fails to fetch the collection of available diffs.
            this.diffnav.render();
            var mockio = this.diffnav.get('lp_client').io_provider;
            mockio.failure();
            Y.Assert.areEqual(
                'Failed to fetch available diffs.',
                Y.one('.diff-navigator').get('text'));
        },

        test_status_indicators: function() {
            // Indicating progress with the spinner image.
            this.diffnav.set_status_updating();
            Y.Assert.areEqual(
                '/@@/spinner',
                Y.one('h2').one('img').getAttribute('src'));
            // Remove the spinner when the work is done.
            this.diffnav.cleanup_status();
            Y.Assert.areEqual(
                'Preview Diff',
                Y.one('h2').get('innerHTML'));
        }

    }));

}, '0.1', {
    requires: ['node-event-simulate', 'test', 'lp.testing.helpers',
               'console', 'lp.client', 'lp.testing.mockio', 'widget',
               'lp.code.branchmergeproposal.inlinecomments', 'lp.anim',
               'lp.code.branchmergeproposal.reviewcomment']
});
