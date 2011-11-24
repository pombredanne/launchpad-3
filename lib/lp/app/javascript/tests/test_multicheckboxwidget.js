/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'dom', 'event',
        'event-simulate', 'lazr.overlay', 'lazr.activator',
        'lp.client', 'lp.app.multicheckbox',
        function(Y) {

var suite = new Y.Test.Suite("lp.app.multicheckbox Tests");

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var rawnode = Y.Node.getDOMNode(widget.one(selector));
    Y.Event.simulate(rawnode, evtype, options);
}

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

var MockClient = function() {
    /* A mock to provide the result of a patch operation. */
};

MockClient.prototype = {
    'patch': function(uri, representation, config, headers) {
        var patch_content = new Y.lp.client.Entry();
        var html = Y.Node.create("<span/>");
        html.set('innerHTML', representation.multicheckboxtest);
        patch_content.set('lp_html', {'multicheckboxtest': html});
        config.on.success(patch_content);
    }
};

suite.add(new Y.Test.Case({
    name: "lp.app.multicheckbox",

    createWidget: function(header) {
      // Create a widget with some default data
      var config = {"empty_display_value": "None"};
      if (header !== 'None') {
          if (header === undefined) {
              header = 'Test multicheckbox widget:';
          }
        config.header = header;
      }

      var mock_client = new MockClient();
      this.widget = Y.lp.app.multicheckbox.addMultiCheckboxPatcher(
        [{"token": "0", "style": "font-weight: normal;", "checked": true,
            "name": "Item 0<foo/>", "value": "item1"},
        {"token": "1", "style": "font-weight: normal;", "checked": false,
            "name": "Item 1<foo/>", "value": "item2"}],
        'A test',
        '/~fred/+recipe/a-recipe',
        'multicheckboxtest',
        'default',
        'edit-test',
        config, mock_client);
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
        var header;
        this.createWidget(header='None');
        header = Y.one('.yui3-widget-hd');
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
        var x;
        for (x = 0; x < 2; x++) {
            var item = Y.one(
                  'input[id="field.multicheckboxtest.'+x+'][type=checkbox]');
            Y.Assert.areEqual(item.getAttribute('value'), x);
            Y.Assert.areEqual(item.get('checked'), x === 0);
        }
    },

    test_widget_has_correct_choice_text: function() {
        // Make sure the checkboxes are rendered with expected label text.
        this.createWidget();
        var x;
        for (x = 0; x < 2; x++) {
            var item = Y.one('label[for="field.multicheckboxtest.'+x+']');
            var txt = item.get('textContent');
            //remove any &nbsp in the text
            txt = txt.replace(/^[\s\xA0]+/g,'').replace(/[\s(&nbsp;)]+$/g,'');
            Y.Assert.areEqual(txt, 'Item '+ x + '<foo/>');
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
    },

    test_widget_content_from_patch_success: function() {
        // Test that when the user clicks "save" and the result comes back,
        // the DOM is correctly updated.
        this.createWidget();
        simulate(this.widget.get('boundingBox'), '#edit-test-save', 'click');
        var items = Y.one('[id="edit-test-items"]');
        var expected_content = items.get('textContent');
        Y.Assert.areEqual(expected_content, 'item1');
    }

}));

Y.lp.testing.Runner.run(suite);

});
