/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.editor',
          'lp.app.formwidgets.resizing_textarea', 'event', 'event-simulate',
          'plugin', function(Y) {

var SAMPLE_HTML = "                                                                           \
 <h1>Single-line editing</h1>                                                                 \
  <div id='editable_single_text'>                                                             \
    <span id='single_text' class='yui3-editable_text-text'>Some editable inline text.</span>  \
    <button id='single_edit' class='yui3-editable_text-trigger'>Edit this</button>            \
  </div>                                                                                      \
  <hr />                                                                                      \
  <h1>Multi-line editing</h1>                                                                 \
  <div id='editable_multi_text'>                                                              \
    <button id='multi_edit' class='yui3-editable_text-trigger'>Edit this</button>             \
    <span id='multi_text' class='yui3-editable_text-text'>                                    \
      <p>Some editable multi-line text.</p></span>                                            \
  </div>                                                                                      \
";

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

/* Helper to stamp a Node with an ID attribute.  Needed for YUI 2.X
 * testing, which is heavily ID-based.
 *
 * Returns the node's 'id' attribute.
 */
function id_for(node) {
    if (!node.getAttribute('id')) {
        var id = Y.stamp(node);
        node.setAttribute('id', id);
    }
    return node.getAttribute('id');
}

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(selector, evtype) {
    var rawnode = Y.Node.getDOMNode(Y.one(selector));
    Y.Event.simulate(rawnode, evtype);
}

/* Helper function that creates a new editor instance. */
function make_editor(cfg) {
    return new Y.InlineEditor(cfg);
}

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        if (bb && Y.Node.getDOMNode(bb)) {
            var parentNode = bb.get('parentNode');
            if (parentNode && Y.Node.getDOMNode(parentNode)) {
                parentNode.removeChild(bb);
            }
        }
    }
    // Kill the widget itself.
    widget.destroy();
}

function setup_sample_html() {
    if (! Y.one("#scaffolding")) {
        Y.one(document.body).appendChild(
            Y.Node.create("<div id='scaffolding'></div>"));
    }

    Y.one("#scaffolding").set("innerHTML", SAMPLE_HTML);
}

function make_editable_text(cfg) {
    // For the editor
    // TODO: fix this ugly hack
    var defaults = {
        contentBox: '#editable_single_text',
        boundingBox: '#inline-edit-container'
    };
    return new Y.EditableText(Y.merge(defaults, cfg));
}

// Helper: convert size specification like "120px" to a number (in casu, 120).
var strip_px = /px$/;
function parse_size(size) {
    return parseInt(size.replace(strip_px, ''), 10);
}

var suite = new Y.Test.Suite("Inline Editor Tests");

