/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * @module TranslationImportQueue
 * @requires oop, event, node
 */

YUI.add('translations', function(Y) {

var translations = Y.namespace('translations');

/**
 * HTML for the "this entry has error output" icon.  This does not include the
 * fold/unfold triangle shown next to it.
 */
var base_button = '<img src="/@@/info" alt="output" />';

/**
 * HTML for panel showing an entry's error output.  The spinner icon is
 * replaced by the actual error output as it comes in.
 */
var output_panel_html =
    '<tr class="discreet secondary output-panel"><td>' +
    '<div><img src="/@@/spinner" /></div>' +
    '</td></tr>';

/**
 * Compose HTML for the error-output button: the basic button plus the
 * fold/unfold triangle.
 */
var compose_button = function(shown) {
    return base_button +
        (shown ? 
            '<img src="/@@/treeExpanded" alt="show" />' :
            '<img src="/@@/treeCollapsed" alt="hide" />');
};

/**
 * Replace given button (or initial placeholder, if the page is only just
 * rendering) with one in the given state.
 *
 * This removes the entire old button and replaces it with a new one.  That's
 * one sure-fire way of getting rid of the old one's click-event handler, which
 * is otherwise a brittle procedure and at the same time hard to test.
 */
var alter_button = function(button, shown) {
    var button_field = button.get('parentNode');
    var text =
        '<div class="new show-output">' +
        compose_button(shown) +
        '</div>';
    new_button = button_field.create(text);
    button_field.replaceChild(new_button, button);
    new_button.attach('click', (shown ? hide_output : show_output));
    return button_field.get('parentNode');
};

/**
 * Remove the error-output panel pointed at by event.
 */
var hide_output = function(e) {
    var row = alter_button(e.currentTarget, false);
    var output_panel = row.next();
    if (output_panel.hasClass("output-panel")) {
        output_panel.get('parentNode').removeChild(output_panel);
    }
};

/**
 * Factory for error-output request (and response handlers) for a given
 * output panel.
 */
var output_loader = function(node) {
    return {
        on: {
            success: function(entry) {
                var output_block = entry.get('error_output');
                var error_pre = node.create('<pre></pre>');
                error_pre.appendChild(document.createTextNode(output_block));
                node.set('innerHTML', null);
                node.appendChild(error_pre);
            },
            failure: function(errcode) {
                node.set(
                    'innerHTML',
                    '<strong>ERROR: could not retrieve output.  ' +
                    'Please try again later.</strong>');
            }
        }
    };
};

/**
 * Button has been clicked.  Reveal output panel and request error output from
 * the Launchpad web service.
 */
var show_output = function(e) {
    var row = alter_button(e.currentTarget, true);
    var table = row.get('parentNode');
    var entry_id = row.get('id');

    var output = table.create(output_panel_html);
    table.insertBefore(output, row.next());

    var entry_uri = '+imports/' + entry_id;
    var div = output.query('div');
    new LP.client.Launchpad().get(entry_uri, output_loader(div));
};


/**
 * Set up the import queue page.  Replace placeholders for error-output buttons
 * with actual buttons, and make them functional.
 */
translations.initialize_import_queue_page = function (Y) {
    var button_markers = Y.all('.show-output');
    button_markers.set('innerHTML', compose_button(false));
    button_markers.attach('click', show_output);
};

}, '0.1', {
    // "oop" and "event" are required to fix known bugs in YUI, which
    // are apparently fixed in a later version.
    requires: ['oop', 'event', 'node']});
