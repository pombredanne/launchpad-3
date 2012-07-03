/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.app.comment.test', function (Y) {

    var tests = Y.namespace('lp.app.comment.test');
    tests.suite = new Y.Test.Suite('lp.app.comment Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.app.comment_tests',

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.app.comment,
                "Could not locate the lp.app.comment module");
        },

        test_init: function () {
            var comment = new Y.lp.app.comment.Comment();
            Y.Assert.isObject(comment.comment_input);
            Y.Assert.isObject(comment.submit_button);
            Y.Assert.isTrue(
                comment.progress_message.hasClass('update-in-progress-message'));
        },

        test_validation: function () {
            var comment = new Y.lp.app.comment.Comment();
            comment.comment_input.set('value', 'foo ');
            Y.Assert.isTrue(comment.validate());

            comment.comment_input.set('value', '    ');
            Y.Assert.isFalse(comment.validate());
        },

        test_post_comment: function () {
            window.LP = {
                cache: {
                    bug: { self_link: '/bug/1/' }
                }
            };
            var mock_client = new Y.lp.testing.helpers.LPClient();
            var comment = new Y.lp.app.comment.Comment(
                { lp_client:  mock_client });
            var no_op = function () {};
            mock_client.named_post.args = [];
            comment.post_comment(no_op);
            Y.Assert.areEqual(
                mock_client.received[0][1][0],
                '/bug/1/');
            Y.Assert.areEqual(
                mock_client.received[0][1][1],
                'newMessage');
        }
    }));

}, '0.1', {'requires': ['test', 'lp.testing.helpers', 'console',
                        'lp.app.comment']});