suite.add(new Y.Test.Case({

    name: 'inline_editor_basics',

    setUp: function() {
        this.editor = make_editor();
    },

    tearDown: function() {
        cleanup_widget(this.editor);
    },

    test_input_value_set_during_sync: function() {
        /* The input element's value should be set during the syncUI()
         * call.
         */
        var ed = this.editor,
            desired_value = 'x';

        Assert.areNotEqual(
            desired_value,
            ed.get('value'),
            "Sanity check: the editor's value shouldn't equal our " +
            "desired value.");
        Assert.isFalse(
            ed.get('rendered'),
            "Sanity check: the widget shouldn't be rendered yet.");

        ed.set('value', desired_value);
        ed.render();
        Assert.areEqual(
            desired_value,
            ed.get('input_field').get('value'),
            "The editor's input field's value should have been set.");
    },

    test_getInput_method: function() {
        this.editor.render();
        Assert.areEqual(
            this.editor.get('input_field').get('value'),
            this.editor.getInput(),
            "The getInput() method should return the same value as " +
            "the editor's input field's current value.");
    },

    test_validate_values: function() {
        Assert.isFalse(this.editor.get('accept_empty'),
            "The editor shouldn't accept empty values by default.");

        var prev = this.editor.get('value');
        this.editor.set('value', null);
        Assert.areEqual(
            prev,
            this.editor.get('value'),
            "The editor's value should not have changed.");

        this.editor.set('value', '');
        Assert.areEqual(
            prev,
            this.editor.get('value'),
            "The editor should not accept the empty string as a " +
            "value if 'accept_empty' is false.");

        /* The control can be asked to accept empty values. */
        this.editor.set('accept_empty', true);
        this.editor.set('value', '');
        Assert.areEqual(
            '',
            this.editor.get('value'),
            "The editor should have accepted the empty string as a " +
            "valid value if 'accept_empty' is true.");
    },

    test_validate_empty_editor_input: function() {
        var ed = this.editor;

        // A helper to catch the 'save' event.
        var got_save = false;
        var after_save = function(ev) { got_save = true; };
        ed.after('ieditor:save', after_save);

        ed.render();

        Assert.isFalse(ed.hasErrors(),
            "Sanity check: the editor shouldn't be displaying any " +
            "errors.");
        Assert.isFalse(ed.get('accept_empty'),
            "Sanity check: the editor shouldn't accept empty inputs.");

        ed.get('input_field').set('value', '');
        ed.save();

        Assert.isTrue(ed.hasErrors(),
            "The editor should be displaying an error after the " +
            "trying to save an empty input.");
        Assert.isFalse(got_save,
            "The editor should not have fired a 'save' event.");
    },

    test_set_and_clear_error_message: function() {
        this.editor.render();

        var ed       = this.editor,
            edisplay = ed.get('error_message'),
            c_hidden   = 'yui3-ieditor-errors-hidden';

        Assert.isNotNull(
            edisplay,
            "The editor should have a valid error display node.");

        Assert.isTrue(
            edisplay.hasClass(c_hidden),
            "The error display should start out hidden.");
        Assert.isFalse(
            ed.get("in_error"),
            "The editor's 'in_error' attribute should not be set.");

        var msg = "An error has occured.";
        ed.showError(msg);

        Assert.areEqual(
            msg,
            edisplay.get('text'),
            "The error display's text should be set.");
        Assert.isFalse(
            edisplay.hasClass(c_hidden),
            "The error display should be visible when an error is set.");
        Assert.isTrue(
            ed.hasErrors(),
            "The editor .hasErrors() method should return true if " +
            "there are errors being displayed.");
        Assert.isTrue(
            ed.get("in_error"),
            "The editor's 'in_error' attribute should be set.");

        ed.clearErrors();
        Assert.isTrue(
            edisplay.hasClass(c_hidden),
            "The error display should be hidden when the error " +
            "is cleared.");
        Assert.isFalse(
            ed.hasErrors(),
            "The editor .hasErrors() method should return false " +
            "if there are no errors being displayed.");
    },

    test_save_input_to_editor: function() {
        var expected_value = 'abc',
            ed = this.editor;

        Assert.areNotEqual(
            expected_value,
            ed.get('value'),
            "Sanity check");

        ed.render();
        ed.get('input_field').set('value', expected_value);
        ed.save();

        Assert.areEqual(
            expected_value,
            ed.get('value'),
            "The value of the editor's input field should have been " +
            "saved to the editor's 'value' attribute.");
    },

    test_focus_method_focuses_editor_input: function() {
        this.editor.render();

        var input = this.editor.get('input_field'),
            test = this,
            focused = false;

        Y.on('focus', function() {
            focused = true;
        }, input);

        this.editor.focus();

        Assert.isTrue(focused,
            "The editor's input field should have received focus " +
            "after calling the editor's focus method.");
    },

    test_input_receives_focus_after_editor_errors: function() {
        this.editor.render();

        var ed = this.editor,
            input = this.editor.get('input_field'),
            got_focus = false;

        Assert.isFalse(
            ed.get('in_error'),
            "Sanity check: the editor should be clear of errors.");
        Assert.isFalse(
            ed.get('accept_empty'),
            "Sanity check: the editor should not accept empty " +
            "values.");

        // Force an error by setting the editor's input to the
        // empty string.
        input.set('value', '');

        var test = this;
        // Add our focus event listener.
        Y.on('focus', function() {
            got_focus = true;
        }, input);

        ed.save();
        Assert.isTrue(
            ed.get('in_error'),
            "Sanity check: the editor should be in an error state " +
            "after saving an empty value.");

        Assert.isTrue(
            got_focus,
            "The editor's input field should have the current " +
            "focus.");
    },

    test_widget_has_a_disabled_tabindex_when_focused: function() {
        // The tabindex attribute appears when the widget is focused.
        this.editor.render();
        this.editor.focus();

        // Be aware that in IE, get('tabIndex') and getAttribute('tabIndex')
        // return different values when set to -1. This is due to YUI's
        // getAttribute() calling dom_node.getAttribute('tabIndex', 2), which
        // is an IE extension.
        // http://msdn.microsoft.com/en-us/library/ms536429%28VS.85%29.aspx
        Assert.areEqual(
            -1,
            this.editor.get('boundingBox').get('tabIndex'),
            "The widget should have a tabindex of -1 (disabled).");
    },

    test_enter_key_saves_input: function() {
        this.editor.render();

        var ed = this.editor,
            input_element = Y.Node.getDOMNode(
                this.editor.get('input_field'));

        input_element.value = 'abc';

        // A helper to flag the 'save' event.
        var saved = false;
        function saveCheck(e) {
            saved = true;
        }

        ed.after('ieditor:save', saveCheck, this);

        // Simulate an 'Enter' key event in the editor's input field.
        Y.Event.simulate(input_element, "keydown", { keyCode: 13 });

        Assert.isFalse(ed.hasErrors());
        Assert.isTrue(saved,
            "Pressing the 'Enter' key inside the editor's input field " +
            "should save the input.");
    },

    test_enter_key_ignored_in_multiline: function() {
        this.editor.set('multiline', true);
        this.editor.render();

        var ed = this.editor;
        var input_element = Y.Node.getDOMNode(this.editor.get('input_field'));

        input_element.value = 'abc';

        // A helper to flag the 'save' event.
        var saved = false;
        function saveCheck(e) {
            saved = true;
        }

        ed.after('ieditor:save', saveCheck, this);

        // Simulate an 'Enter' key event in the editor's input field.
        Y.Event.simulate(input_element, "keydown", { keyCode: 13 });

        // Restore to previous state.
        this.editor.set('multiline', false);

        Assert.isFalse(ed.hasErrors());
        Assert.isFalse(saved,
            "Pressing the 'Enter' key in multiline mode " +
            "should not trigger a save.");
    },

    test_input_should_be_trimmed_of_whitespace: function() {
        this.editor.render();

        var input = this.editor.get('input_field');

        // Set a whitespace value as the input.
        input.set('value', '  ');

        this.editor.save();

        Assert.isTrue(
            this.editor.hasErrors(),
            "The editor should be displaying an error after trying to " +
            "save a whitespace value.");
    }
}));

