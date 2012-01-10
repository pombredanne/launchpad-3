/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.foldable.test', function (Y) {

    var test_foldable = Y.namespace('lp.foldable.test');
    var suite = new Y.Test.Suite('Foldable Tests');

    var quote_comment = ['<p>Mister X wrote:<br />',
        '<span class="foldable-quoted">',
        '&gt; This is a quoted line<br />',
        '</span>',
        'This is a reply to the line above.<br />',
        'This is a continuation line.</p>'].join('');

    var multiple_quoted_comment = [
        '<p>Attribution line<br />',
        '<span class="foldable-quoted">',
        '&gt; First line in the first paragraph.<br />',
        '&gt; Second line in the first paragraph.<br />',
        '&gt;<br />',
        '&gt; First line in the second paragraph.<br />',
        '&gt; Second line in the second paragraph.<br />',
        '&gt;<br />',
        '&gt; First line in the third paragraph.<br />',
        '&gt; Second line in the third paragraph.',
        '&gt; First line in the third paragraph.<br />',
        '&gt; Second line in the third paragraph.',
        '&gt; First line in the third paragraph.<br />',
        '&gt; Second line in the third paragraph.',
        '&gt; First line in the third paragraph.<br />',
        '&gt; Second line in the third paragraph.',
        '&gt; First line in the third paragraph.<br />',
        '&gt; Second line in the third paragraph.',
        '&gt; First line in the third paragraph.<br />',
        '&gt; Second line in the third paragraph.',
        '&gt; First line in the third paragraph.<br />',
        '&gt; Second line in the third paragraph.',
        '</span></p>'
    ];

    var foldable_comment = [
        '<p><span class="foldable" style="display: none; "><br>',
        '-----BEGIN PGP SIGNED MESSAGE-----<br>',
        'Hash: SHA1',
        '</span></p>'
    ].join('');

    suite.add(new Y.Test.Case({

        name: 'foldable_tests',

        _add_comment: function (comment) {
            var cnode = Y.Node.create('<div/>');
            cnode.set('innerHTML', comment);
            Y.one('#target').appendChild(cnode);
        },

        tearDown: function () {
            Y.one('#target').setContent('');
        },

        test_namespace_exists: function () {
            Y.Assert.isObject(Y.lp.app.foldable,
                'Foldable should be found');
        },

        test_inserts_ellipsis: function () {
            this._add_comment(multiple_quoted_comment);
            Y.lp.app.foldable.init();

            Y.Assert.isObject(Y.one('a'));
            Y.Assert.areSame('[...]', Y.one('a').getContent());
        },

        test_hides_quote: function () {
            this._add_comment(multiple_quoted_comment);
            Y.lp.app.foldable.init();
            var quote = Y.one('.foldable-quoted');
            Y.Assert.areSame(quote.getStyle('display'), 'none');
        },

        test_doesnt_hide_short: function () {
            this._add_comment(quote_comment);
            Y.lp.app.foldable.init();
            Y.Assert.isNull(Y.one('a'));

            var quote = Y.one('.foldable-quoted');
            Y.Assert.areSame(quote.getStyle('display'), 'inline');
        },

        test_clicking_link_shows: function () {
            this._add_comment(multiple_quoted_comment);
            Y.lp.app.foldable.init();

            var link = Y.one('a');
            link.simulate('click');

            var quote = Y.one('.foldable-quoted');
            Y.Assert.areSame(quote.getStyle('display'), 'inline');

            // and make sure that if clicked again it hides
            link.simulate('click');
            Y.Assert.areSame(quote.getStyle('display'), 'none');
        },

        test_foldable: function () {
            this._add_comment(foldable_comment);
            Y.lp.app.foldable.init();
            var link = Y.one('a');
            link.simulate('click');

            var quote = Y.one('.foldable');
            Y.Assert.areSame(quote.getStyle('display'), 'inline');

            // and make sure that if clicked again it hides
            link.simulate('click');
            Y.Assert.areSame(quote.getStyle('display'), 'none');
        }
    }));

    test_foldable.suite = suite;

}, '0.1', {
    requires: ['test', 'node-event-simulate', 'node', 'lp.app.foldable']
});
