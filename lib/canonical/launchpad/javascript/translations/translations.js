/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * @module TranslationImportQueue
 * @requires node-base, dom-base, event, node, io, selector
 */

YUI.add('translations', function(Y) {

var translations = Y.namespace('translations');

var base_button = '<img src="/@@/info" alt="output" />';
var output_panel_html =
    '<tr class="discreet secondary output-panel"><td>' +
    '<div><img src="/@@/spinner" /></div>' +
    '</td></tr>';

function compose_button(shown) {
    return base_button +
	(shown ? 
	    '<img src="/@@/treeExpanded" alt="show" />' :
	    '<img src="/@@/treeCollapsed" alt="hide" />');
}

function alter_button(button, shown) {
    var button_field = button.get('parentNode');
    var text =
	'<div class="new show-output">' +
	compose_button(shown) +
	'</div>';
    new_button = button_field.create(text);
    button_field.replaceChild(new_button, button);
    new_button.attach('click', (shown ? hide_output : show_output));
    return button_field.get('parentNode');
}

function hide_output(e) {
    var row = alter_button(e.currentTarget, false);
    var output_panel = row.next();
    if (output_panel.hasClass("output-panel")) {
	output_panel.get('parentNode').removeChild(output_panel);
    }
}

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

function show_output(e) {
    var row = alter_button(e.currentTarget, true);
    var table = row.get('parentNode');
    var entry_id = row.get('id');

    var output = table.create(output_panel_html);
    table.insertBefore(output, row.next());

    var entry_uri = '+imports/' + entry_id;
    var div = output.query('div');
    translations.lpclient.get(entry_uri, output_loader(div));
}

translations.initialize_import_queue_page = function (Y) {
    translations.lpclient = new LP.client.Launchpad();

    var button_markers = Y.all('.show-output');
    button_markers.set('innerHTML', compose_button(false));
    button_markers.attach('click', show_output);
};

}, '0.1', {
    requires: [
        'yui-base', 'event', 'dom-base', 'selector',
        'io-base', 'io-form', 'io-queue', 'io-xdr', 'node-base']});
