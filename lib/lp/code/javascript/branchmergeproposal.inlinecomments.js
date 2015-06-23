/* Copyright 2014-2015 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for handling inline comments in diffs.
 *
 * @module lp.code.branchmergeproposal.inlinecomments
 * @requires node
 */

YUI.add('lp.code.branchmergeproposal.inlinecomments', function(Y) {

if (typeof window.KeyEvent === "undefined") {
    window.KeyEvent = {
        DOM_VK_RETURN: 13,
        DOM_VK_H: 72,
        DOM_VK_J: 74,
        DOM_VK_K: 75,
        DOM_VK_L: 76,
        DOM_VK_N: 78,
        DOM_VK_P: 80
    };
}

// Grab the namespace in order to be able to expose the connect methods.
var namespace = Y.namespace('lp.code.branchmergeproposal.inlinecomments');

namespace.inlinecomments = null;

namespace.current_previewdiff_id = null;

namespace.lp_client = new Y.lp.client.Launchpad();

namespace.cleanup_empty_comment_containers = function() {
    Y.one('.diff').all('tr.inline-comments > td > div:empty').each(
        function(node) {
            node.ancestor('tr.inline-comments').remove(true);
        });
};

namespace.find_line_number = function(element) {
    var text_row = element.ancestor('tr', true);
    if (text_row.hasClass('inline-comments')) {
        text_row = text_row.previous();
    }
    return text_row.one('.line-no').get('text');
};

namespace.delete_draft = function(draft_div) {
    var line_number = namespace.find_line_number(draft_div);
    delete namespace.inlinecomments[line_number];
    draft_div.remove(true);
    namespace.cleanup_empty_comment_containers();
    namespace.init_keynav();
};

namespace.flush_drafts_to_server = function() {
    var config = {
        on: {
            success: function() {
                Y.fire('inlinecomment.UPDATED');
            }
        },
        parameters: {
            previewdiff_id: namespace.current_previewdiff_id,
            comments: namespace.inlinecomments
        }
    };
    namespace.lp_client.named_post(
        LP.cache.context.self_link, 'saveDraftInlineComment', config);
};

namespace.add_doubleclick_handler = function() {
    var handling_request = false;
    var edit_handler = function(e) {
        if (handling_request === true) {
            return;
        }
        handling_request = true;
        // Retrieve or create a container for the comment editor.
        var line_number = namespace.find_line_number(e.currentTarget);
        var draft_div = Y.one('#comments-diff-line-' + line_number + ' .draft');
        if (draft_div === null) {
            draft_div = namespace.create_row({'line_number': line_number});
        }
        var widget = new Y.EditableText({
            contentBox: draft_div.one('.boardCommentBody div'),
            initial_value_override: namespace.inlinecomments[line_number],
            accept_empty: true,
            multiline: true,
            buttons: 'top'
        });
        widget.render();
        widget.editor.on('save', function() {
            namespace.inlinecomments[line_number] = this.get('value');
            if (this.get('value') === '') {
                namespace.delete_draft(draft_div);
            }
            namespace.flush_drafts_to_server();
            handling_request = false;
            draft_div.one('.boardCommentFooter').show();
            draft_div.one('.editorShortcutTip').remove();
             // firefox retains focus, preventing nav.
            document.activeElement.blur();
            namespace.init_keynav();
        });
        widget.editor.on('keydown', function(e) {
           if (e.domEvent.ctrlKey === true &&
               e.domEvent.button === window.KeyEvent.DOM_VK_RETURN) {
               this.save();
           }
        });
        widget.editor.on('cancel', function(e) {
            handling_request = false;
            draft_div.one('.boardCommentFooter').show();
            draft_div.one('.editorShortcutTip').remove();
            // If there's no saved comment to return to, just remove the
            // draft UI.
            if (namespace.inlinecomments[line_number] === undefined) {
                draft_div.remove(true);
                namespace.cleanup_empty_comment_containers();
            }
        });
        widget._triggerEdit(e);
        draft_div.one('.boardCommentFooter').hide();
        draft_div.one('.boardCommentDetails')
          .append('<div class="editorShortcutTip">' +
                  '[Esc] Cancel, [Ctrl+Enter] Save' +
                  '</div>');
    };
    var delete_handler = function(e) {
        var line_number = namespace.find_line_number(e.currentTarget);
        var draft_div = Y.one('#comments-diff-line-' + line_number + ' .draft');
        namespace.delete_draft(draft_div);
        namespace.flush_drafts_to_server();
    };
    // The editor can be invoked by double-clicking a diff line or
    // clicking the line number. Hovering over a line shows an edit icon
    // near the line number, to hint that it's clickable.
    // XXX: Introduce a separate comment column.
    Y.one('.diff').delegate(
        'click', edit_handler, '.boardCommentFooter a.draft-edit');
    Y.one('.diff').delegate(
        'click', delete_handler, '.boardCommentFooter a.draft-delete');
    Y.one('.diff').delegate('dblclick', edit_handler, 'tr[id^="diff-line"]');
    Y.one('.diff').delegate(
        'click', edit_handler, 'tr[id^="diff-line"] .line-no');
    Y.one('.diff').delegate('hover',
        function(e) {
            e.currentTarget.one('.line-no').addClass('active');
        },
        function(e) {
            e.currentTarget.one('.line-no').removeClass('active');
        },
        'tr[id^="diff-line"]');
};

namespace.create_row = function(comment) {
    // Find or create the container for this line's comments.
    var comments_tr = Y.one('#comments-diff-line-' +
                            comment.line_number),
        comment_date;

    if (comments_tr === null) {
        if (Y.all('table.ssdiff').size() > 0) {
            colspan = 4;
        } else {
            colspan = 2;
        }
        comments_tr = Y.Node.create(
            '<tr class="inline-comments">' +
            '<td class="inline-comment" colspan="' + colspan + '">' +
            '<div></div></td></tr>')
            .set('id', 'comments-diff-line-' + comment.line_number);
        Y.one('#diff-line-' + comment.line_number)
            .insert(comments_tr, 'after');
    }
    comments_div = comments_tr.one('div');

    var newrow = Y.Node.create(
        '<div class="boardComment">' +
        '<div class="boardCommentDetails"></div>' +
        '<div class="boardCommentBody"><div></div></div>' +
        '</div>');
    if (Y.Lang.isUndefined(comment.person)) {
        // Creates a draft inline comment area.
        newrow.addClass('draft');
        newrow.append('<div class="boardCommentFooter"></div>');
        newrow.one('.boardCommentDetails').set('text', 'Unsaved comment');
        newrow.one('.boardCommentBody div')
            .append('<span class="yui3-editable_text-text"></span>')
            .append('<div class="yui3-editable_text-trigger"></div>');
        newrow.one('.boardCommentFooter')
            .append('<a class="js-action draft-edit">Edit</a>')
            .append('<a class="js-action draft-delete">Delete</a>');
        if (!Y.Lang.isUndefined(comment.text)) {
            namespace.inlinecomments[comment.line_number] = comment.text;
            newrow.one('span').set('text', comment.text);
        }
    } else {
        // Creates a published inline comment area.
        var headerspan = Y.Node.create(
            '<span><a class="sprite person"></a> wrote <span></span>:</span>');
        // Wrap resources coming from LP.cache, as they come from
        // the LP API (updates during the page life-span). This way
        // the handling code can be unified.
        if (LP.links.me !== undefined) {
            newrow.append('<div class="boardCommentFooter"></div>');
            newrow.one('.boardCommentFooter')
                .append('<a class="js-action draft-edit">Reply</a>');
        }
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
        if (typeof comment.date === 'string') {
            comment_date = Y.lp.app.date.parse_date(comment.date);
        } else {
            comment_date = comment.date;
        }
        var date = Y.lp.app.date.approximatedate(comment_date);
        headerspan.one('span').set('text', date);
        newrow.one('.boardCommentDetails').append(headerspan);
        newrow.one('.boardCommentBody div').append('<span></span>');
        newrow.one('.boardCommentBody').one('span').set('text', comment.text);
    }

    // Ensure that drafts always end up at the end.
    var maybe_draft = comments_div.one('.draft');
    if (comment.person !== undefined && maybe_draft !== null) {
        maybe_draft.insert(newrow, 'before');
    } else {
        comments_div.appendChild(newrow);
    }
    return newrow;
};

namespace.cleanup_comments = function() {
    // Cleanup existing inline review comments.
    Y.all('.inline-comments').remove(true);
};

namespace.populate_comments = function() {
    var config_published = {
        on: {
            success: function(comments) {
                // Display published inline comments.
                // [{'line_number': <lineno>, 'person': <IPerson>,
                //   'text': <comment>, 'date': <timestamp>}, ...]
                comments.forEach(function(comment) {
                    namespace.create_row(comment);
                });
                Y.fire('inlinecomment.UPDATED');
                // Initialise key event navigation
                namespace.init_keynav();
            }
        },
        parameters: {
            previewdiff_id: namespace.current_previewdiff_id
        }
    };
    namespace.lp_client.named_get(
        LP.cache.context.self_link, 'getInlineComments', config_published);
};

namespace.populate_drafts = function() {
    var config_draft = {
        on: {
            success: function(drafts) {
                namespace.inlinecomments = {};
                if (drafts === null) {
                    return;
                }
                // Display draft inline comments:
                // {'<line_number>':''<comment>', ...})
                Object.keys(drafts).forEach(function(line_number) {
                    var comment = {
                        'line_number': line_number,
                        'text': drafts[line_number]
                    };
                    namespace.create_row(comment);
                });
                Y.fire('inlinecomment.UPDATED');
            }
        },
        parameters: {
            previewdiff_id: namespace.current_previewdiff_id
        }
    };
    namespace.lp_client.named_get(
        LP.cache.context.self_link, 'getDraftInlineComments', config_draft);
};

namespace.setup_inline_comments = function(previewdiff_id) {
    // Store the current diff ID locally.
    namespace.current_previewdiff_id = previewdiff_id;

    namespace.cleanup_comments();

    // Draft inline-comments and click-handlers do not need to be
    // loaded for anonymous requests.
    // In fact, if loading draft is attempted is will fail due to
    // the LP permission checks.
    if (LP.links.me !== undefined) {
        // Add the double-click handler for each row in the diff. This needs
        // to be done first since populating existing published and draft
        // comments may add more rows.
        namespace.add_doubleclick_handler();
        namespace.populate_drafts();
    }
    namespace.populate_comments();
};


var PublishDrafts = function() {
    PublishDrafts.superclass.constructor.apply(this, arguments);
};

Y.mix(PublishDrafts, {

    NAME: 'publishdrafts',

    ATTRS: {
    }

});

Y.extend(PublishDrafts, Y.Widget, {

    /**
     * syncUI implementation for PublishDrafts.
     *
     * Modifies the CodeReviewComment widget, by enable/disable it and
     * adding/removing its 'publish_inline_comments' field according to
     * the presence of draft inline comments to be published.
     *
     * @method syncUI
     */
    syncUI: function() {
        var n_drafts = Y.all('.draft').size(),
            rc_scroller = Y.one('.review-comment-scroller'),
            scroller_text = '';

        this.get('contentBox').empty();
        if (rc_scroller !== null) {
            if (n_drafts > 0) {
                scroller_text = 'Return to save comment';
                if (n_drafts > 1) { scroller_text += 's'; }
                rc_scroller.set('text', scroller_text);
            } else {
                rc_scroller.set('text', 'Return to add comment');
            }
        }
        if (n_drafts === 0) {
            Y.fire('CodeReviewComment.SET_DISABLED', true);
            return;
        }
        var text = ' Include ' + n_drafts + ' diff comment';
        if (n_drafts > 1) { text += 's'; }
        var checkbox = Y.Node.create(
            '<input id="field.publish_inline_comments"' +
            'name="field.publish_inline_comments"' +
            'type="checkbox" class="checkboxType"' +
            'checked=""></input>');
        var label = Y.Node.create(
            '<label for="field.publish_inline_comments" />')
            .set('text', text);
        this.get('contentBox').append(checkbox).append(label);
        Y.fire('CodeReviewComment.SET_DISABLED', false);
    },

    /**
     * bindUI implementation for PublishDrafts.
     *
     * Simply hook syncUI() to 'inlinecomment.UPDATE' events.
     *
     * @method bindUI
     */
    bindUI: function() {
        Y.detach('inlinecomment.UPDATED');
        Y.on('inlinecomment.UPDATED', this.syncUI, this);
    }

});

namespace.PublishDrafts = PublishDrafts;


var InlineCommentToggle = function() {
    InlineCommentToggle.superclass.constructor.apply(this, arguments);
};

Y.mix(InlineCommentToggle, {

    NAME: 'inlinecommenttoggle',

    ATTRS: {
    }

});

Y.extend(InlineCommentToggle, Y.Widget, {

    renderUI: function() {
        var ui = Y.Node.create('<li><label>' +
            '<input type="checkbox" checked="checked" id="show-ic"/>' +
            '&nbsp;Show comments</label></li>');
        var ul = Y.one('#review-diff div div ul.horizontal');
        if (ul) {
            ul.appendChild(ui);
        }
    },

    bindUI: function() {
        var cb = Y.one('#show-ic');
        if (cb === null) {
            return;
        }
        var self = this;
        cb.on('click', function() {
            self.showIC(cb.get('checked'));
        });
    },

    showIC: function(display) {
        var css_display = 'none';
        if (display) {
            css_display = 'table-row';
        }
        Y.all('.inline-comments').each(function() {
            this.setStyle('display', css_display);
            this.next().setStyle('display', css_display);
        });
    }
});

namespace.InlineCommentToggle = InlineCommentToggle;


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

        previewdiff_id: {
            value: null
        },

        navigator: {
            getter: function() {return this.get('srcNode').one('select');},
            setter: function(navigator) {
                var container = this.get('srcNode').one('.diff-navigator');
                container.append(navigator);
                var self = this;
                navigator.on('change', function() {
                    self._showPreviewDiff(this.get('value'));
                });
                this._connectScrollers();
                this._showPreviewDiff(navigator.get('value'));
            }
        }

    }

});