suite.add(new Y.Test.Case({
    name: 'Initial value',

    setUp: function() {
        this.editor = make_editor({initial_value_override: 'Initial value'});
    },

    tearDown: function() {
        cleanup_widget(this.editor);
    },

    test_initial_value_override: function() {
        this.editor.render();
        Assert.areEqual(
            'Initial value',
            this.editor.get('input_field').get('value'),
            "The editor's input field should have the initial value.");
    }
}));

suite.add(new Y.Test.Case({
    name: 'Editable text initial values',

    setUp: function() {
        setup_sample_html();
        this.etext = make_editable_text(
            {initial_value_override: 'Initial value'});
    },

    tearDown: function() {
        // Reset the <span>.
        cleanup_widget(this.etext);
    },

    test_save_initial_value_override: function() {
        this.etext.render();

        Assert.areEqual(
            'Initial value',
            this.etext.editor.get('input_field').get('value'),
            "The input_field should have been set to the initial value.");

        this.etext.editor.save();
        Assert.areEqual(
            'Initial value',
            this.etext.editor.get('value'),
            "The editor's initial value did not get saved.");
        Assert.areEqual(
            null,
            this.etext.editor.get('initial_value_override'),
            "The editor's initial_value_override should be null.");
    },

    test_cancel_does_not_modify_value: function() {
        this.etext.render();

        Assert.areEqual(
            'Some editable inline text.',
            this.etext.editor.get('value'),
            "The editor's value is not what it should be.");
        Assert.areEqual(
            'Initial value',
            this.etext.editor.get('initial_value_override'),
            "The editor's initial_value_override is not what it should be.");

        this.etext.editor.cancel();
        Assert.areEqual(
            'Some editable inline text.',
            this.etext.editor.get('value'),
            "The editor's value did not get reset.");
        Assert.areEqual(
            'Initial value',
            this.etext.editor.get('initial_value_override'),
            "The editor's initial_value_override did not get preserved.");
    }
}));

