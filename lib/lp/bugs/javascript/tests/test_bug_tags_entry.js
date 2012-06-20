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

    suite.add(new Y.Test.Case({
        name: 'Actions',

        setUp: function() {
            this.fixture = Y.one("#fixture");
            var template = Y.one('#bug-tag-form').getContent();
            this.fixture.append(template);
            this.edit_tags_trigger = Y.one('#edit-tags-trigger');
            this.add_tags_trigger = Y.one('#add-tags-trigger');
            this.tag_list_span = Y.one('#tag-list');
            this.tag_input = Y.one('#tag-input');
            this.ok_button = Y.one('#edit-tags-ok');
            this.cancel_button = Y.one('#edit-tags-cancel');
            window.LP = {
                links: {me : "/~user"},
                cache: {}
                };
        },

        tearDown: function () {
            if (this.fixture !== null) {
                this.fixture.empty();
            }
            delete this.fixture;
            delete window.LP;
        },

        test_edit: function () {
            module.setup_tag_entry(['project-tag']);
            this.edit_tags_trigger.simulate('click');
            Y.Assert.areEqual(
                'none', this.edit_tags_trigger.getStyle('display'));
        }
    }));

    Y.lp.testing.Runner.run(suite);
});
