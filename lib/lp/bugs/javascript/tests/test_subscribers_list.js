YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.subscribers_list',
           'node-event-simulate',
           function(Y) {

var suite = new Y.Test.Suite("lp.bugs.subscribers_list Tests");
var module = Y.lp.bugs.subscribers_list;

/**
 * Test resetting of the subscribers list.
 */
suite.add(new Y.Test.Case({
    name: 'Resetting subscribers list',

    setUp: function() {
        this.root = Y.Node.create('<div></div>');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_no_subscribers: function() {
        // There are no subscribers left in the subscribers_list
        // (iow, subscribers_links is empty).
        var subscribers_links = Y.Node.create('<div></div>')
            .set('id', 'subscribers-links');
        var subscribers_list = Y.Node.create('<div></div>');
        subscribers_list.appendChild(subscribers_links);
        this.root.appendChild(subscribers_list);

        // Resetting the list adds a 'None' div to the
        // subscribers_list (and not to the subscriber_links).
        module.reset();
        var none_node = subscribers_list.one('#none-subscribers');
        Y.Assert.isNotNull(none_node);
        Y.Assert.areEqual('None', none_node.get('innerHTML'));
        Y.Assert.areEqual(subscribers_list,
                          none_node.get('parentNode'));

    },

    test_subscribers: function() {
        // When there is at least one subscriber, nothing
        // happens when reset() is called.
        var subscribers_links = Y.Node.create('<div></div>')
            .set('id', 'subscribers-links');
        subscribers_links.appendChild(
            Y.Node.create('<div>Subscriber</div>'));
        var subscribers_list = Y.Node.create('<div></div>');
        subscribers_list.appendChild(subscribers_links);
        this.root.appendChild(subscribers_list);

        // Resetting the list is a no-op.
        module.reset();
        var none_node = subscribers_list.one('#none-subscribers');
        Y.Assert.isNull(none_node);
    },


    test_empty_duplicates: function() {
        // There are no subscribers among the duplicate subscribers.
        var dupe_subscribers = Y.Node.create('<div></div>')
            .set('id', 'subscribers-from-duplicates');
        this.root.appendChild(dupe_subscribers);

        // There must always be subscribers-links node for reset() to work.
        var subscribers_links = Y.Node.create('<div></div>')
            .set('id', 'subscribers-links');
        this.root.appendChild(subscribers_links);

        // Resetting the list removes the entire duplicate subscribers node.
        module.reset();
        var dupes_node = Y.one('#subscribers-from-duplicates');
        Y.Assert.isNull(dupes_node);

    },

    test_duplicates: function() {
        // There are subscribers among the duplicate subscribers,
        // and nothing changes.
        var dupe_subscribers = Y.Node.create('<div></div>')
            .set('id', 'subscribers-from-duplicates');
        dupe_subscribers.appendChild(
            Y.Node.create('<div>Subscriber</div>'));
        this.root.appendChild(dupe_subscribers);

        // There must always be subscribers-links node for reset() to work.
        var subscribers_links = Y.Node.create('<div></div>')
            .set('id', 'subscribers-links');
        this.root.appendChild(subscribers_links);

        // Resetting the list does nothing.
        module.reset();

        // The list is still there.
        var dupes_node = this.root.one('#subscribers-from-duplicates');
        Y.Assert.isNotNull(dupes_node);
        Y.Assert.areEqual(1, dupes_node.all('div').size());
    }
}));


var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