suite.add(new Y.Test.Case({

    name: "Inline editor input sizing for a positive size value",

    setUp: function() {
        this.expected_size = 32;
        this.editor = make_editor({size: this.expected_size});
    },

    tearDown: function() {
        cleanup_widget(this.editor);
    },

    test_editor_size_attribute_matches_user_value: function() {
        Assert.areEqual(
            this.editor.get('size'),
            this.expected_size,
            "The editor's 'size' attribute should match the user's " +
            "specified size.");
    },

    test_input_field_size_matches_the_editor_size: function() {
        this.editor.render();
        var input = this.editor.get('input_field');
        Assert.areEqual(
            this.expected_size + 'px',
            input.getStyle('width'),
            "The editor's input field size should have been set from the " +
            "'size' attribute.");
    }

}));

suite.add(new Y.Test.Case({

    name: "Inline editor input sizing for a null size value",

    setUp: function() {
        this.editor = make_editor();
        this.editor.render();
    },

    tearDown: function() {
        cleanup_widget(this.editor);
    },

    test_editor_size_attribute_is_null: function() {
        Assert.areEqual(
            null,
            this.editor.get('size'),
            "The editor's 'size' attribute should default to 'null'.");
    },

    test_editor_input_has_browser_default_size: function() {
        var input = this.editor.get('input_field');
        Assert.isFalse(
            input.hasAttribute('size'),
            "The editor's input field should have the browser default " +
            "size if the editor's size is 'null'.");
    }
}));

/*
 * XXX mars 20090206
 *
 * The following test is just for the attribute validators.  Most of this is
 * made necessary because YUI doesn't publish attribute validation errors.
 *
 * See ticket http://yuilibrary.com/projects/yui3/ticket/2525946
 */
suite.add(new Y.Test.Case({

    name: "Inline editor size attribute validation",

    setUp: function() {
        this.initial_size = null;
        this.editor = make_editor({size: this.initial_size});
    },

    test_editor_accepts_null_as_size: function() {
        this.editor.set('size', null);
        Assert.areEqual(
            null,
            this.editor.get('size'),
            "The editor should accept a null value for the size attribute.");
    },

    test_editor_accepts_positive_numbers_as_size: function() {
        this.editor.set('size', 123);
        Assert.areEqual(
            123,
            this.editor.get('size'),
            "The editor should accept a positive number as a valid size.");
    },

    test_editor_rejects_negative_numbers_for_size: function() {
        this.editor.set('size', -2);
        Assert.areEqual(
            this.initial_size,
            this.editor.get('size'),
            "The editor should not accept negative numbers for its size.");
    },

    test_editor_rejects_characters_for_size: function() {
        this.editor.set('size', 'a');
        Assert.areEqual(
            this.initial_size,
            this.editor.get('size'),
            "The editor should not accept strings for its size.");
    }
}));


suite.add(new Y.Test.Case({

    name: 'editor_save_state_change',

    setUp: function() {
        this.editor = make_editor();
    },

    tearDown: function() {
        cleanup_widget(this.editor);
    },

    test_ui_initial_state_is_not_waiting: function() {
        this.editor.render();
        Assert.isFalse(
            this.editor.get('boundingBox').hasClass('yui3-ieditor-waiting'),
            "The editor UI should not start out in the 'waiting' state.");
    },

    test_set_ui_waiting_state: function() {
        var ed = this.editor;
        ed.render();

        ed._uiSetWaiting();

        Assert.isTrue(
            ed.get('input_field').get('disabled'),
            "The editor's input should be disabled while in the " +
            "'waiting' state.");
        Assert.isTrue(
            ed.get('boundingBox').hasClass('yui3-ieditor-waiting'),
            "The editor's UI should reflect the 'waiting' state " +
            "with an appropriate class.");
    },

    test_clear_ui_waiting_state: function() {
        var ed = this.editor;
        ed.render();

        ed._uiSetWaiting();
        ed._uiClearWaiting();

        Assert.isFalse(
            ed.get('input_field').get('disabled'),
            "The editor's input should be re-enabled when clearing " +
            "the 'waiting' state.");
        Assert.isFalse(
            ed.get('boundingBox').hasClass('yui3-ieditor-waiting'),
            "The editor's UI should have the 'waiting' state " +
            "class removed.");
    }
}));


