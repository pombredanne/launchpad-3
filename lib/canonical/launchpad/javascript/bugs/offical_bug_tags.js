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

var valid_name_re = new RegExp(valid_name_pattern);

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
        '  <input type="checkbox" id="tag-checkbox-{tag}" />',
        '  <label for="tag-checkbox-{tag}">{tag} {count}</label>',
        '</li>'
        ].join(''),
        item);
    var li_node = Y.Node.create(li_html);
    li_node._tag = item;
    li_node.query('input').on('click', function(e) {
      Y.log(li_node.get('innerHTML'))
      if (li_node.get('checked')) {
        li_node.get('parentNode').addClass('selected');
      } else {
        li_node.get('parentNode').removeClass('selected');
      }
    });
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

bugs.save_tags = function() {
    var tags = [];
    Y.each(official_tags, function(item) {
        tags.push(item['tag']);
    });
    Y.get('#field-official_bug_tags').set('value', tags.join(' '));
    Y.get('#save-form').submit();
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

    var on_new_tag_add = function() {
        var new_tag = Y.Lang.trim(Y.get('#new-tag-text').get('value'));
        var new_tag_already_official = false;
        Y.each(official_tags, function(item) {
            new_tag_already_official = new_tag_already_official || (item['tag'] == new_tag);
        });
        var new_tag_already_used = false;
        Y.each(other_tags, function(item) {
            new_tag_already_used = new_tag_already_used || (item['tag'] == new_tag);
        });
        if (new_tag_already_used) {
            Y.each(other_tags, function(item) {
                if (item['tag'] == new_tag) {
                    official_tags.push(item);
                }
            });
            other_tags = bugs.filter_array(other_tags, function(item) {
                return item['tag'] != new_tag;
            });
        }
        if (!new_tag_already_official && !new_tag_already_used) {
            if (valid_name_re.test(new_tag)) {
                var count = used_bug_tags[new_tag];
                if (count == null) {
                    count = 0;
                }
                official_tags.push({tag: new_tag, count: 0});
            } else {
                Y.get("#field-error-message").setStyle('display', 'block');
            }
        }
        bugs.render_tag_lists();
    }

    Y.get('#new-tag-add').on('click', function(e) {
        on_new_tag_add();
    });

    Y.get('#new-tag-text').on('keypress', function(e) {
        var new_value = Y.Lang.trim(Y.get('#new-tag-text').get('value'));
        if (valid_name_re.test(new_value)) {
            Y.get("#field-error-message").setStyle('display', 'none');
        }
        if (e.keyCode == 13) { // Enter == 13
            on_new_tag_add();
        }
    });

    Y.get('#save-button').on('click', function(e) {
        e.halt();
        bugs.save_tags();
    });
}
}, '0.1', {requires: ['node', 'substitute', 'base']});

