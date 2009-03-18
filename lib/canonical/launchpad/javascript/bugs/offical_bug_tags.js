/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Official bug tags management user interface.
 *
 * @module OfficialBugTagManagement
 * @requires yahoo, node, LP
 */

YUI.add('bugs.official_bug_tag_management', function(Y) {

var bugs = Y.namespace('bugs');

bugs.setup_official_bug_tag_management = function() {
    var make_tag_li = function(name, count) {
        var li_html = Y.Lang.substitute('<li>{name} {count}</li>',
                                        {name: name, count: count});
        return Y.Node.create(li_html);
    };


    var layout_table = Y.get('#layout-table');

    layout_table.setStyle('display', 'block');

    var official_tags_ul = Y.get('#official-tags-list');
    var other_tags_ul = Y.get('#other-tags-list');

    Y.each(official_bug_tags, function(item) {
        var count = used_bug_tags[item];
        if (count == null) {
            count = 0;
        }
        official_tags_ul.appendChild(make_tag_li(item, count));
    });

    Y.each(used_bug_tags, function(value, key, obj) {
        other_tags_ul.appendChild(make_tag_li(key, value));
    });

}
}, '0.1', {requires: ['node', 'substitute', 'base']});