suite.add(new Y.Test.Case({

    name: 'editable_text',

    setUp: function() {
        setup_sample_html();
        this.etext = make_editable_text();
    },

    tearDown: function() {
        cleanup_widget(this.etext);
    },

    test_initial_values_from_DOM: function() {
        Assert.areEqual(
            Y.one("#single_text"),
            this.etext.get('text'),
            "The editor's text node should have been set from the " +
            "DOM.");

        Assert.areEqual(
            Y.one('#single_edit'),
            this.etext.get('trigger'),
            "The editor's trigger node should have been set from " +
            "the DOM.");

        Assert.areEqual(
            'Some editable inline text.',
            this.etext.editor.get('value'),
            "The editor's initial value should be set from it's " +
            "text node.");

        Assert.areEqual(
            this.etext.editor.get('value'),
            this.etext.get('value'),
            "The editable text's value should be the same as the " +
            "editor's.");
    },

    test_show: function() {
        /* The show() method should display the editor, and hide the
         * existing contents.
         */
        this.etext.render();
        this.etext.show_editor();
        Assert.isTrue(this.etext.editor.get('visible'),
            "The editor's 'visible' attribute should be true.");
    },

    test_hide: function() {
        /* The hide() method should hide the editor, and display the
         * original contents.
         */
        this.etext.render();
        this.etext.show_editor();
        this.etext.hide_editor();
        Assert.isFalse(this.etext.editor.get('visible'),
            "The editor's 'visible' attribute should be False.");
    },

    test_trigger_edit: function() {
        /* Clicking on the editable text's "Edit" button should
         * make the editor visible.
         */
        Assert.isFalse(this.etext.editor.get('visible'),
            "Sanity check, the editor should be hidden.");

        this.etext.render();
        simulate('#single_edit', 'click');

        Assert.isTrue(this.etext.editor.get('visible'),
            "The editor should be visible.");
    },

    test_text_is_updated_to_saved_value: function() {
        this.etext.render();

        // Grab the normalized text.
        var expected_value = 'abc';

        Assert.areNotEqual(
            expected_value,
            this.etext.get('value'),
            "Sanity check");

        simulate('#single_edit', 'click');
        this.etext.editor
            .get('input_field')
            .set('value', expected_value);

        this.etext.editor.save();

        Assert.areEqual(
            expected_value,
            this.etext.editor.get('value'),
            "Sanity check: the editor's value should have been " +
            "saved.");

        Assert.areEqual(
            expected_value,
            this.etext.get('value'),
            "The editable text's current value should be updated " +
            "after saving some new text in the editor.");
    },

    test_text_is_escaped: function() {
        this.etext.render();

        var input_value = '<i>l33t inject0r d00d</i> 0wnz y00';
        var shown_value = '&lt;i&gt;l33t inject0r d00d&lt;/i&gt; 0wnz y00';

        simulate('#single_edit', 'click');
        this.etext.editor.setInput(input_value);
        this.etext.editor.save();

        Assert.areEqual(
            shown_value,
            this.etext.get('text').get('innerHTML'),
            "Input text should be escaped before being inserted in HTML.");
        Assert.areEqual(
            input_value,
            this.etext.editor.getInput(),
            "Input text should be retained verbatim.");
    },

    test_accept_empty_attribute_passthrough: function() {
        var et = this.etext;

        Assert.areEqual(
            et.get('accept_empty'),
            et.editor.get('accept_empty'),
            "The editor and inline editor's 'accept_empty " +
            "should start out the same.");

        et.set('accept_empty', true);
        Assert.isTrue(
            et.editor.get('accept_empty'),
            "The inline editor's 'accept_empty' attribute should " +
            "also be set to 'true'.");
        Assert.isTrue(
            et.get('accept_empty'),
            "The editor's 'accept_empty' attribute should be true.");

        et.set('accept_empty', false);
        Assert.isFalse(
            et.get('accept_empty'),
            "The editor's 'accept_empty' attribute should be false.");
        Assert.isFalse(
            et.editor.get('accept_empty'),
            "The inline editor's 'accept_empty' attribute should " +
            "also be set to 'false'.");
    },

    test_widget_has_a_disabled_tabindex_when_focused: function() {
        // The tabindex attribute appears when the widget is focused.
        this.etext.render();
        this.etext.focus();

        // Be aware that in IE, get('tabIndex') and getAttribute('tabIndex')
        // return different values when set to -1. This is due to YUI's
        // getAttribute() calling dom_node.getAttribute('tabIndex', 2), which
        // is an IE extension.
        // http://msdn.microsoft.com/en-us/library/ms536429%28VS.85%29.aspx

        // On IE and KHTML, EditableText._onRender() will prevent the
        // default widget rendering that would set the tabIndex on the
        // boundingBox, so this test will fail for those browsers.
        Assert.areEqual(
            -1,
            this.etext.get('boundingBox').get('tabIndex'),
            "The widget should have a tabindex of -1 (disabled).");
    },

    test_trigger_is_disabled_if_the_widget_is_not_rendered: function() {
        var trigger = this.etext.get('trigger');
        Assert.isInstanceOf(
            Y.Node, trigger,
            "Sanity check: the editor's trigger should be a valid node.");
        Assert.isFalse(
            this.etext.get('rendered'),
            "Sanity check: the editor should not be rendered.");

        simulate(trigger, 'click');
        // Peek inside the box a bit, and check that the nested editor
        // instance is still invisible.  Assume that if it is, then
        // the show_editor() method was never called.
        Assert.isFalse(
            this.etext.editor.get('visible'),
            "Triggering an unrendered editor should not display the widget.");
    }
}));

