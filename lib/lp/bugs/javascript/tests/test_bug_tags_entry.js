YUI().use('lp.testing.runner', 'lp.testing.mockio', 'test', 'console',
          'lp.client', 'node-event-simulate', 'lp.bugs.bug_tags_entry',
    function(Y) {

    var module = Y.lp.bugs.bug_tags_entry;
    var suite = new Y.Test.Suite("Bug tags entry Tests");

    suite.add(new Y.Test.Case({
        name: 'Tags parsing',

        test_empty_string: function() {
            var tag_string = '';
            var results = module.parse_tags(tag_string);
            Y.ArrayAssert.itemsAreEqual([], results);
        },

        test_one_item: function() {
            var tag_string = 'cow';
            var results = module.parse_tags(tag_string);
            Y.ArrayAssert.itemsAreEqual(['cow'], results);
        },

        test_two_items: function() {
            var tag_string = 'cow pig';
            var results = module.parse_tags(tag_string);
            Y.ArrayAssert.itemsAreEqual(['cow', 'pig'], results);
        },

        test_spaces: function() {
            var tag_string = '   ';
            var results = module.parse_tags(tag_string);
            Y.ArrayAssert.itemsAreEqual([], results);
        },

        test_items_with_spaces: function() {
            var tag_string = ' cow pig  chicken  ';
            var results = module.parse_tags(tag_string);
            Y.ArrayAssert.itemsAreEqual(['cow', 'pig', 'chicken'], results);
        }

      }));

    Y.lp.testing.Runner.run(suite);
});
