/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Official bug tags management user interface.
 *
 * @module OfficialBugTagManagement
 * @requires yahoo, node, LP
 */

YUI.add('bugs.official_bug_tag_management', function(Y) {

var bugs = Y.namespace('bugs');

var official_tags;
var other_tags;

bugs.filter_array = function(arr, fn) {
    var new_array = [];
    Y.each(arr, function(item) {
        if (fn(item)) {
            new_array.push(item);
        }
    });
    return new_array;
}

bugs.sort_tags = function(tags) {
    tags.sort(function(x, y) {
        if (x['tag'] == y['tag']) {
            return 0;
        } else if (x['tag'] > y['tag']) {
            return 1;
        } else {
            return -1;
        }
    });
}

bugs.get_official_bug_tags = function() {
    var tags = [];
    Y.each(official_bug_tags, function(item) {
        var count = used_bug_tags[item];
        if (count == null) {
            count = 0;
        }
        tags.push({tag: item, count: count});
    });
    bugs.sort_tags(tags);
    return tags;
}

bugs.get_other_bug_tags = function() {
    var tags = [];
    Y.each(used_bug_tags, function(value, key, obj) {
        if (official_bug_tags.indexOf(key) < 0) {
            tags.push({tag: key, count: value});
        }
    });
    bugs.sort_tags(tags);
    return tags;
}

bugs.make_tag_li = function(item) {
    var li_html = Y.Lang.substitute([
        '<li id="tag-{tag}">',
        '  <input type="checkbox" />',
        '  {tag} {count}',
        '</li>'
        ].join(''),
        item);
    var li_node = Y.Node.create(li_html);
    li_node._tag = item;
    return li_node;
};

bugs.render_tag_lists = function() {
    var official_tags_ul = Y.get('#official-tags-list');
    var other_tags_ul = Y.get('#other-tags-list');

    official_tags_ul.set('innerHTML', '');
    other_tags_ul.set('innerHTML', '');

    Y.each(official_tags, function(item) {
        official_tags_ul.appendChild(bugs.make_tag_li(item));
    });

    Y.each(other_tags, function(item) {
        other_tags_ul.appendChild(bugs.make_tag_li(item));
    });
}

bugs.setup_official_bug_tag_management = function() {
    official_tags = bugs.get_official_bug_tags();
    other_tags = bugs.get_other_bug_tags();

    var layout_table = Y.get('#layout-table');

    layout_table.setStyle('display', 'block');

    var official_tags_ul = Y.get('#official-tags-list');
    var other_tags_ul = Y.get('#other-tags-list');

    var get_selected_tags = function(tags_ul) {
        var selected_tags = [];
        tags_ul.queryAll('li').each(function(li) {
            if (li.query('input').get('checked')) {
                selected_tags.push(li._tag);
            }
        });
        return selected_tags;
    }

    bugs.render_tag_lists();

    Y.get('#add-official-tags').on('click', function(e) {
        var selected_tags = get_selected_tags(other_tags_ul);
        Y.each(selected_tags, function(item) {
            official_tags.push(item);
        });
        other_tags = bugs.filter_array(other_tags, function(item) {
            return (selected_tags.indexOf(item) < 0);
        });
        bugs.render_tag_lists();
    });

    Y.get('#remove-official-tags').on('click', function(e) {
        var selected_tags = get_selected_tags(official_tags_ul);
        Y.each(selected_tags, function(item) {
            other_tags.push(item);
        });
        official_tags = bugs.filter_array(official_tags, function(item) {
            return (selected_tags.indexOf(item) < 0);
        });
        bugs.render_tag_lists();
    });
}
}, '0.1', {requires: ['node', 'substitute', 'base']});