suite.add(new Y.Test.Case({

    name: "EditableText single-line/multi-line modes",

    setUp: function() {
        setup_sample_html();
        this.single = make_editable_text({
            contentBox: '#editable_single_text',
            multiline: false
        });
        this.single.render();
        this.single.show_editor();
        this.multi = make_editable_text({
            contentBox: '#editable_multi_text',
            multiline: true
        });
        this.multi.render();
        this.multi.show_editor();
    },

    tearDown: function() {
        cleanup_widget(this.single);
        cleanup_widget(this.multi);
    },

    test_multi_line_has_larger_minimum: function() {
        var single = this.single.editor;
        var multi = this.multi.editor;

        single.setInput('');
        multi.setInput('');

        var single_height = single.get('input_field').getStyle('height');
        var multi_height = multi.get('input_field').getStyle('height');

        single_height = parse_size(single_height);
        multi_height = parse_size(multi_height);

        Assert.areNotEqual(
            multi_height,
            single_height,
            "Multi-line and single-line editors should have different sizes.");
        Assert.isTrue(
            multi_height > single_height,
            "Multi-line editor should start out larger.");
    },

    test_single_line_top_button_box: function() {
        var box = this.single.editor.get("top_buttons");
        Assert.areEqual(
            null,
            box,
            "Single-line editor should not have a top button box.");
    },

    test_multi_line_top_button_box: function() {
        var box = this.multi.editor.get("top_buttons");
        Assert.areNotEqual(
            null,
            box,
            "Multi-line editor should have a top button box.");
    }
}));

