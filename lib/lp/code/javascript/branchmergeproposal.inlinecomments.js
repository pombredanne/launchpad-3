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

namespace.inlinecomments = null;

namespace.current_previewdiff_id = null;

namespace.lp_client = new Y.lp.client.Launchpad();

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
        var header_row = Y.one(
            '#ict-' + line_number + '-draft-header');
        if (header_row === null) {
            header_row = namespace.create_row(
                {'line_number': line_number});
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
            if (saved === false) {
                handling_request = false;
		if (namespace.inlinecomments[line_number] === undefined) {
		    header_row.remove(true);
		}
                return;
            }

            namespace.inlinecomments[line_number] = comment;
            if (comment === '') {
                delete namespace.inlinecomments[line_number];
                header_row.remove(true);
                content_row.remove(true);
            }
            var config = {
                parameters: {
                    previewdiff_id: namespace.current_previewdiff_id,
                    comments: namespace.inlinecomments
                }
            };
            namespace.lp_client.named_post(
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
            '<span>Comment by <a></a> <span></span></span>');
        // Wrap resources coming from LP.cache, as they come from
        // the LP API (updates during the page life-span). This way
        // the handling code can be unified.
        if (Y.Lang.isUndefined(comment.person.get)) {
            comment.person = namespace.lp_client.wrap_resource(
                null, comment.person);
        }
        var header_content = (
            comment.person.get('display_name') +
            ' (' + comment.person.get('name') + ')');
        headerspan.one('a').set('href', comment.person.get('web_link')).set(
            'text', header_content);
        // XXX cprov 20140226: the date should be formatted according to
        // the user locale/timezone similar to fmt:displaydate.
        // We should leverage Y.Intl features. 
        var fmt_date = 'on ' + Y.Date.format(
            new Date(comment.date), {format: '%Y-%m-%d'});
        headerspan.one('span').set('text', fmt_date);
        newrow = Y.Node.create('<tr><td></td><td><span></span></td></tr>');
        newrow.one('span').set('text', comment.text);
    }
    headerrow.one('td').appendChild(headerspan);

    // We want to have the comments in order after the line.
    var tr = Y.one('#diff-line-' + (parseInt(comment.line_number) + 1));
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

    var config_published = {
        on: {
            success: function (comments) {
                // Display published inline comments.
                // [{'line_number': <lineno>, 'person': <IPerson>,
                //   'text': <comment>, 'date': <timestamp>}, ...]
                comments.forEach( function (comment) {
                    namespace.create_row(comment);
                });
            },
        },
        parameters: {
            previewdiff_id: namespace.current_previewdiff_id
        }
    };
    namespace.lp_client.named_get(
        LP.cache.context.self_link, 'getInlineComments', config_published);

    var config_draft = {
        on: {
            success: function (drafts) {
                namespace.inlinecomments = {}; 
                if (drafts === null) {
                    return;
                }
                // Display draft inline comments:
                // {'<line_number>':''<comment>', ...})
                Object.keys(drafts).forEach( function (line_number) {
                    var comment = {
                        'line_number': line_number,
                        'text': drafts[line_number],
                    };
                    namespace.create_row(comment);
                });
            },
        },
        parameters: {
            previewdiff_id: namespace.current_previewdiff_id
        }
    };
    namespace.lp_client.named_get(
        LP.cache.context.self_link, 'getDraftInlineComments', config_draft);
};

namespace.setup_inline_comments = function(previewdiff_id) {
    if (LP.cache.inline_diff_comments !== true) {
        return;
    }
    // Store the current diff ID locally.
    namespace.current_previewdiff_id = previewdiff_id;
    // Add the double-click handler for each row in the diff. This needs
    // to be done first since populating existing published and draft
    // comments may add more rows.
    namespace.add_doubleclick_handler();
    namespace.populate_existing_comments();
};



function DiffNav(config) {
    DiffNav.superclass.constructor.apply(this, arguments);
}

Y.mix(DiffNav, {

    NAME: 'diffnav',

    ATTRS: {

        /**
         * The LP client to use. If none is provided, one will be
         * created during initialization.
         *
         * @attribute lp_client
         */
        lp_client: {
            value: null
        },
    }

});


Y.extend(DiffNav, Y.Widget, {

    /*
     * The initializer method that is called from the base Plugin class.
     *
     * @method initializer
     * @protected
     */
    initializer: function(cfg){
        // If we have not been provided with a Launchpad Client, then
        // create one now:
        if (null === this.get("lp_client")){
            // Create our own instance of the LP client.
            this.set("lp_client", new Y.lp.client.Launchpad());
        }
    },

    _connectNavigator: function(navigator) {
        var self = this;
        var rc = Y.lp.code.branchmergeproposal.reviewcomment;
        (new rc.NumberToggle()).render();
        namespace.setup_inline_comments(navigator.get('value'));

        navigator.on('change', function() {
            var previewdiff_id = this.get('value');
            var preview_diff_uri = (
                LP.cache.context.web_link +
                '/+preview-diff/' + previewdiff_id + '/+diff');
            var container = self.get('srcNode').one('.diff-content');
            var config = {
                on: {
                    success: function (diff_html) {
                        container.set('innerHTML', diff_html);
                        (new rc.NumberToggle()).render();
                        namespace.setup_inline_comments(previewdiff_id);
                    },
                    failure: function(ignore, response, args) {
                        Y.log('DiffNav: ' + preview_diff_uri +
                              ' - ' + response.statusText);
                        var error_note = Y.Node.create('<p />')
                            .addClass('exception')
                            .addClass('lowlight')
                            .set('text', 'Failed to fetch diff content.');
                        container.empty();
                        container.append(error_note);
                    },
                },
            };
            self.get('lp_client').get(preview_diff_uri, config);
        });
    },

    renderUI: function() {
        if (LP.cache.inline_diff_comments !== true) {
            return
        }
        var self = this;
        var container = self.get('srcNode').one('.diff-navigator');
        container.empty();
        var preview_diffs_uri = LP.cache.context.preview_diffs_collection_link;
        var config = {
            on: {
                success: function(collection) {
                    var navigator = Y.Node.create('<select >')
                        .set('name', 'available-choices');
                    collection.entries.forEach(function(pd) {
                        // XXX cprov 20140226: the date should be formatted
                        // according to the user locale/timezone similar to
                        // fmt:displaydate. We should leverage Y.Intl
                        // features. 
                        var fmt_date = 'on ' + Y.Date.format(
                            new Date(pd.get('date_created')),
                            {format: '%Y-%m-%d'});
                        var text = (pd.get('title') + ' ' + fmt_date);
                        var option = Y.Node.create('<option />')
                            .set('value', pd.get('id'))
                            .set('text', text);
                        if (LP.cache.context.preview_diff_link ==
                            pd.get('self_link')) {
                            option.set('selected', 'selected');
                        }
                        navigator.append(option);
                    });
                    container.append(navigator)
                    self._connectNavigator(navigator);
                },
                failure: function(ignore, response, args) {
                    Y.log('DiffNav: ' + preview_diffs_uri +
                          ' - ' + response.statusText)
                    var error_note = Y.Node.create('<p />')
                        .addClass('exception')
                        .addClass('lowlight')
                        .set('text', 'Failed to fetch available diffs.');
                    container.empty();
                    container.append(error_note);
                },
            }
        };
        this.get('lp_client').get(preview_diffs_uri, config);
    },

});

namespace.DiffNav = DiffNav;

}, '0.1', {requires: ['datatype-date', 'event', 'io', 'node', 'widget',
                      'lp.client', 'lp.ui.editor']});