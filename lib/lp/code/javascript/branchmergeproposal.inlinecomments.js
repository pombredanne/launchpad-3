/* Copyright 2013 Canonical Ltd.  This software is licensed under the
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
        var rownumber = linenumberdata.get('text');
        var rows = namespace.create_or_return_row(rownumber, null, null, null);
        var headerrow = rows[0];
        var newrow = rows[1];
        var widget = new Y.EditableText({
            contentBox: newrow.one('#inlinecomment-' + rownumber + '-draft'),
            initial_value_override: namespace.inlinecomments[rownumber],
            accept_empty: true,
            multiline: true,
            buttons: 'top'
        });
        widget.render();
        handle_widget_button = function(saved, comment) {
            if (saved === true) {
                namespace.inlinecomments[rownumber] = comment;
            }
            if (comment === '') {
                delete namespace.inlinecomments[rownumber];
                headerrow.remove(true);
                newrow.remove(true);
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

namespace.create_or_return_row = function(rownumber, person, comment, date) {
    var suffix = '-draft';
    var middle = rownumber + suffix;
    var draft = true;
    if (person !== null) {
        draft = false;
    }
    var headerrow = null;
    if (draft === true) {
        headerrow = Y.one('#ict-' + middle + '-header');
        if (headerrow !== null) {
            return [headerrow, headerrow.next()];
        }
    }
    headerrow = Y.Node.create(
        '<tr><td colspan="2"></td></tr>').addClass('ict-header');
    var headerspan;
    if (person != null && date != null) {
        if (person.get === undefined) {
            var lp_client = new Y.lp.client.Launchpad();
            person = lp_client.wrap_resource(null, person);
        }
        headerspan = Y.Node.create(
            '<span>Comment by <a></a> on <span></span></span>');
        var header_content = (
            person.get('display_name') +
            ' (' + person.get('name') + ')');
        headerspan.one('a').set('href', person.get('web_link')).set(
            'text', header_content);
        headerspan.one('span').set('text', date);
    } else {
        headerspan = Y.Node.create('<span></span>').set(
            'text', 'Draft comment.');
    }
    headerrow.one('td').appendChild(headerspan);
    if (draft === true) {
        headerrow.set('id', 'ict-' + middle + '-header');
        newrow = Y.Node.create('<tr><td></td><td><div>' +
            '<span class="yui3-editable_text-text"></span>' +
            '<div class="yui3-editable_text-trigger"></div>' +
            '</div></td></tr>').set('id', 'ict-' + middle);
        newrow.one('td>div').set('id', 'inlinecomment-' + middle);
        if (comment !== null) {
            namespace.inlinecomments[rownumber] = comment;
            newrow.one('span').set('text', comment);
        }
    } else {
        newrow = Y.Node.create('<tr><td></td><td><span></span></td></tr>');
        newrow.one('span').set('text', comment);
    }
    // We want to have the comments in order after the line, so grab the
    // next row.
    var tr = Y.one('#diff-line-' + (parseInt(rownumber, 10) + 1));
    if (tr !== null) {
        tr.insert(headerrow, 'before');
    } else {
        // If this is the last row, grab the last child.
        tr = Y.one('.diff>tbody>tr:last-child');
        tr.insert(headerrow, 'after');
    }
    // The header row is the tricky one to place, the comment just goes
    // after it.
    headerrow.insert(newrow, 'after');
    return [headerrow, newrow];
};

namespace.populate_existing_comments = function() {
    // Cleanup previous inline review comments.
    Y.all('.ict-header').each( function(line) {
        line.next().remove();
        line.remove();
    });
    var comments = LP.cache.published_inline_comments.concat(
        LP.cache.draft_inline_comments);
    console.log(comments)
    for (var i = 0; i < comments.length; i++) {
        var row = comments[i];
        namespace.create_or_return_row(
            row[0], row[1], row[2], row[3]);
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
