/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
      }).use('event', 'lp.bugs.bugtask_index', 'lp.client', 'node',
             'lp.testing.mockio', 'test', 'widget-stack', 'console',
             function(Y) {


// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;
var module = Y.lp.bugs.bugtask_index;
var suite = new Y.Test.Suite("Async comment loading tests");

var comments_markup =
    "<div>This is a comment</div>" +
    "<div>So is this</div>" +
    "<div>So is this</div>" +
    "<div>And this, too.</div>";

suite.add(new Y.Test.Case({

    name: 'Basic async comment loading tests',

    setUp: function() {
        // Monkeypatch LP to avoid network traffic and to make
        // some things work as expected.
        Y.lp.client.Launchpad.prototype.named_post =
          function(url, func, config) {
            config.on.success();
          };
        LP = {
          'cache': {
            'bug': {
              self_link: "http://bugs.example.com/bugs/1234"
          }}};
        // Add some HTML to the page for us to use.
        this.comments_container = Y.Node.create(
            '<div id="comments-container"></div>');
        this.add_comment_form_container = Y.Node.create(
            '<div id="add-comment-form-container" class="hidden"></div>');
        Y.one('body').appendChild(this.comments_container);
        Y.one('body').appendChild(this.add_comment_form_container);
    },

    tearDown: function() {
        this.comments_container.remove();
        this.add_comment_form_container.remove();
    },

    /**
     * load_more_comments() calls the passed batch_commments_url of the
     * current bug task and loads more comments from it.
     */
    test_load_more_comments_loads_more_comments: function() {
        var mockio = new Y.lp.testing.mockio.MockIo();
        module.load_more_comments(
            '', this.comments_container, mockio);
        mockio.success({
            responseText: comments_markup,
            responseHeaders: {'Content-Type': 'application/xhtml'}
        });
        Assert.areEqual(
            '<div>' + comments_markup + '</div>',
            this.comments_container.get('innerHTML'));
    },

    /**
     * load_more_comments() will show the "add comment" form once all
     * the comments have loaded.
     */
    test_load_more_comments_shows_add_comment_form: function() {
        var add_comment_form_container = Y.one(
            '#add-comment-form-container');
        Assert.isTrue(add_comment_form_container.hasClass('hidden'));
        var mockio = new Y.lp.testing.mockio.MockIo();
        module.load_more_comments(
            '', this.comments_container, mockio);
        mockio.success({
            responseText: comments_markup,
            responseHeaders: {'Content-Type': 'application/xhtml'}
        });
        Assert.isFalse(add_comment_form_container.hasClass('hidden'));
    },

    /**
     * load_more_comments() will call itself recursively until there are
     * no more comments to load.
     */
    test_load_more_comments_is_recursive: function() {
        var next_batch_url_div =
            '<div id="next-batch-url">https://launchpad.dev/</div>';
        var more_comments_to_load_markup =
            '<div>Here, have a comment. There are more where this came' +
            'from</div>';
        var mockio = new Y.lp.testing.mockio.MockIo();
        module.load_more_comments(
            '', this.comments_container, mockio);
        mockio.success({
            responseText: next_batch_url_div + more_comments_to_load_markup,
            responseHeaders: {'Content-Type': 'application/xhtml'}
        });
        mockio.success({
            responseText: comments_markup,
            responseHeaders: {'Content-Type': 'application/xhtml'}
        });
        var expected_markup =
            '<div>' + more_comments_to_load_markup + '</div>' +
            '<div>' + comments_markup + '</div>';
        Assert.areEqual(
            expected_markup, this.comments_container.get('innerHTML'));
    },

}));

var handle_complete = function(data) {
    window.status = '::::' + JSON.stringify(data);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
