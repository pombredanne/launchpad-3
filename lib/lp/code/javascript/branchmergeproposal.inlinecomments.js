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

namespace.add_doubleclick_handler = function() {
    var handling_request = false;
    handler = function(e) {
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
                delete namespace.inlinecomments[line_number];
                draft_div.remove(true);
                namespace.cleanup_empty_comment_containers();
            }
            var config = {
                on: {
                    success: function () {
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
            handling_request = false;
            draft_div.one('.boardCommentFooter').show();
        });
        widget.editor.on('cancel', function(e) {
            handling_request = false;
            draft_div.one('.boardCommentFooter').show();
            // If there's no saved comment to return to, just remove the
            // draft UI.
            if (namespace.inlinecomments[line_number] === undefined) {
                draft_div.remove(true);
                namespace.cleanup_empty_comment_containers();
            }
        });
        widget._triggerEdit(e);
        draft_div.one('.boardCommentFooter').hide();
    };

    // The editor can be invoked by double-clicking a diff line or
    // clicking the line number. Hovering over a line shows an edit icon
    // near the line number, to hint that it's clickable.
    // XXX: Introduce a separate comment column.
    Y.one('.diff').delegate('click', handler, '.boardCommentFooter a');
    Y.one('.diff').delegate('dblclick', handler, 'tr[id^="diff-line"]');
    Y.one('.diff').delegate('click', handler, 'tr[id^="diff-line"] .line-no');
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
    var comments_tr = Y.one('#comments-diff-line-' + comment.line_number);
    if (comments_tr === null) {
        var comments_tr = Y.Node.create(
            '<tr class="inline-comments">'
            + '<td colspan="2"><div></div></td></tr>')
            .set('id', 'comments-diff-line-' + comment.line_number);
        Y.one('#diff-line-' + comment.line_number)
            .insert(comments_tr, 'after');
    }
    comments_div = comments_tr.one('div');

    var newrow = Y.Node.create(
        '<div class="boardComment">' +
        '<div class="boardCommentDetails"></div>' +
        '<div class="boardCommentBody"><div></div></div>' +
        '<div class="boardCommentFooter"></div>' +
        '</div>');
    if (Y.Lang.isUndefined(comment.person)) {
        // Creates a draft inline comment area.
        newrow.addClass('draft');
        newrow.one('.boardCommentDetails').set('text', 'Unsaved comment');
        newrow.one('.boardCommentBody div')
            .append('<span class="yui3-editable_text-text"></span>')
            .append('<div class="yui3-editable_text-trigger"></div>');
        newrow.one('.boardCommentFooter')
            .append('<a class="js-action">Edit</a>');
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
        newrow.one('.boardCommentFooter')
            .append('<a class="js-action">Reply</a>');
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
            success: function (comments) {
                // Display published inline comments.
                // [{'line_number': <lineno>, 'person': <IPerson>,
                //   'text': <comment>, 'date': <timestamp>}, ...]
                comments.forEach( function (comment) {
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
        LP.cache.context.self_link, 'getInlineComments', config_published);
};

namespace.populate_drafts = function() {
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
    if (LP.cache.inline_diff_comments !== true) {
        return;
    }
    // Store the current diff ID locally.
    namespace.current_previewdiff_id = previewdiff_id;

    namespace.cleanup_comments();

    // Draft inline-comments and click-handlers do not need to be
    // loaded for anonymous requests.
    // In fact, if loading draft is attempted is will fail due to
    // the LP permission checks.
    if (LP.links['me'] !== undefined) {
        // Add the double-click handler for each row in the diff. This needs
        // to be done first since populating existing published and draft
        // comments may add more rows.
        namespace.add_doubleclick_handler();
        namespace.populate_drafts();
    }
    namespace.populate_comments();
};


var PublishDrafts = function () {
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
        this.get('contentBox').empty();
        var n_drafts = Y.all('.draft').size();
        var rc_scroller = Y.one('.review-comment-scroller');
        if (rc_scroller !== null) {
            if (n_drafts > 0) {
                var scroller_text = 'Return to save comment'
                if (n_drafts > 1) scroller_text += 's';
                rc_scroller.set('text', scroller_text);
            } else {
                rc_scroller.set('text', 'Return to add comment');
            }
        }
        if (n_drafts == 0) {
            Y.fire('CodeReviewComment.SET_DISABLED', true);
            return;
        }
        var text = ' Include ' + n_drafts + ' diff comment';
        if (n_drafts > 1) text += 's';
        var checkbox = Y.Node.create(
            '<input id="field.publish_inline_comments"' +
            'name="field.publish_inline_comments"' +
            'type="checkbox" class="checkboxType"' +
            'checked=""></input>')
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


var InlineCommentToggle = function () {
    InlineCommentToggle.superclass.constructor.apply(this, arguments);
};

Y.mix(InlineCommentToggle, {

    NAME: 'inlinecommenttoggle',

    ATTRS: {
    }

});

Y.extend(InlineCommentToggle, Y.Widget, {

    renderUI: function() {
        if (LP.cache.inline_diff_comments !== true) {
            return;
        }
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
        Y.all('.inline-comments').each( function() {
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
    initializer: function(cfg){
        // If we have not been provided with a Launchpad Client, then
        // create one now:
        if (null === this.get("lp_client")){
            // Create our own instance of the LP client.
            this.set("lp_client", new Y.lp.client.Launchpad());
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
        if (LP.cache.inline_diff_comments !== true) {
            return;
        }
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
        Y.all('td[data-previewdiff-id]').each( function(td) {
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
            .addClass('review-comment-scroller')
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
                success: function (diff_html) {
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
        this._updateDiff(preview_diff_uri);
    },

    /**
     * Render diff navigator contents (navigator and diff area).
     *
     * @method renderUI
     */
    renderUI: function() {
        var self = this;
        if (LP.cache.inline_diff_comments !== true) {
            var preview_diff_uri = (LP.cache.context.web_link + '/++diff');
            self._updateDiff(preview_diff_uri);
            return;
        }

        var pub_drafts_anchor = Y.one('[id="field.review_type"]');
        if (pub_drafts_anchor !== null) {
            var pub_drafts_container = Y.one('.publish_drafts_container')
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

namespace.DiffNav = DiffNav;

}, '0.1', {requires: ['datatype-date', 'event', 'io', 'node', 'widget',
                      'lp.client', 'lp.ui.editor']});
