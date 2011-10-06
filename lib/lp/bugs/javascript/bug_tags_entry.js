/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Inline bug tags entry with auto suggestion.
 *
 * @module bugs
 * @submodule bug_tags_entry
 */

YUI.add('lp.bugs.bug_tags_entry', function(Y) {

var namespace = Y.namespace('lp.bugs.bug_tags_entry');

var bug_tags_div;
var edit_tags_trigger;
var add_tags_trigger;
var tag_list_span;
var tag_input;
var ok_button;
var cancel_button;
var tags_edit_spinner;
var tags_form;
var available_tags;
var autocomplete;

var DISPLAY = 'display',
    NONE = 'none',
    INLINE = 'inline',
    A = 'a',
    VALUE = 'value',
    BUG = 'bug',
    INNER_HTML = 'innerHTML',
    ESCAPE = 27,
    TAGS_SHOW = 'tags-show',
    TAGS_HIDE = 'tags-hide';

/**
 * Grab all existing tags and insert them into the input
 * field for editing.
 *
 * @method populate_tags_input
 */
var populate_tags_input = function() {
    var tags = [];

    tag_list_span.all(A).each(function(anchor) {
        tags.push(anchor.get(INNER_HTML));
    });
    
    var tag_list = tags.join(' ');
    /* If there are tags then add a space to the end of the string so the user 
       doesn't have to type one. */
    if (tag_list != "") {
        tag_list += ' ';
    }
    tag_input.set(VALUE, tag_list);
};

/**
 * The base URL for tag searches. Append a tag to get a tag search URL.
 */
var base_url = window.location.href.split('/+bug')[0] + '/+bugs?field.tag=';

/**
 * Save the currently entered tags and switch inline editing off.
 *
 * @method save_tags
 */
var save_tags = function() {
    var lp_client = new Y.lp.client.Launchpad();
    var tags = Y.Array(
        Y.Lang.trim(tag_input.get(VALUE)).split(new RegExp('\\s+'))).filter(
            function(elem) { return elem !== ''; });
    var bug = new Y.lp.client.Entry(
        lp_client, LP.cache[BUG], LP.cache[BUG].self_link);
    bug.removeAttr('http_etag');
    bug.set('tags', tags);
    tags_edit_spinner.setStyle(DISPLAY, INLINE);
    ok_button.setStyle(DISPLAY, NONE);
    cancel_button.setStyle(DISPLAY, NONE);
    bug.lp_save({on : {
        success: function(updated_entry) {
            var official_tags = [];
            var unofficial_tags = [];
            Y.each(updated_entry.get('tags'), function(tag) {
                if (available_tags.indexOf(tag) > -1) {
                    official_tags.push(tag);
                } else {
                    unofficial_tags.push(tag);
                }
            });
            official_tags.sort();
            unofficial_tags.sort();
            var tags_html = Y.Array(official_tags).map(function(tag) {
                return Y.Lang.substitute(
                    '<a href="{tag_url}" class="official-tag">{tag}</a>',
                    {tag_url: base_url + tag, tag: tag});
            }).join(' ') + ' ' + Y.Array(unofficial_tags).map(function(tag) {
                return Y.Lang.substitute(
                    '<a href="{tag_url}" class="unofficial-tag">{tag}</a>',
                    {tag_url: base_url + tag, tag: tag});
            }).join(' ');
            tag_list_span.set(INNER_HTML, tags_html);
            tag_input.setStyle(DISPLAY, NONE);
            tag_list_span.setStyle(DISPLAY, INLINE);
            ok_button.setStyle(DISPLAY, NONE);
            cancel_button.setStyle(DISPLAY, NONE);
            edit_tags_trigger.setStyle(DISPLAY, INLINE);
            tags_edit_spinner.setStyle(DISPLAY, NONE);
            Y.lp.anim.green_flash({ node: tag_list_span }).run();
            if (Y.Lang.trim(tags_html) === '') {
                Y.one('#bug-tags').removeClass(TAGS_SHOW);
                Y.one('#bug-tags').addClass(TAGS_HIDE);
                Y.one('#add-bug-tags').removeClass(TAGS_HIDE);
                Y.one('#add-bug-tags').addClass(TAGS_SHOW);
            }
        },
        failure: function(id, request) {
            tags_edit_spinner.setStyle(DISPLAY, NONE);
            Y.lp.anim.green_flash({ node: tag_list_span }).run();
        }
    }});
};

/**
 * Cancel editing - hide the inline editor and restore the tags display.
 *
 * @method cancel
 */
var cancel = function() {
    tag_input.setStyle(DISPLAY, NONE);
    tag_list_span.setStyle(DISPLAY, INLINE);
    ok_button.setStyle(DISPLAY, NONE);
    cancel_button.setStyle(DISPLAY, NONE);
    edit_tags_trigger.setStyle(DISPLAY, INLINE);
    tags_edit_spinner.setStyle(DISPLAY, NONE);
    autocomplete.hide();
    Y.lp.anim.red_flash({ node: tag_list_span }).run();
    if (Y.Lang.trim(tag_list_span.get('innerHTML')) === '') {
        Y.one('#bug-tags').removeClass(TAGS_SHOW);
        Y.one('#bug-tags').addClass(TAGS_HIDE);
        Y.one('#add-bug-tags').removeClass(TAGS_HIDE);
        Y.one('#add-bug-tags').addClass(TAGS_SHOW);
    }
};

/**
 * Start editing - show the inline editor and populate it.
 *
 * @method edit
 */
var edit = function() {
    populate_tags_input();
    tag_list_span.setStyle(DISPLAY, NONE);
    tag_input.setStyle(DISPLAY, INLINE);
    tag_input.focus();
    edit_tags_trigger.setStyle(DISPLAY, NONE);
    ok_button.setStyle(DISPLAY, INLINE);
    cancel_button.setStyle(DISPLAY, INLINE);
    autocomplete.render();
};

/**
 * Set up inline tag editing on a bug page.
 *
 * @method setup_tag_entry
 */
namespace.setup_tag_entry = function(available_official_tags) {
    if (LP.links.me === undefined) { return; }

    available_tags = Y.Array(available_official_tags);
    bug_tags_div = Y.one('#bug-tags');
    edit_tags_trigger = bug_tags_div.one('#edit-tags-trigger');
    add_tags_trigger = Y.one('#add-tags-trigger');
    tag_list_span = bug_tags_div.one('#tag-list');
    tag_input = bug_tags_div.one('#tag-input');
    ok_button = bug_tags_div.one('#edit-tags-ok');
    cancel_button = bug_tags_div.one('#edit-tags-cancel');
    tags_edit_spinner = bug_tags_div.one('#tags-edit-spinner');
    tags_form = bug_tags_div.one('#tags-form');

    edit_tags_trigger.on('click', function(e) {
        e.halt();
        edit();
    });

    add_tags_trigger.on('click', function(e) {
        e.halt();
        Y.one('#bug-tags').removeClass(TAGS_HIDE);
        Y.one('#bug-tags').addClass(TAGS_SHOW);
        Y.one('#add-bug-tags').removeClass(TAGS_SHOW);
        Y.one('#add-bug-tags').addClass(TAGS_HIDE);
        edit();
    });

    cancel_button.on('click', function(e) {
        e.halt();
        cancel();
    });

    ok_button.on('click', function(e) {
        e.halt();
        save_tags();
        /* Check to see if the autocomplete dialogue is still open
           and if so, close it. */
        if (!autocomplete._last_input_was_completed) {
            autocomplete.hide();
        }
    });

    tag_input.on('keydown', function(e) {
        if (e.keyCode == ESCAPE) {
            e.halt();
            cancel();
        }
    });

    tags_form.on('submit', function(e) {
        e.halt();
        save_tags();
    });

    // We indicate that the links are AJAXified before the AutoComplete
    // widget is set up, since the AutoComplete isn't needed to edit the
    // tags inline.
    add_tags_trigger.addClass('js-action');
    edit_tags_trigger.addClass('js-action');

    autocomplete = new Y.lazr.AutoComplete({
        input: '#tag-input',
        data: available_official_tags,
        boundingBox: '#tags-autocomplete',
        contentBox: '#tags-autocomplete-content'
    });

    autocomplete.on('queryChange', function(e) {
        var val = "null";
        if (e.newVal !== null) {
            val = "'" + e.newVal.text + "', " + e.newVal.offset;
        }
    });
};
}, "0.1", {"requires": ["base", "io-base", "node", "substitute", "node-menunav",
                        "lazr.base", "lp.anim", "lazr.autocomplete",
                        "lp.client"]});

