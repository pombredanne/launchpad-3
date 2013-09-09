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

namespace.add_doubleclick_handler = function() {
    var inlinecomments = {};
    var rows = Y.one('.diff').all('tr');
    var handling_request = false;
    handler = function(e) {
        if (handling_request === true) {
            return;
        }
        handling_request = true;
        var linenumberdata = e.currentTarget.one('.line-no');
        var rownumber = linenumberdata.get('text');
        var rows = namespace.create_or_return_row(rownumber, '', '', '');
        var headerrow = rows[0];
        var newrow = rows[1];
        var widget = new Y.EditableText({
            contentBox: newrow.one('#inlinecomment-' + rownumber + '-draft'),
            initial_value_override: inlinecomments[rownumber],
            accept_empty: true,
            multiline: true,
            buttons: 'top'
        });
        widget.render();
        handle_widget_button = function(saved, comment) {
            if (saved === true) {
                inlinecomments[rownumber] = comment;
            }
            if (comment === '') {
                headerrow.remove(true);
                newrow.remove(true);
            }
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
    var draft = true;
    if (person !== '') {
        suffix = '-' + person.name;
        draft = false;
    }
    var middle = rownumber + suffix;
    var headerrow = Y.one('#ict-' + middle + '-header');
    var newrow;
    if (headerrow === null) {
        headerrow = Y.Node.create(
            '<tr><td colspan="2"></td></tr>').set(
            'id', 'ict-' + middle + '-header').addClass('ict-header'); 
        var headerspan = Y.Node.create('<span></span>').addClass(
            'inlinecomment-' + middle + '-header').set(
            'text', 'Draft comment.');
        if (person !== '' && date !== '') {
            var personlink = Y.Node.create('<a></a>').set(
                'href', person.web_link).set(
                'text', person.display_name + ' (' + person.name + ')');
            headerspan.set(
                'text', "Comment by ").appendChild(personlink);
            headerspan.appendChild(Y.Node.create('<span></span>').set(
                'text', " on " + date));
        }
        headerrow.one('td').appendChild(headerspan);
        if (draft === true) {
            var newrowdiv = Y.Node.create('<div></div>').set(
                'id', 'inlinecomment-' + middle);
            newrowdiv.appendChild(
                '<span class="yui3-editable_text-text"></span>');
            newrowdiv.appendChild(
                '<div class="yui3-editable_text-trigger"></div>');
            newrow = Y.Node.create('<tr></tr>').set('id', 'ict-' + middle);
            newrow.appendChild('<td></td>');
            newrow.appendChild('<td></td>').appendChild(newrowdiv);
        } else {
            newrow = Y.Node.create('<tr></tr>').set('id', 'ict-' + middle);
            newrow.appendChild('<td></td>');
            newrow.appendChild('<td></td>').appendChild(
                Y.Node.create('<span></span>').set('text', comment));
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
    } else {
        newrow = headerrow.next();
    }
    return [headerrow, newrow];
};

namespace.populate_existing_comments = function() {
    var i;
    for (i = 0; i < LP.cache.published_inline_comments.length; i++) {
        var row = LP.cache.published_inline_comments[i];
        namespace.create_or_return_row(
            row.line, row.person, row.comment, row.date);
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

  }, '0.1', {requires: ['event', 'io', 'node', 'widget', 'lp.ui.editor']});
