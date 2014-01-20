/* Copyright 2014 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for handling inline comments in diffs.
 *
 * @module lp.code.branchmergeproposal.inlinecomments
 * @requires node
 */

YUI.add('lp.code.branchmergeproposal.inlinecomments', function(Y) {

// Grab the namespace in order to be able to expose the connect methods.
var namespace = Y.namespace('lp.code.branchmergeproposal.inlinecomments');

namespace.inlinecomments = {};

namespace.add_doubleclick_handler = function() {
    var rows = Y.one('.diff').all('tr');
    var handling_request = false;
    handler = function(e) {
        if (handling_request === true) {
            return;
        }
        handling_request = true;
        var linenumberdata = e.currentTarget.one('.line-no');
        var line_number = linenumberdata.get('text');
        // Retrieve or create a row container for the comment editor.
        var header_row = Y.one('#ict-' + line_number + '-draft-header');
        if (header_row === null) {
            header_row = namespace.create_row({'line_number': line_number});
        }
        var content_row = header_row.next()
        var widget = new Y.EditableText({
            contentBox: content_row.one(
                '#inlinecomment-' + line_number + '-draft'),
            initial_value_override: namespace.inlinecomments[line_number],
            accept_empty: true,
            multiline: true,
            buttons: 'top'
        });
        widget.render();
        handle_widget_button = function(saved, comment) {
            if (saved === true) {
                namespace.inlinecomments[line_number] = comment;
            }
            if (comment === '') {
                delete namespace.inlinecomments[line_number];
                header_row.remove(true);
                content_row.remove(true);
            }
            var diff_timestamp = LP.cache.preview_diff_timestamps.slice(-1)[0];
            var config = {
                parameters: {
                    diff_timestamp: diff_timestamp,
                    comments: namespace.inlinecomments
                }
            };
            lp_client = new Y.lp.client.Launchpad();
            lp_client.named_post(
                LP.cache.context.self_link, 'saveDraftInlineComment', config);
            handling_request = false;
        };
        widget.editor.on('save', function() {
            handle_widget_button(true, this.get('value'));
        });
        widget.editor.on('cancel', function(e) {
            handle_widget_button(false, this.get('value'));
        });
        widget._triggerEdit(e);
    };
    rows.on('dblclick', handler);
};

namespace.create_row = function(comment) {
    var ident = comment.line_number + '-draft';
    var headerrow = Y.Node.create(
        '<tr><td colspan="2"></td></tr>').addClass('ict-header');
    var headerspan;
    var newrow;
    if (Y.Lang.isUndefined(comment.person)) {
        // Creates a draft inline comment area.
        headerspan = Y.Node.create('<span></span>').set(
            'text', 'Draft comment.');
        headerrow.set('id', 'ict-' + ident + '-header');
        newrow = Y.Node.create('<tr><td></td><td><div>' +
            '<span class="yui3-editable_text-text"></span>' +
            '<div class="yui3-editable_text-trigger"></div>' +
            '</div></td></tr>').set('id', 'ict-' + ident);
        newrow.one('td>div').set('id', 'inlinecomment-' + ident);
        if (!Y.Lang.isUndefined(comment.text)) {
            namespace.inlinecomments[comment.line_number] = comment.text;
            newrow.one('span').set('text', comment.text);
        }
    } else {
        // Creates a published inline comment area.
        headerspan = Y.Node.create(
            '<span>Comment by <a></a> on <span></span></span>');
        // Wrap resources coming from LP.cache, as they come from
        // the LP API (updates during the page life-span). This way
        // the handling code can be unified.
        if (Y.Lang.isUndefined(comment.person.get)) {
            var lp_client = new Y.lp.client.Launchpad();
            comment.person = lp_client.wrap_resource(null, comment.person);
        }
        var header_content = (
            comment.person.get('display_name') +
            ' (' + comment.person.get('name') + ')');
        headerspan.one('a').set('href', comment.person.get('web_link')).set(
            'text', header_content);
        headerspan.one('span').set('text', comment.date);
        newrow = Y.Node.create('<tr><td></td><td><span></span></td></tr>');
        newrow.one('span').set('text', comment.text);
    }
    headerrow.one('td').appendChild(headerspan);

    // We want to have the comments in order after the line.
    var tr = Y.one('#diff-line-' + (parseInt(comment.line_number, 10) + 1));
    if (tr !== null) {
        tr.insert(headerrow, 'before');
    } else {
        // If this is the last row, grab the last child.
        tr = Y.one('.diff>tbody>tr:last-child');
        tr.insert(headerrow, 'after');
    }
    headerrow.insert(newrow, 'after');

    return headerrow;
};

namespace.populate_existing_comments = function() {
    // Cleanup previous inline review comments.
    Y.all('.ict-header').each( function(line) {
        line.next().remove();
        line.remove();
    });
    // Display published inline comments.
    // [{'line_number': <lineno>, 'person': <IPerson> 'text': <comment>,
    //   'date': <timestamp>}, ...]
    LP.cache.published_inline_comments.forEach( function (comment) {
        namespace.create_row(comment);
    });
    // Display draft inline comments:
    // {'<line_number>':''<comment>', ...})
    if (LP.cache.draft_inline_comments !== null) {
        var drafts = LP.cache.draft_inline_comments;
        Object.keys(drafts).forEach( function (line_number) {
            var comment = {
                'line_number': line_number,
                'text': drafts[line_number],
            };
            namespace.create_row(comment);
        });
    }

};

namespace.setup_inline_comments = function() {
    if (LP.cache.inline_diff_comments === true) {
        // Add the double-click handler for each row in the diff. This needs
        // to be done first since populating existing published and draft
        // comments may add more rows.
        namespace.add_doubleclick_handler();
        namespace.populate_existing_comments();
    }
};

}, '0.1', {requires: ['event', 'io', 'node', 'widget', 'lp.client',
                      'lp.ui.editor']});
