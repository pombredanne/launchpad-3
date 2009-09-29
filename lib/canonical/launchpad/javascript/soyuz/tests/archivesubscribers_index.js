/* Copyright 2009 Canonical Ltd.  This software is licensed under the
   GNU Affero General Public License version 3 (see the file LICENSE). */

YUI({
    base: '../../../icing/yui/current/build/',
    filter: 'raw',
    combine: false
    }).use(
        'yuitest', 'console', 'soyuz.archivesubscribers_index', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("ArchiveSubscriber Tests");

suite.add(new Y.Test.Case({

    name: 'add-subscriber',

    setUp: function() {
        this.add_subscriber_placeholder = Y.get(
            '#add-subscriber-placeholder');
        this.archive_subscribers_table_body = Y.get(
            '#archive-subscribers').query('tbody');
        this.error_div = Y.get('#errors');
        this.subscribers_div = Y.get('#subscribers');


        // Ensure there are no errors displayed.
        this.error_div.set('innerHTML', '');

        // Ensure the add subscriber place-holder is empty.
        this.add_subscriber_placeholder.set('innerHTML', '');

        // Ensure the table has the correct structure.
        this.archive_subscribers_table_body.set(
            'innerHTML', [
                '<tr class="add-subscriber">',
                '<td>New 1</td>',
                '<td>New 2</td>',
                '<td>New 3</td>',
                '<td>Add</td>',
                '</tr>',
                '<tr>',
                '<td>Existing 1</td>',
                '<td>Existing 2</td>',
                '<td>Existing 3</td>',
                '<td>Edit</td>',
                '</tr>'
                ].join(''));

        this.add_subscriber_row = Y.get(
            '#archive-subscribers .add-subscriber');
    },

    test_add_row_displayed_by_default: function() {
        Assert.areEqual(
            'table-row', this.add_subscriber_row.getStyle('display'),
            'The add subscriber row degrades to display without js.');
    },

    test_subscribers_displayed_by_default: function() {
        Assert.areEqual(
            'block', this.subscribers_div.getStyle('display'),
            'The subscribers section is displayed by default without js.');
    },

    test_add_row_hidden_after_setup: function() {
        Y.soyuz.setup_archivesubscribers_index();
        Assert.areEqual(
            'none', this.add_subscriber_row.getStyle('display'),
            'The add subscriber row is hidden during setup.');
    },

    test_subscribers_section_displayed_after_setup: function() {
        Y.soyuz.setup_archivesubscribers_index();
        Assert.areEqual(
            'block', this.subscribers_div.getStyle('display'),
            'The subscribers div normally remains displayed after setup.');
    },

    test_subscribers_section_hidden_when_no_subscribers: function() {
        // Add a paragraph with the no-subscribers id.
        this.error_div.set('innerHTML', '<p id="no-subscribers">blah</p>');
        Y.soyuz.setup_archivesubscribers_index();
        Assert.areEqual(
            'none', this.subscribers_div.getStyle('display'),
            'The subscribers div is hidden when no subscribers yet.');
    },

    test_add_row_displayed_when_errors_present: function() {
        // Add an error paragraph.
        this.error_div.set('innerHTML', '<p class="error message">Blah</p>');
        Y.soyuz.setup_archivesubscribers_index();
        Assert.areEqual(
            'table-row', this.add_subscriber_row.getStyle('display'),
            'The add subscriber row is displayed if there are errors ' +
            'present.');
    },

    test_add_access_link_added_after_setup: function() {
        Y.soyuz.setup_archivesubscribers_index();
        Assert.areEqual(
            '<a class="js-action sprite add" href="#">Add access</a>',
            this.add_subscriber_placeholder.get('innerHTML'),
            "The 'Add access' link is created during setup.")
    },

    test_click_add_access_displays_add_row: function() {
        Y.soyuz.setup_archivesubscribers_index();
        var link_node = this.add_subscriber_placeholder.query('a');
        Assert.areEqual(
            'Add access', link_node.get('innerHTML'));

        Y.Event.simulate(Y.Node.getDOMNode(link_node), 'click');

        Assert.areEqual(
            'table-row', this.add_subscriber_row.getStyle('display'),
            "The add subscriber row is displayed after clicking " +
            "'Add access'");
    }
}));

Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
