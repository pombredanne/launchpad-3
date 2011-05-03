YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false,
    }).use('test', 'console', 'lp.answers.question_spam', function(Y) {

    var suite = new Y.Test.Suite("lp.answers.question_spam Tests");

    suite.add(new Y.Test.Case({
        name: 'question_spam',

        setUp: function() {
            this.comment = Y.one('.boardComment');
            this.spam_link = Y.one('#mark-spam');
            },

        test_mark_as_spam: function () {
            // this should fail
            Y.Assert.isTrue(false);
            },
        
        test_mark_as_not_spam: function () {
            // this should fail
            Y.Assert.isTrue(false);
            },

        }));

    // Lock, stock, and two smoking barrels.
    Y.Test.Runner.add(suite);
    
    var handle_complete = function(data) {
        status_node = Y.Node.create(
            '<p id="complete">Test status: complete</p>');
        Y.one('body').appendChild(status_node);
        };
    Y.Test.Runner.on('complete', handle_complete);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});