Y.extend(DiffNav, Y.Widget, {

    /**
     * The initializer method that is called from the base Plugin class.
     *
     * @method initializer
     * @protected
     */
    initializer: function(cfg) {
        // If we have not been provided with a Launchpad Client, then
        // create one now:
        if (null === this.get('lp_client')) {
            // Create our own instance of the LP client.
            this.set('lp_client', new Y.lp.client.Launchpad());
        }
    },

    /**
     * Add the spinner image to the diff section title.
     *
     * @method set_status_updating
     */
    set_status_updating: function() {
       var image = Y.Node.create('<img />')
           .set('src', '/@@/spinner')
           .set('title', 'Updating diff ...');
       this.get('srcNode').one('h2').append(image);
    },

    /**
     * Run finishing tasks after the diff content is updated.
     *
     * @method updated
     */
    set_status_updated: function() {
        var rc = Y.lp.code.branchmergeproposal.reviewcomment;
        (new rc.NumberToggle()).render();
        (new namespace.InlineCommentToggle()).render();
        if (this.get('previewdiff_id')) {
            namespace.setup_inline_comments(this.get('previewdiff_id'));
        }
    },

    /**
     * Remove the spinner image from the diff section title.
     *
     * @method cleanup_status
     */
    cleanup_status: function() {
        this.get('srcNode').all('h2 img').remove(true);
    },

    /**
     * Update diff status on new review comments
     *
     * @method update_on_new_comment
     */
    update_on_new_comment: function() {
        namespace.cleanup_comments();
        namespace.populate_comments();
        namespace.populate_drafts();
        this._connectScrollers();
    },

    /**
     * Helper method to connect all inline-comment-scroller links to the
     * to the diff navigator.
     *
     * @method _connectScrollers
     */
    _connectScrollers: function() {
        var self = this;
        var rc = Y.lp.code.branchmergeproposal.reviewcomment;
        Y.all('td[data-previewdiff-id]').each(function(td) {
            // Comments from superseded MPs should be ignored.
            if (td.getData('from-superseded') === 'True') {
                return;
            }
            var previewdiff_id = td.getData('previewdiff-id');
            var comment_id = td.getData('comment-id');
            // We have to remove the old scrollers otherwise they will
            // fire multiple 'click' handlers (and animations).
            var scroller = td.one('.ic-scroller');
            if (scroller !== null) {
               scroller.remove(true);
            }
            scroller = Y.Node.create(
                '<a href="" class="ic-scroller" style="float: right;">' +
                'Show diff comments</a>');
            td.append(scroller);
            rc.link_scroller(scroller, '#review-diff', function() {
                self._showPreviewDiff(previewdiff_id);
            });
        });

        var rc_scroller = Y.one('.review-comment-scroller');
        if (rc_scroller !== null) {
            return;
        }
        rc_scroller = Y.Node.create('<a href="">Return to add comment</a>')
            .addClass('review-comment-scroller');
        this.get('srcNode').append(rc_scroller);
        rc.link_scroller(rc_scroller, '#add-comment-form', function() {
            if (Y.all('.draft').size() > 0) {
                Y.one('#add-comment-form input[type=submit]').focus();
            } else {
                Y.one('#add-comment-form textarea').focus();
            }
        });
    },

    /**
     * Helper method to update diff-content area according to given
     * diff content uri
     *
     * @method _updateDiff
     */
    _updateDiff: function(preview_diff_uri) {
        var self = this;
        var container = this.get('srcNode').one('.diff-content');
        var config = {
            on: {
                success: function(diff_html) {
                    container.set('innerHTML', diff_html);
                    self.set_status_updated();
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
                start: function() {
                    self.set_status_updating();
                },
                end: function() {
                    self.cleanup_status();
                }
            }
        };
        this.get('lp_client').get(preview_diff_uri, config);
    },

    /**
     * Helper method to show the previewdiff for the given id.
     * Do nothing if the current content is already displayed.
     *
     * @method _showPreviewDiff
     */
    _showPreviewDiff: function(previewdiff_id) {
        var navigator = this.get('navigator');
        if (!Y.Lang.isValue(navigator)) {
           // DiffNav was not properly initialised.
           return;
        }
        if (this.get('previewdiff_id') === previewdiff_id) {
            // The requested diff is already presented.
            return;
        }
        navigator.set('value', previewdiff_id);
        this.set('previewdiff_id', previewdiff_id);
        var preview_diff_uri = (
            LP.cache.context.web_link +
            '/+preview-diff/' + previewdiff_id + '/+diff');
        var qs = window.location.search;
        var query = Y.QueryString.parse(qs.replace(/^[?]/, ''));
        if (query.ss) {
            preview_diff_uri += '?ss=1';
        }
        this._updateDiff(preview_diff_uri);
    },

    /**
     * Render diff navigator contents (navigator and diff area).
     *
     * @method renderUI
     */
    renderUI: function() {
        var self = this;

        var pub_drafts_anchor = Y.one('[id="field.review_type"]');
        if (pub_drafts_anchor !== null) {
            var pub_drafts_container = Y.one('.publish_drafts_container');
            if (pub_drafts_container === null) {
                pub_drafts_container = Y.Node.create(
                    '<div class="publish_drafts_container">');
                pub_drafts_anchor.insert(pub_drafts_container, 'after');
            }
            (new namespace.PublishDrafts(
                {'contentBox': pub_drafts_container})).render();
        }

        var container = this.get('srcNode').one('.diff-navigator');
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
                        if (LP.cache.context.preview_diff_link ===
                            pd.get('self_link')) {
                            option.set('selected', 'selected');
                        }
                        navigator.append(option);
                    });
                    self.set('navigator', navigator);
                },
                failure: function(ignore, response, args) {
                    Y.log('DiffNav: ' + preview_diffs_uri +
                          ' - ' + response.statusText);
                    var error_note = Y.Node.create('<p />')
                        .addClass('exception')
                        .addClass('lowlight')
                        .set('text', 'Failed to fetch available diffs.');
                    container.append(error_note);
                },
                start: function() {
                    self.set_status_updating();
                },
                end: function() {
                    self.cleanup_status();
                }
            }
        };
        this.get('lp_client').get(preview_diffs_uri, config);
    }

});

