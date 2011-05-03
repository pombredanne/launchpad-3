YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false,
    }).use('test', 'console', 'node', 'node-event-simulate',
           'lp.answers.question_spam', function(Y) {

    var suite = new Y.Test.Suite("lp.answers.question_spam Tests");

    suite.add(new Y.Test.Case({
        name: 'question_spam',

        test_mark_as_spam: function () {
            comment = Y.one('.boardComment');
            spam_link = Y.one('#mark-spam');
            spam_link.simulate('click');
            Y.Assert.isTrue(comment.hasClass('adminHiddenComment'));
            },
        
        test_mark_as_not_spam: function () {
            spam = Y.one('#spam');
            comment = spam.one('.boardComment');
            spam_link = spam.one('#mark-spam');
            Y.Assert.isFalse(comment.hasClass('adminHiddenComment'));
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