suite.add(new Y.Test.Case({

    name: "Editor input sizing",

    setUp: function() {
        this.expected_size = 43;
        this.editor = make_editor({
            contentBox: '#editable_single_text',
            size: this.expected_size,
            multiline: true,
            skip_animations: true

        });
        this.editor.render();

        this.long_line = 'mm mmmmm mmmmmmm mm mmm mm mmmmmmm mmmmmmmm mm mmm m';
        this.long_word = 'mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm';
        this.short_line = 'hi mom';
    },

    tearDown: function() {
        cleanup_widget(this.editor);
    },

    // test_size_attribute_passthrough: function() {
    //     // create a new editor with the input size set to 23 characters.
    //     Assert.areEqual(
    //         this.expected_size,
    //         this.editor.get('size'),
    //         "The inline editor widget should have received a size " +
    //         "from the EditableText widget.");
    // },

    test_long_text_wraps: function() {
        var editor = this.editor,
            input = editor.get('input_field'),
            original_height = input.getComputedStyle('height');

        editor.setInput(this.long_line);
        var new_height = input.getComputedStyle('height');

        Assert.areNotEqual(
            original_height,
            new_height,
            "Inserting a long text should grow the input area.");
        Assert.isTrue(
            parse_size(new_height) > parse_size(original_height),
            "A grown input area should be larger than before.");
    },

    test_long_words_scroll: function() {
        var editor = this.editor,
            input = editor.get('input_field'),
            original_height = input.getStyle('height');

        editor.setInput(this.long_word);
        var new_height = input.getStyle('height');

        Assert.areNotEqual(
            original_height,
            new_height,
            "Long words should add legroom for a horizontal scrollbar.");
        Assert.isTrue(
            parse_size(new_height) > parse_size(original_height),
            "A grown input area should be larger than before.");
    },

    test_long_text_unwraps: function() {
        var editor = this.editor,
            input = editor.get('input_field');

        editor.setInput(this.short_line);
        var original_height = input.getStyle('height');

        editor.setInput(this.long_line);
        editor.setInput(this.short_line);
        var new_height = input.getStyle('height');

        Assert.areEqual(
            original_height,
            new_height,
            "Removing lines of text should shrink the input area.");
    },

    test_long_words_unscroll: function() {
        var editor = this.editor,
            input = editor.get('input_field');

        editor.setInput(this.short_line);
        var original_height = input.getStyle('height');

        editor.setInput(this.long_word);
        editor.setInput(this.short_line);
        var new_height = input.getStyle('height');

        Assert.areEqual(
            original_height,
            new_height,
            "Removing long words should remove legroom for scrollbar.");
        Assert.areEqual(
            'hidden',
            input.getStyle('overflow'),
            "Scrollbars should be hidden when long lines are removed.");
    }
}));

suite.add(new Y.Test.Case({
    name: "Window resizing",

    setUp: function() {
        this.small_size = 5;
        this.large_size = 40;
        this.short_line = 'i';
        // A line that fits in small_size but not in large_size.
        this.long_line = 'x xx x xx x xx x xx';
        // A word that fits in small_size but not in large_size.
        this.long_word = 'xxxxxxxxxxxxxxxxxxx';
        this.editor = make_editor();
        this.editor.render();
    },

    tearDown: function() {
        cleanup_widget(this.editor);
    },

    // Pretend that a window resize has changed the editor's width to
    // the given number of columns.  Also lets you set new contents for
    // the input box.  Returns resulting input box height in pixels.
    _pretendResize: function(new_size, new_text) {
        var text = (new_text ? new_text : this.editor.getInput());
        var content_box = this.editor.get('contentBox');

        var old_input = this.editor.get('input_field');
        content_box.removeChild(old_input);
        this.editor.set('input_field', null);

        var old_alter_ego = this.editor.alter_ego;
        content_box.removeChild(old_alter_ego);
        this.editor.alter_ego = null;

        this.editor.set('size', new_size);
        this.editor._initInput();

        this.editor.setInput(text);
        this.editor._windowResize();
        return this._getInputBoxHeight();
    },

    _getInputBoxHeight: function() {
        var input = this.editor.get('input_field');
        return parse_size(input.getStyle('height'));
    },

    // Helper: assert lower < higher, and print helpful message.
    _assertLower: function(lower, higher, failure_text) {
        if (!(lower < higher)) {
            // Log values in separate statements to avoid infinite recursion
            // during ill-typed attempts at string concatenation.
            Y.log("Expected the first of these to be lower than the second:");
            Y.log(lower);
            Y.log(higher);
        }
        Assert.isTrue(lower < higher, failure_text);
    },

    test_resize_might_not_change_layout: function() {
        var roomy = this._pretendResize(this.large_size, this.short_line);
        console.log('roomy', roomy);
        console.log('right', tight);
        
        var tight = this._pretendResize(this.small_size);
        Assert.areEqual(
            roomy,
            tight,
            "If there's enough room, resizing should not affect height.");
    },

    test_undersize_adds_lines: function() {
        var roomy = this._pretendResize(this.large_size, this.long_line);
        var tight = this._pretendResize(this.small_size);
        this._assertLower(
            roomy,
            tight,
            "Undersizing a long line should break it.");
    },

    test_oversize_removes_lines: function() {
        var tight = this._pretendResize(this.small_size, this.long_line);
        var roomy = this._pretendResize(this.large_size);
        this._assertLower(
            roomy,
            tight,
            "Oversizing a long line should unbreak it.");
    },

    test_undersize_adds_scrollbar: function() {
        // Actually, a scrollbar and/or more lines.  The spec leaves it
        // all up to the browser, but either way we'll see a higher
        // input box.
        var roomy = this._pretendResize(this.large_size, this.long_word);
        var tight = this._pretendResize(this.small_size);
        this._assertLower(
            roomy,
            tight,
            "Undersizing a long word should require a taller input box.");
    },

    test_oversize_removes_scrollbar: function() {
        var tight = this._pretendResize(this.small_size, this.long_word);
        var roomy = this._pretendResize(this.large_size);
        this._assertLower(
            roomy,
            tight,
            "Oversizing a long word should reduce input box height.");
    },

    test_resize_works_while_hidden: function() {
        var roomy = this._pretendResize(this.large_size, this.long_line);
        this.editor.hide();
        var tight = this._pretendResize(this.small_size);
        this.editor.show();
        this.editor.updateSize();
        Assert.areNotEqual(
            roomy,
            tight,
            "Editors should notice window resizes even while hidden.");
    }
}));