namespace.init_keynav = function() {
    var diff_nav_keys = [window.KeyEvent.DOM_VK_H,
                         window.KeyEvent.DOM_VK_J,
                         window.KeyEvent.DOM_VK_K,
                         window.KeyEvent.DOM_VK_L,
                         window.KeyEvent.DOM_VK_N,
                         window.KeyEvent.DOM_VK_P];

    namespace.headers = namespace.get_headers();
    namespace.set_comments(namespace.headers);
    if (!namespace.scrollPos) {
        namespace.scrollPos = -1;
    } else {
        // retain scroll position if inline comment added.
        namespace.scrollPos = namespace.scrollPos + 1;
    }

    if (!namespace.handle_nav_keys_attached) {
        Y.one('body').on('key', namespace.handle_nav_keys,
                         'down:' + diff_nav_keys.join(','));
    }
    namespace.handle_nav_keys_attached = true;
};

namespace.get_headers = function() {
    return document.querySelectorAll(
        'table.diff td.diff-file, table.diff td.diff-chunk, ' +
        'table.diff td.inline-comment');
};

namespace.set_comments = function(headers) {
    var i;
    delete namespace.comment_idx;
    // Set first and last comment indicies, allowing for nav fallthough.
    for (i = 0; i < headers.length; i++) {
        if (!namespace.comment_idx
            && namespace.header_has_type(headers[i], 'comment')) {
                namespace.comment_idx = {'first':  i};
            }
        if (namespace.comment_idx
            && namespace.header_has_type(headers[i], 'comment')) {
            namespace.comment_idx.last = i;
        }
    }
};

