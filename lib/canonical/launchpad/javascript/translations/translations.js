/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * @module TranslationImportQueue
 * @requires yui-base, event, dom-base, selector, io-base, io-form, io-queue,
 * io-xdr, node-base
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
 * Compose HTML for the error-output button box: the basic button plus the
 * fold/unfold triangle.
 */
function compose_button_box(shown) {
    return base_button +
	(shown ? 
	    '<img src="/@@/treeExpanded" alt="show" />' :
	    '<img src="/@@/treeCollapsed" alt="hide" />');
}

/**
 * Replace given button box (or initial placeholder, if the page is only
 * just rendering) with one in the given state.
 *
 * This removes the entire button box and replaces it with a new one.  That's
 * one sure-fire way of getting rid of the old one's click-event handler, which
 * is otherwise a brittle procedure and at the same time hard to test.
 */
function alter_button_box(button, shown) {
    var button_field = button.get('parentNode');
    var text =
	'<div class="new show-output">' +
	compose_button_box(shown) +
	'</div>';
    new_button = button_field.create(text);
    button_field.replaceChild(new_button, button);
    new_button.attach('click', (shown ? hide_output : show_output));
    return button_field.get('parentNode');
}

/**
 * Remove the error-output panel pointed at by event.
 */
function hide_output(e) {
    var row = alter_button_box(e.currentTarget, false);
    var output_panel = row.next();
    if (output_panel.hasClass("output-panel")) {
	output_panel.get('parentNode').removeChild(output_panel);
    }
}

/**
 * Factory for error-output request (and response handlers) for a given
 * output panel.
 */
function output_loader(node) {
    return {
	on: {
	    success: function(entry) {
		var output_block = entry.get('error_output');
		node.set('innerHTML',
                    '<pre></pre>');
		node.appendChild(document.createTextNode(output_block));
	    },
	    failure: function(errcode) {
		node.set(
		    'innerHTML',
		    '<strong>ERROR: could not retrieve output.  ' +
		    'Please try again later.</strong>');
	    }
	}
    };
}

/**
 * Button box has been clicked.  Reveal output panel and request error output
 * from the Launchpad web service.
 */
function show_output(e) {
    var row = alter_button_box(e.currentTarget, true);
    var table = row.get('parentNode');
    var entry_id = row.get('id');

    var output = table.create(output_panel_html);
    table.insertBefore(output, row.next());

    var entry_uri = '+imports/' + entry_id;
    var div = output.query('div');
    translations.lpclient.get(entry_uri, output_loader(div));
}


/**
 * Set up the import queue page.  Replace placeholders for error-output buttons
 * with actual button boxes, and make them functional.
 */
translations.initialize_import_queue_page = function (Y) {
    translations.lpclient = new LP.client.Launchpad();

    var button_markers = Y.all('.show-output');
    button_markers.set('innerHTML', compose_button_box(false));
    button_markers.attach('click', show_output);
};

}, '0.1', {
    requires: [
        'yui-base', 'event', 'dom-base', 'selector',
        'io-base', 'io-form', 'io-queue', 'io-xdr', 'node-base']});
