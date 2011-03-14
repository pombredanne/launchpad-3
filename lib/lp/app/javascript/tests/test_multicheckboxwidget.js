/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'dom', 'lazr.overlay', 'lazr.activator',
                'lp.client', 'lp.app.multicheckbox', function(Y) {

var suite = new Y.Test.Suite("lp.app.multicheckbox Tests");

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        bb.get('parentNode').removeChild(bb);
    }
    // Kill the widget itself.
    widget.destroy();
}

suite.add(new Y.Test.Case({
    name: "lp.app.multicheckbox",

    createWidget: function(header) {
      // Create a widget with some default data
      var config = {"empty_display_value": "None"};
      if( header != 'None' ) {
        if( header == null )
            header = 'Test multicheckbox widget:';
        config['header'] = header;
      }
      this.widget = Y.lp.app.multicheckbox.addMultiCheckboxPatcher(
        [{"token": "0", "style": "font-weight: normal;", "checked": true,
            "name": "Item 0", "value": "item1"},
        {"token": "1", "style": "font-weight: normal;", "checked": false,
            "name": "Item 1", "value": "item2"}],
        'A test',
        '/~fred/+recipe/a-recipe',
        'multicheckboxtest',
        'reference',
        'edit-test',
        config)
    },

    tearDown: function() {
        cleanup_widget(this.widget);
    },

    test_widget_can_be_instantiated: function() {
        this.createWidget();
        Y.Assert.isInstanceOf(
            Y.lazr.PrettyOverlay, this.widget,
            "Widget failed to be instantiated");
    },

    test_header_value: function() {
        // Check the header text value.
        this.createWidget();
        var header = Y.one('.yui3-widget-hd');
        Y.Assert.areEqual(
            header.get('innerHTML'), '<h2>Test multicheckbox widget:</h2>');
    },

    test_default_header_value: function() {
        // Check the default header text value.
        this.createWidget(header='None');
        var header = Y.one('.yui3-widget-hd');
        Y.Assert.areEqual(
            header.get('innerHTML'), '<h2>Choose an item.</h2>');
    },

    test_help_text_value: function() {
        // Check the help text value.
        this.createWidget();
        var header = Y.one('.yui3-widget-bd p.formHelp');
        Y.Assert.areEqual(
            header.get('innerHTML'), 'A test');
    },

    test_widget_has_correct_choice_data: function() {
        // Make sure the checkboxes are rendered with expected data values..
        this.createWidget();
        for( var x=0; x<2; x++ ) {
            var item = Y.one(
                  'input[id="field.multicheckboxtest.'+x+'][type=checkbox]');
            Y.Assert.areEqual(item.getAttribute('value'), x);
            Y.Assert.areEqual(item.get('checked'), x==0);
        }
    },

    test_widget_has_correct_choice_text: function() {
        // Make sure the checkboxes are rendered with expected label text.
        this.createWidget();
        for( var x=0; x<2; x++ ) {
            var item = Y.one('label[for="field.multicheckboxtest.'+x+']');
            var txt = item.get('textContent');
            //remove any &nbsp in the text
            txt = txt.replace(/^[\s\xA0]+/g,'').replace(/[\s(&nbsp;)]+$/g,'');
            Y.Assert.areEqual(txt, 'Item '+ x);
        }
    },

    test_getSelectedItems: function() {
        // Test that getSelectedItems returns the correct values.
        this.createWidget();
        var items = Y.one('[id="multicheckboxtest.items"]');
        var mapping = {0: 'Item0', 1: 'Item1'};
        var selected = Y.lp.app.multicheckbox.getSelectedItems(
                                    items, mapping, '');
        Y.ArrayAssert.itemsAreEqual(['Item0'], selected);
    },

    test_marshall_references: function() {
        // Test that getSelectedItems returns the correct values for reference
        // values which are links to domain objects.
        this.createWidget();
        var items = Y.one('[id="multicheckboxtest.items"]');
        var mapping = {0: '/ubuntu/Item0', 1: '/ubuntu/Item1'};
        var selected = Y.lp.app.multicheckbox.getSelectedItems(
                                    items, mapping, 'reference');
        var item_value = Y.lp.client.normalize_uri(selected[0]);
        var link = Y.lp.client.get_absolute_uri(item_value);
        Y.ArrayAssert.itemsAreEqual([link], selected);
    }

}));

// Lock, stock, and two smoking barrels.
var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yui_console = new Y.Console({
    newestOnTop: false
});
yui_console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