namespace.add_nav_cursor = function(headers, row) {
    Y.all('.nav-cursor').removeClass('nav-cursor');
    Y.one(row.children[0]).addClass('nav-cursor');
};

namespace.get_header_row = function(headers, pos) {
    // XXX blr 20150407: Workaround for rare case where the headers collection
    // inexplicably loses parentNodes.
    if (!headers[pos].parentNode) {
        namespace.headers = namespace.get_headers();
        headers = namespace.headers;
    }
    return {'row': headers[pos].parentNode, 'pos': pos};
};

namespace.header_has_type = function(header, type) {
    return header.className.indexOf(type) > -1;
};

namespace.get_next_header = function(headers, type, direction) {
    var cursor = namespace.scrollPos;
    var i;
    if (headers.length <= 1) {
        return namespace.get_header_row(headers, 0);
    }
    if (direction === 'forwards') {
        for (i=cursor + 1; i < headers.length; i++) {
            if (namespace.header_has_type(headers[i], type)) {
                return namespace.get_header_row(headers, i);
            }
        }
    } else {
        if (cursor >= -1 && cursor <= 1) { cursor = headers.length; }
        for (i=cursor - 1; i > -1; --i) {
            if (namespace.header_has_type(headers[i], type)) {
                return namespace.get_header_row(headers, i);
            }
        }
    }
    // fallthrough case sets state to first header, chunk or comment.
    switch (type) {
    case 'comment':
        if (namespace.comment_idx) {
            if (direction === 'forwards') {
                return namespace.get_header_row(headers,
                                                namespace.comment_idx.first);
            } else {
                return namespace.get_header_row(headers,
                                                namespace.comment_idx.last);
            }
        }
        break;
    case 'chunk':
        return namespace.get_header_row(headers, 1);
    default:
        return namespace.get_header_row(headers, 0);
    }
};

