/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Official bug tags management user interface.
 *
 * @module BugTagsEntry
 * @requires base, node, substitute
 */

YUI.add('bugs.bug_tags_entry', function(Y) {

var bugs = Y.namespace('bugs');

var bug_tags_div;
var edit_tags_trigger;
var tag_list_span;
var tag_input;
var ok_button;
var cancel_button;
var tags_edit_spinner;
var available_tags;
var autocomplete;

var populate_tags_input = function() {
    var tags = [];
    var anchors = tag_list_span.queryAll('a');
    if (anchors != null) {
      tag_list_span.queryAll('a').each(function(a) {
          tags.push(a.get('innerHTML'));
      });
    }
    tags.sort();
    tag_input.set('value', tags.join(' '));
};

var save_tags = function() {
    var lp_client = new LP.client.Launchpad();
    var tags = Y.Lang.trim(tag_input.get('value')).split(new RegExp('\\s+'));
    var bug = new LP.client.Entry(
        lp_client, LP.client.cache['bug'], LP.client.cache['bug'].self_link);
    bug.removeAtt('http_etag');
    bug.set('tags', tags);
    tags_edit_spinner.setStyle('visibility', 'visible');
    bug.lp_save({on : {
        success: function(updated_entry) {
            var official_tags = [];
            var unofficial_tags = [];
            Y.each(updated_entry.get('tags'), function(tag) {
                if (available_tags.indexOf(tag) > -1) {
                    official_tags.push(tag);
                } else {
                    unofficial_tags.push(tag);
                };                
            });
            official_tags.sort();
            unofficial_tags.sort();
            var tags_html = Y.Array(official_tags).map(function(tag) {
                return Y.Lang.substitute(
                    '<a href="{tag_url}" class="official-tag">{tag}</a>',
                    {tag_url: '#', tag: tag});
            }).join(' ') + ' ' + Y.Array(unofficial_tags).map(function(tag) {
                return Y.Lang.substitute(
                    '<a href="{tag_url}" class="unofficial-tag">{tag}</a>',
                    {tag_url: '#', tag: tag});
            }).join(' ');
            tag_list_span.set('innerHTML', tags_html);
            tag_input.setStyle('display', 'none');
            tag_list_span.setStyle('display', 'inline');
            ok_button.setStyle('display', 'none');
            cancel_button.setStyle('display', 'none');
            edit_tags_trigger.setStyle('display', 'inline');
            tags_edit_spinner.setStyle('display', 'none');
            tags_edit_spinner.setStyle('visibility', 'hidden');
            Y.lazr.anim.green_flash({ node: tag_list_span }).run();
        },
        failure: function(id, request) {
            log(request);
            tags_edit_spinner.setStyle('display', 'none');
            tags_edit_spinner.setStyle('visibility', 'hidden');
            Y.lazr.anim.green_flash({ node: tag_list_span }).run();
        }
    }});
};

var cancel = function() {
    tag_input.setStyle('display', 'none');
    tag_list_span.setStyle('display', 'inline');
    ok_button.setStyle('display', 'none');
    cancel_button.setStyle('display', 'none');
    edit_tags_trigger.setStyle('display', 'inline');
    Y.lazr.anim.red_flash({ node: tag_list_span }).run();
}

bugs.setup_tag_entry = function() {
    if (LP.client.links['me'] === undefined) { return; }

    available_tags = Y.Array(available_official_tags);
    bug_tags_div = Y.get('#bug-tags');
    edit_tags_trigger = bug_tags_div.query('#edit-tags-trigger');
    tag_list_span = bug_tags_div.query('#tag-list');
    tag_input = bug_tags_div.query('#tag-input');
    ok_button = bug_tags_div.query('#edit-tags-ok');
    cancel_button = bug_tags_div.query('#edit-tags-cancel');
    tags_edit_spinner = bug_tags_div.query('#tags-edit-spinner');

    edit_tags_trigger.on('click', function(e) {
        e.halt();
        populate_tags_input();
        tag_list_span.setStyle('display', 'none');
        tag_input.setStyle('display', 'inline');
        autocomplete.render();
        autocomplete.show();
        edit_tags_trigger.setStyle('display', 'none');
        tags_edit_spinner.setStyle('display', 'inline');
        ok_button.setStyle('display', 'inline');
        cancel_button.setStyle('display', 'inline');
    });
    
    cancel_button.on('click', function(e) {
        e.halt();
        cancel();
    });
    
    ok_button.on('click', function(e) {
        e.halt();
        save_tags();
    });

    autocomplete = new Y.lazr.AutoComplete({
        input: '#tag-input',
        data: available_official_tags
    });
    
    tag_input.on('blur', function(e) {
        autocomplete.hide();
    });

    tag_input.on('keypress', function(e) {
        if (e.keyCode == 13) { // Enter
            save_tags();
        } else if (e.keyCode == 27) { //Escape
            cancel();
        } else {
            return;
        };
    });

};
}, '0.1', {requires: ['base', 'io-base', 'node', 'substitute',
                      'widget-position-ext', 'lazr.base', 'lazr.anim',
                      'lazr.overlay', 'lazr.autocomplete']});

