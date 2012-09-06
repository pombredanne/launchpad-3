/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI().use('lp.testing.runner', 'test', 'console', 'node-event-simulate',
    'lp.translations.poexport', function(Y) {

var suite = new Y.Test.Suite("export Tests");
var namespace = Y.lp.translations.poexport;


suite.add(new Y.Test.Case({
    name: 'PO export',

    setUp: function() {
        fixture = Y.one("#fixture");
        var template = Y.one('#pofile-export').getContent();
        var test_node = Y.Node.create(template);
        fixture.append(test_node);
    },

    tearDown: function() {
        Y.one("#fixture").empty();
    },

    test_initialize_pofile_export_page_without_pochanged: function() {
        // The change handler was not added if the checbox does not exist.
        var pochanged = Y.one('#div_pochanged');
        pochanged.get('parentNode').removeChild(pochanged);
        handler_added = namespace.initialize_pofile_export_page();
        Y.Assert.isFalse(handler_added);
    },

    test_initialize_pofile_export_page_with_pochanged_default_po: function() {
        // The checkbox is enabled when PO is selected.
        handler_added = namespace.initialize_pofile_export_page();
        Y.Assert.isTrue(handler_added);
        Y.Assert.isTrue(
            Y.one('#po-format-only').hasClass('hidden'));
        Y.Assert.isFalse(
            Y.one('#div_pochanged span').hasClass('disabledpochanged'));
        Y.Assert.isFalse(
            Y.one('#div_pochanged input').get('disabled'));
    },

    test_initialize_pofile_export_page_with_pochanged_mo_selected: function() {
        // The checkbox is disabled when MO is selected.
        handler_added = namespace.initialize_pofile_export_page();
        Y.Assert.isTrue(handler_added);
        var formatlist = Y.one('#div_format select');
        formatlist.set('selectedIndex', 1);
        formatlist.simulate('change');
        Y.Assert.isTrue(
            Y.one('#div_pochanged span').hasClass('disabledpochanged'));
        Y.Assert.isTrue(
            Y.one('#div_pochanged input').get('disabled'));
    }
}));

Y.lp.testing.Runner.run(suite);
});