namespace.scroll_to_header = function(type, direction) {
    if (namespace.headers.length > 0) {
        var header = namespace.get_next_header(
            namespace.headers, type, direction);
        if (!header) { return; }
        if (type !== 'comment') {
            namespace.add_nav_cursor(namespace.headers, header.row);
        }
        namespace.scrollPos = header.pos;
        header.row.scrollIntoView({block: 'start', behavior: 'smooth'});
    }
};

/*
 * Vim style bindings for diff previews. n/p (hunks), j/k (files)
 */
namespace.handle_nav_keys = function(e) {
    // Do not respond to keydown events for modkeys or when elements
    // have focus.
    if (e.altKey || e.ctrlKey || e.shiftKey ||
        document.querySelector(":focus")) {
        return;
    }
    if (e.button === window.KeyEvent.DOM_VK_H) {
        namespace.scroll_to_header('comment', 'forwards');
    }
    if (e.button === window.KeyEvent.DOM_VK_L) {
        namespace.scroll_to_header('comment', 'backwards');
    }
    if (e.button === window.KeyEvent.DOM_VK_J) {
        namespace.scroll_to_header('file', 'forwards');
    }
    if (e.button === window.KeyEvent.DOM_VK_K) {
        namespace.scroll_to_header('file', 'backwards');
    }
    if (e.button === window.KeyEvent.DOM_VK_N) {
        namespace.scroll_to_header('chunk', 'forwards');
    }
    if (e.button === window.KeyEvent.DOM_VK_P) {
        namespace.scroll_to_header('chunk', 'backwards');
    }
};

namespace.DiffNav = DiffNav;

}, '0.1', {requires: ['datatype-date', 'event', 'io', 'node',
                      'querystring-parse', 'widget',
                      'lp.client', 'lp.ui.editor', 'lp.app.date']});
