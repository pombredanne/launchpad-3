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
                cache: {
                    bug: {
                        resource_type_link: 'Bug',
                        self_link: '/bug/1',
                        tags: ['project-tag']}
                    }
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
            Y.Assert.isTrue(this.tag_list_span.hasClass('hidden'));
            Y.Assert.isTrue(this.edit_tags_trigger.hasClass('hidden'));
            Y.Assert.isFalse(this.tag_input.hasClass('hidden'));
            Y.Assert.isFalse(this.ok_button.hasClass('hidden'));
            Y.Assert.isFalse(this.cancel_button.hasClass('hidden'));
        },

        test_cancel: function () {
            module.setup_tag_entry(['project-tag']);
            this.edit_tags_trigger.simulate('click');
            this.cancel_button.simulate('click');
            Y.Assert.isFalse(this.tag_list_span.hasClass('hidden'));
            Y.Assert.isFalse(this.edit_tags_trigger.hasClass('hidden'));
            Y.Assert.isTrue(this.tag_input.hasClass('hidden'));
            Y.Assert.isTrue(this.ok_button.hasClass('hidden'));
            Y.Assert.isTrue(this.cancel_button.hasClass('hidden'));
        },

        test_save_tags: function () {
            module.setup_tag_entry(['project-tag']);
            this.edit_tags_trigger.simulate('click');
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.lp_config = {io_provider: mockio};
            this.ok_button.simulate('click');
            Y.Assert.areEqual(
                '/api/devel/bug/1', mockio.last_request.url);
            mockio.success({
                responseText: Y.JSON.stringify({
                    resource_type_link: 'Bug',
                    self_link: '/bug/1',
                    tags: ['project-tag']}),
                responseHeaders: {'Content-Type': 'application/json'}});
            Y.Assert.isFalse(this.tag_list_span.hasClass('hidden'));
            Y.Assert.isFalse(this.edit_tags_trigger.hasClass('hidden'));
            Y.Assert.isTrue(this.tag_input.hasClass('hidden'));
            Y.Assert.isTrue(this.ok_button.hasClass('hidden'));
            Y.Assert.isTrue(this.cancel_button.hasClass('hidden'));
        }
    }));

    Y.lp.testing.Runner.run(suite);
});