suite.add(new Y.Test.Case({
    name: "EditableText text value",

    setUp: function() {
        setup_sample_html();
        this.multi = make_editable_text({

            contentBox: '#editable_multi_text',
            multiline: true
        });
        this.multi.render();
    },

    tearDown: function() {
        cleanup_widget(this.multi);
    },

    test_text_value_no_trailing_newlines: function() {
        var text = this.multi.get('value');
        Assert.areEqual(
           "Some editable multi-line text.",
           text,
           "The editor kills trailing whitespace.");
    }
}));

function FailedSavePlugin() {
  FailedSavePlugin.superclass.constructor.apply(this, arguments);
}

FailedSavePlugin.NAME = 'failedsave';
FailedSavePlugin.NS = 'test';

Y.extend(FailedSavePlugin, Y.Plugin.Base, {
    initializer: function(config) {
      this.doBefore("_saveData", this._altSave);
    },

    _altSave: function() {
      var host  = this.get('host');
      // Set the UI 'waiting' status.
      host._uiSetWaiting();
      host.showError("Some error occurred.");
      // Make sure we clear the 'waiting' status.
      host._uiClearWaiting();
      return new Y.Do.Halt();
    }
  });

// suite.add(new Y.Test.Case({
//     name: "Edit buttons enabled on error",
// 
//     setUp: function() {
//         setup_sample_html();
//         this.multi = make_editable_text({
// 
//             contentBox: '#editable_multi_text',
//             multiline: true
//         });
//         this.multi.render();
//         this.multi.show_editor();
//     },
// 
//     tearDown: function() {
//         cleanup_widget(this.multi);
//     },
// 
//     test_error_on_save_enabled_buttons: function() {
//         var editor = this.multi.editor;
//         editor.plug({fn:FailedSavePlugin});
//         // Now saving should invoke an error.
//         editor.save();
//         Assert.isTrue(editor.get('in_error'), "Editor should be in error");
//         // Both the submit and cancel buttons should be visible.
//         Assert.areEqual(
//             'inline-block',
//             editor.get('submit_button').getStyle('display'),
//             "Submit should be set to display:inline");
//         Assert.areEqual(
//             'inline-block',
//             editor.get('cancel_button').getStyle('display'),
//             "Cancel should be set to display:inline");
//     }
// }));

Y.lp.testing.Runner.run(suite);

});
