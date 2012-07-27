/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide functionality for marking a bug as a duplicate.
 *
 * @module bugs
 * @submodule duplicates
 */
YUI.add('lp.bugs.duplicates', function(Y) {

var namespace = Y.namespace('lp.bugs.duplicates');

// Overlay related vars.
var submit_button_html =
    '<button type="submit" name="field.actions.change" ' +
    '>Save Duplicate</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    '>Cancel</button>';

/**
 * Manage the process of marking a bug as a duplicate.
 * This widget does no rendering itself; it is used to enhance existing HTML.
 */
namespace.MarkBugDuplicate = Y.Base.create("markBugDupeWidget", Y.Widget, [], {
    initializer: function(cfg) {
        this.lp_client = new Y.lp.client.Launchpad(cfg);
        this.io_provider = Y.lp.client.get_configured_io_provider(cfg);
        var update_dupe_link = cfg.update_dupe_link;
        if (update_dupe_link) {
            // Add a class denoting the link as js-action link.
            update_dupe_link.addClass('js-action');
        }
    },

    renderUI: function() {
        var update_dupe_link = this.get('update_dupe_link');
        if (!Y.Lang.isValue(update_dupe_link)) {
            return;
        }
        // Pre-load the mark-dupe form.
        var mark_dupe_form_url =
            update_dupe_link.get('href') + '/++form++';

        var form_header = '<p>Marking this bug as a duplicate will,' +
                          ' by default, hide it from search results ' +
                          'listings.</p>';

        var duplicates_div = this.get('duplicates_div');
        if (Y.Lang.isValue(duplicates_div)) {
            form_header = form_header +
                '<p class="block-sprite large-warning">' +
                '<strong>Note:</strong> ' +
                'This bug has duplicates of its own. ' +
                'If you go ahead, they too will become duplicates of ' +
                'the bug you specify here.  This cannot be undone.' +
                '</p>';
        }

        this.duplicate_form = new Y.lazr.FormOverlay({
            headerContent: '<h2>Mark bug report as duplicate</h2>',
            form_header: form_header,
            form_submit_button: Y.Node.create(submit_button_html),
            form_cancel_button: Y.Node.create(cancel_button_html),
            centered: true,
            // The form submit first searches for the bug.
            form_submit_callback:
                    Y.bind(this._find_duplicate_bug, this),
            visible: false,
            io_provider: this.io_provider
        });
        this.duplicate_form.render('#duplicate-form-container');
        this.duplicate_form.loadFormContentAndRender(
            mark_dupe_form_url);
    },

    bindUI: function () {
        // Add an on-click handler to any links found that displays
        // the form overlay.
        var update_dupe_link = this.get('update_dupe_link');
        if (!Y.Lang.isValue(update_dupe_link)) {
            return;
        }
        var that = this;
        update_dupe_link.on('click', function(e) {
            // Only go ahead if we have received the form content by the
            // time the user clicks:
            if (that.duplicate_form) {
                e.halt();
                that.duplicate_form.show();
                Y.DOM.byId('field.duplicateof').focus();
            }
        });
        // When the dupe form overlay is hidden, we need to reset the form.
        this.duplicate_form.after('visibleChange', function() {
            if (!this.get('visible')) {
                that._hide_confirm_node();
            }
        });
    },

    /**
     * Show a spinner next to the specified node.
     *
     * @method _show_bug_spinner
     * @private
     */
    _show_bug_spinner: function(node) {
        if( node === null) {
            return;
        }
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Searching..." />');
        node.insert(spinner_node, 'after');
    },

    /**
     * Hide the spinner next to the specified node.
     *
     * @method _hide_bug_spinner
     * @private
     */
    _hide_bug_spinner: function(node) {
        if( node === null) {
            return;
        }
        var spinner = node.get('parentNode').one('.spinner');
        if (spinner !== null) {
            spinner.remove();
        }
    },

    /**
     * Look up the selected bug and get the user to confirm that it is the one
     * they want.
     *
     * @param data
     * @private
     */
    _find_duplicate_bug: function(data) {
        var new_dup_id = Y.Lang.trim(data['field.duplicateof'][0]);
        // If there's no bug data entered then we are deleting the duplicate
        // link.
        if (new_dup_id === '') {
            this._update_bug_duplicate(new_dup_id);
            return;
        }
        var that = this;
        var qs_data
            = Y.lp.client.append_qs("", "ws.accept", "application.json");

        var bug_field = this.duplicate_form.form_node
            .one('[id="field.duplicateof"]');
        var config = {
            on: {
                start: function() {
                    that._show_bug_spinner(bug_field);
                    that.duplicate_form.clearError();
                },
                end: function() {
                    that._hide_bug_spinner(bug_field);
                },
                success: function(id, response) {
                    if (response.responseText === '') {
                        return;
                    }
                    var bug_data = Y.JSON.parse(response.responseText);
                    that._confirm_selected_bug(bug_data);
                },
                failure: function(id, response) {
                    var error_msg;
                    if (response.status === 404) {
                        error_msg = new_dup_id +
                            ' is not a valid bug number.';
                    } else {
                        error_msg = response.responseText;
                    }
                    that.duplicate_form.showError(error_msg);
                }
            },
            data: qs_data
        };
        var uri
            = Y.lp.client.get_absolute_uri("/api/devel/bugs/" + new_dup_id);
        this.io_provider.io(uri, config);
    },

    // Template for rendering the bug details.
    _bug_details_template: function() {
        return [
        '<div id="client-listing">',
        '  <div class="buglisting-col1">',
        '      <div class="importance {{importance_class}}">',
        '          {{importance}}',
        '      </div>',
        '      <div class="status {{status_class}}">',
        '          {{status}}',
        '      </div>',
        '      <div class="buginfo-extra">',
        '              <div class="information_type">',
        '                  {{information_type}}',
        '              </div>',
        '      </div>',
        '  </div>',
        '  <div class="buglisting-col2" style="max-width: 60em;">',
        '      <span class="bugnumber">#{{id}}</span>',
        '      <a href="{{bug_url}}" class="bugtitle">{{bug_summary}}</a>',
        '      <div class="buginfo-extra">',
        '          <p class="ellipsis line-block" style="max-width: 70em;">',
        '          {{description}}</p>',
        '      </div>',
        '  </div>',
        '</div>'
        ].join(' ');
    },

    // Template for the bug confirmation form.
    _bug_confirmation_form_template: function() {
        return [
            '<div class="confirmation-node yui3-lazr-formoverlay-form" ',
            'style="margin-top: 6px;">',
            '{{> bug_details}}',
            '<div class="yui3-lazr-formoverlay-errors"></div>',
            '<div class="extra-form-buttons">',
            '  <button class="yes_button" type="button">',
            '  Save Duplicate</button>',
            '  <button class="no_button" type="button">Search Again</button>',
            '  <button class="cancel_button" type="button">Cancel</button>',
            '</div>',
            '</div>'].join('');
    },

    /**
     * Ask the user to confirm the chosen bug is the one they want.
     * @param bug_data
     * @private
     */
    _confirm_selected_bug: function(bug_data) {
        // TODO - get real data from the server
        bug_data.importance = 'High';
        bug_data.importance_class = 'importanceHIGH';
        bug_data.status = 'Triaged';
        bug_data.status_class = 'statusTRIAGED';
        bug_data.bug_summary = bug_data.title;
        bug_data.bug_url = bug_data.web_link;

        var bug_id = bug_data.id;
        var html = Y.lp.mustache.to_html(
            this._bug_confirmation_form_template(), bug_data,
            {bug_details: this._bug_details_template()});
        var confirm_node = Y.Node.create(html);
        this._show_confirm_node(confirm_node);
        var that = this;
        confirm_node.one(".yes_button")
            .on('click', function(e) {
                e.halt();
                that._update_bug_duplicate(bug_id);
            });

        confirm_node.one(".no_button")
            .on('click', function(e) {
                e.halt();
                that._hide_confirm_node(confirm_node);
            });
        confirm_node.one(".cancel_button")
            .on('click', function(e) {
                e.halt();
                that.duplicate_form.hide();
            });
    },

    // Centre the duplicate form along the x axis without changing y position.
    _xaxis_centre: function() {
        var viewport = Y.DOM.viewportRegion();
        var new_x = (viewport.right  + viewport.left)/2 -
            this.duplicate_form.get('contentBox').get('offsetWidth')/2;
        this.duplicate_form.move([new_x, this.duplicate_form._getY()]);

    },

    /** Show the bug selection confirmation node.
     * @method _show_confirm_node
     * @private
     */
    _show_confirm_node: function(confirmation_node) {
        this.duplicate_form.form_header_node
            .insert(confirmation_node, 'after');
        this.confirmation_node = confirmation_node;
        this._xaxis_centre();
        this._fade_in(confirmation_node, this.duplicate_form.form_node);
    },

    /** Hide the bug selection confirmation node.
     * @method _hide_confirm_node
     * @private
     */
    _hide_confirm_node: function() {
        this.duplicate_form.form_node.removeClass('hidden');
        if (Y.Lang.isValue(this.confirmation_node)) {
            this._fade_in(
                this.duplicate_form.form_node, this.confirmation_node);
        this._xaxis_centre();
            this.confirmation_node.remove();
            this.confirmation_node = null;
        }
    },

    // Animate the display of content.
    _fade_in: function(content_node, old_content, use_animation) {
        content_node.removeClass('hidden');
        if (old_content === null) {
            content_node.removeClass('transparent');
            content_node.setStyle('opacity', 1);
            content_node.show();
            return;
        }
        old_content.addClass('hidden');
        if (!Y.Lang.isValue(use_animation)) {
            use_animation = this.get('use_animation');
        }
        if (!use_animation) {
            old_content.setStyle('opacity', 1);
            return;
        }
        content_node.addClass('transparent');
        content_node.setStyle('opacity', 0);
        var fade_in = new Y.Anim({
            node: content_node,
            to: {opacity: 1},
            duration: 0.8
        });
        fade_in.run();
    },

    /**
     * Bug was successfully marked as a duplicate, update the UI.
     *
     * @method _update_bug_duplicate_success
     * @param updated_entry
     * @param new_dup_url
     * @param new_dup_id
     * @private
     */
    _update_bug_duplicate_success: function(updated_entry, new_dup_url,
                                           new_dup_id) {
        this.duplicate_form.hide();
        updated_entry.set('duplicate_of_link', new_dup_url);
        this.set('lp_bug_entry', updated_entry);

        var dupe_span = this.get('dupe_span');
        var update_dup_url = dupe_span.one('a').get('href');
        if (Y.Lang.isValue(new_dup_url)) {
            dupe_span.setContent([
                '<a id="change_duplicate_bug" ',
                'title="Edit or remove linked duplicate bug" ',
                'class="sprite edit action-icon">Edit</a>',
                'Duplicate of <a>bug #</a>'].join(""));
            dupe_span.all('a').item(0) .set('href', update_dup_url);
            dupe_span.all('a').item(1)
                .set('href', '/bugs/' + new_dup_id)
                .appendChild(document.createTextNode(new_dup_id));
            var duplicates_div = this.get('duplicates_div');
            if (Y.Lang.isValue(duplicates_div)) {
                duplicates_div.remove(true);
            }
            this._show_comment_on_duplicate_warning();
        } else {
            dupe_span.addClass('sprite bug-dupe');
            dupe_span.setContent([
                '<a class="menu-link-mark-dupe js-action">',
                'Mark as duplicate</a>'].join(""));
            dupe_span.one('a').set('href', update_dup_url);
            this._hide_comment_on_duplicate_warning();
        }
        var anim_duration = 1;
        if (!this.get('anim_duration')) {
            anim_duration = 0;
        }
        Y.lp.anim.green_flash({
            node: dupe_span,
            duration: anim_duration
            }).run();
        // ensure the new link is hooked up correctly:
        var that = this;
        dupe_span.one('a').on(
            'click', function(e){
                e.preventDefault();
                that.duplicate_form.show();
                Y.DOM.byId('field.duplicateof').focus();
            });
    },

    /**
     * There was an error marking a bug as a duplicate.
     *
     * @method _update_bug_duplicate
     * @param response
     * @param old_dup_url
     * @param new_dup_id
     * @private
     */
    _update_bug_duplicate_failure: function(response, old_dup_url, new_dup_id) {
        // Reset the lp_bug_entry.duplicate_of_link as it wasn't
        // updated.
        this.get('lp_bug_entry').set('duplicate_of_link', old_dup_url);
        var error_msg = response.responseText;
        if (response.status === 400) {
            var error_info = response.responseText.split('\n');
            error_msg = error_info.slice(1).join(' ');
        }
        this.confirmation_node.one('.yui3-lazr-formoverlay-errors')
            .setContent(error_msg);
        this.confirmation_node.one(".yes_button").addClass('hidden');
        this._xaxis_centre();

    },

    /**
     * Update the bug duplicate via the LP API
     *
     * @method _update_bug_duplicate
     * @param new_dup_id
     * @private
     */
    _update_bug_duplicate: function(new_dup_id) {
        // XXX noodles 2009-03-17 bug=336866 It seems the etag
        // returned by lp_save() is incorrect. Remove it for now
        // so that the second save does not result in a '412
        // precondition failed' error.
        //
        // XXX deryck 2009-04-29 bug=369293 Also, this has to
        // happen before *any* call to lp_save now that bug
        // subscribing can be done inline.  Named operations
        // don't return new objects, making the cached bug's
        // etag invalid as well.
        var lp_bug_entry = this.get('lp_bug_entry');
        lp_bug_entry.removeAttr('http_etag');

        var new_dup_url = null;
        if (new_dup_id !== '') {
            var self_link = lp_bug_entry.get('self_link');
            var last_slash_index = self_link.lastIndexOf('/');
            new_dup_url = self_link.slice(0, last_slash_index+1) + new_dup_id;
        }
        var old_dup_url = lp_bug_entry.get('duplicate_of_link');
        lp_bug_entry.set('duplicate_of_link', new_dup_url);

        var dupe_span = this.get('dupe_span');
        var that = this;
        var submit_btn = null;
        if (Y.Lang.isValue(this.confirmation_node)) {
            submit_btn = this.confirmation_node.one(".yes_button");
        }
        var config = {
            on: {
                start: function() {
                    dupe_span.removeClass('sprite bug-dupe');
                    dupe_span.addClass('update-in-progress-message');
                    that._show_bug_spinner(submit_btn);
                },
                end: function() {
                    dupe_span.removeClass('update-in-progress-message');
                    that._hide_bug_spinner(submit_btn);
                },
                success: function(updated_entry) {
                    that._update_bug_duplicate_success(
                        updated_entry, new_dup_url, new_dup_id);
                },
                failure: function(id, response) {
                    that._update_bug_duplicate_failure(
                        response, old_dup_url, new_dup_id);
                }
            }
        };
        // And save the updated entry.
        lp_bug_entry.lp_save(config);
    },

    /*
     * Ensure that a warning about adding a comment to a duplicate bug
     * is displayed.
     *
     * @method _show_comment_on_duplicate_warning
     * @private
     */
    _show_comment_on_duplicate_warning: function() {
        var duplicate_warning = Y.one('#warning-comment-on-duplicate');
        if (!Y.Lang.isValue(duplicate_warning)) {
            var container = Y.one('#add-comment-form');
            var first_node = container.get('firstChild');
            duplicate_warning = Y.Node.create(
                ['<div class="warning message"',
                 'id="warning-comment-on-duplicate">',
                 'Remember, this bug report is a duplicate. ',
                 'Comment here only if you think the duplicate status ',
                 'is wrong.',
                 '</div>'].join(''));
            container.insertBefore(duplicate_warning, first_node);
        }
    },

    /*
     * Ensure that no warning about adding a comment to a duplicate bug
     * is displayed.
     *
     * @method _hide_comment_on_duplicate_warning
     * @private
     */
    _hide_comment_on_duplicate_warning: function() {
        var duplicate_warning = Y.one('#warning-comment-on-duplicate');
        if (duplicate_warning !== null) {
            duplicate_warning.ancestor().removeChild(duplicate_warning);
        }
    }
}, {
    HTML_PARSER: {
        // Look for the 'Mark as duplicate' links or the
        // 'change duplicate bug' link.
        update_dupe_link: '.menu-link-mark-dupe, #change_duplicate_bug',
        // The rendered duplicate information.
        dupe_span: '#mark-duplicate-text'
    },
    ATTRS: {
        // The launchpad client entry for the current bug.
        lp_bug_entry: {
            value: null
        },
        // The link used to update the duplicate bug number.
        update_dupe_link: {
        },
        // The rendered duplicate information.
        dupe_span: {
        },
        // Div containing duplicates of this bug.
        duplicates_div: {
            getter: function() {
                return Y.one('#portlet-duplicates');
            }
        },
        // Override for testing.
        use_animation: {
            value: true
        }
    }
});

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "json", "lazr.formoverlay",
    "lazr.effects", "lp.app.widgets.expander", "lp.mustache",
    "lp.app.formwidgets.resizing_textarea", "plugin"]});
