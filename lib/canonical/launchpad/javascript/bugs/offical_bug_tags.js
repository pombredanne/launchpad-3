/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Official bug tags management user interface.
 *
 * @module OfficialBugTagManagement
 * @requires yahoo, node, LP
 */

YUI.add('bugs.official_bug_tag_management', function(Y) {

var bugs = Y.namespace('bugs');

bugs.get_official_bug_tags = function() {
    var tags = [];
    Y.each(official_bug_tags, function(item) {
        var count = used_bug_tags[item];
        if (count == null) {
            count = 0;
        }
        tags.push({tag: item, count: count});
    });
    return tags;
}

bugs.get_other_bug_tags = function() {
    var tags = [];
    Y.each(used_bug_tags, function(value, key, obj) {
        if (official_bug_tags.indexOf(key) < 0) {
            tags.push({tag: key, count: value});
        }
    });
    return tags;
}

bugs.setup_official_bug_tag_management = function() {
    var official_tags = bugs.get_official_bug_tags();
    var other_tags = bugs.get_other_bug_tags();

    var make_tag_li = function(item) {
        var li_html = Y.Lang.substitute('<li>{tag} {count}</li>', item);
        return Y.Node.create(li_html);
    };

    var layout_table = Y.get('#layout-table');

    layout_table.setStyle('display', 'block');

    var official_tags_ul = Y.get('#official-tags-list');
    var other_tags_ul = Y.get('#other-tags-list');

    Y.each(official_tags, function(item) {
        official_tags_ul.appendChild(make_tag_li(item));
    });

    Y.each(other_tags, function(item) {
        other_tags_ul.appendChild(make_tag_li(item));
    });

}
}, '0.1', {requires: ['node', 'substitute', 'base']});

