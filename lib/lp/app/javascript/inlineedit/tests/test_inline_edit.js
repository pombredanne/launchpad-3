/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.inline_edit.test', function (Y) {

    var tests = Y.namespace('lp.inline_edit.test');
    tests.suite = new Y.Test.Suite('inline_edit Tests');
    var Assert = Y.Assert;  // For easy access to isTrue(), etc.

    var SAMPLE_HTML = [
        '<h1>Single-line editing</h1>',
        ' <div id="editable_single_text" style="width: 40em;">',
        ' <span id="single_text"',
        '  class="yui3-editable_text-text">Some editable inline text.</span>',
        ' <button id="single_edit" class="yui3-editable_text-trigger">',
        '  Edit this</button>',
        ' </div>',
        ' <hr />',
        ' <h1>Multi-line editing</h1>',
        ' <div id="editable_multi_text">',
        ' <button id="multi_edit" class="yui3-editable_text-trigger">',
        '  Edit this</button>',
        ' <span id="multi_text" class="yui3-editable_text-text">',
        ' <p>Some editable multi-line text.</p></span>',
        ' </div>'
    ].join('');


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

    // Helper: convert size specification like "120px" to a number (in casu,
    // 120).
    var strip_px = /px$/;
    function parse_size(size) {
        return parseInt(size.replace(strip_px, ''), 10);
    }

    tests.suite.add(new Y.Test.Case({
        name: 'inline_editor_basics',

        setUp: function() {
            this.editor = make_editor();
        },

        tearDown: function() {
            cleanup_widget(this.editor);
        },
        test_library_exists: function () {
            Y.Assert.isObject(Y.InlineEditor,
                "Could not locate the lp.${LIBRARY} module");
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

        test_multiline_calls_display_error: function() {
            this.editor.set('multiline', true);
            this.editor.render();

            // Ensure display_error is called.
            var error_shown = false;
            var old_error_method = Y.lp.app.errors.display_error;
            Y.lp.app.errors.display_error = function(text) {
                error_shown = true;
            };

            var msg = "An error has occured.";
            this.editor.showError(msg);
            Y.Assert.isTrue(error_shown);

            // Restore original method.
            Y.lp.app.errors.display_error = old_error_method;

            // Restore to previous state.
            this.editor.set('multiline', false);
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

            // Be aware that in IE, get('tabIndex') and
            // getAttribute('tabIndex') return different values when set to
            // -1. This is due to YUI's getAttribute() calling
            // dom_node.getAttribute('tabIndex', 2), which is an IE extension.
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
            var input_element = Y.Node.getDOMNode(
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

    tests.suite.add(new Y.Test.Case({
        name: 'Initial value',

        setUp: function() {
            this.editor = make_editor({
                initial_value_override: 'Initial value'
            });
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

    tests.suite.add(new Y.Test.Case({
        name: 'Ellipsis',

        setUp: function() {
            setup_sample_html();
            this.long_text = 'Blah';
            var x;
            for (x=0; x<100; x++) {
                this.long_text += ' Blah';
            }
            Y.one('#single_text').set('text', this.long_text);
            this.single = make_editable_text({
                contentBox: '#editable_single_text',
                truncate_lines: 2,
                multiline: false
            });
            this.single.render();
            this.single._showEllipsis();
        },

        tearDown: function() {
            cleanup_widget(this.single);
        },

        // Long text is truncated in the text display.
        _assert_displayed_value_truncated: function() {
            var ellipsis = '\u2026';
            var display_text = Y.one('#single_text').get('text');
            Y.Assert.isTrue(
                display_text.indexOf(
                    ellipsis, display_text.length - ellipsis.length) >= 0,
                'Long text should be truncated when displayed.');
        },

        // Long text is truncated when first displayed.
        test_initial_value_truncated: function() {
            this._assert_displayed_value_truncated();
        },

        // When the text is edited, the untruncated text is displayed in the
        // input field.
        test_edit_value_not_truncated: function() {
            simulate('#single_edit', 'click');
            Y.Assert.areEqual(
                this.long_text,
                this.single.editor.get('value'),
                'Untruncated text should be displayed in the edit ' +
                'field.');
        },

        // When the text is edited and a short value is entered,  the
        // untruncated text is displayed in the text field as well as being
        // saved.
        test_short_saved_value_not_truncated: function() {
            simulate('#single_edit', 'click');
            this.single.editor
                .get('input_field')
                .set('value', 'Short');

            this.single.editor.save();

            Assert.areEqual(
                'Short',
                this.single.editor.get('value'),
                "Sanity check: the editor's value should have been " +
                "saved.");

            Assert.areEqual(
                'Short',
                this.single.get('value'),
                "The editable text's current value should be updated " +
                "after saving some new text in the editor.");
        },

        // When the text is edited and a long value is entered, the truncated
        // text is displayed in the text field but the long value is saved.
        test_long_saved_value_truncated: function() {
            simulate('#single_edit', 'click');
            var long_saved_text = this.long_text + 'foo';
            this.single.editor
                .get('input_field')
                .set('value', long_saved_text);

            this.single.editor.save();

            Assert.areEqual(
                long_saved_text,
                this.single.editor.get('value'),
                "Sanity check: the editor's value should have been " +
                "saved.");

            Assert.areEqual(
                long_saved_text,
                this.single.get('value'),
                "The editable text's current value should be updated " +
                "after saving some new text in the editor.");
            this._assert_displayed_value_truncated();
        }

    }));

    tests.suite.add(new Y.Test.Case({
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

    tests.suite.add(new Y.Test.Case({
        name: "Edit buttons enabled on error",

        setUp: function() {
            setup_sample_html();
            this.multi = make_editable_text({

                contentBox: '#editable_multi_text',
                multiline: true
            });
            this.multi.render();
            this.multi.show_editor();
        },

        tearDown: function() {
            cleanup_widget(this.multi);
        },

        test_error_on_save_enabled_buttons: function() {
            var editor = this.multi.editor;
            editor.plug({fn:FailedSavePlugin});
            // Now saving should invoke an error.
            editor.save();
            Assert.isTrue(editor.get('in_error'), "Editor should be in error");
            // Both the submit and cancel buttons should be visible.
            Assert.areEqual(
                'inline-block',
                editor.get('submit_button').getStyle('display'),
                "Submit should be set to display:inline");
            Assert.areEqual(
                'inline-block',
                editor.get('cancel_button').getStyle('display'),
                "Cancel should be set to display:inline");
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'lazr.editor', 'node',
    'lp.app.formwidgets.resizing_textarea', 'lp.app.ellipsis',
    'event', 'event-simulate', 'plugin']
});
