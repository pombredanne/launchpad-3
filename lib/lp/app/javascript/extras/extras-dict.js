/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Things that YUI3 really needs.
 *
 * @module lp
 * @submodule extras-dict
 */

YUI.add('lp.extras-dict', function(Y) {

Y.log('loading lp.extras-dict');

var namespace = Y.namespace("lp.extras"),
    isArray = Y.Lang.isArray;

/**
 * An object type that resembles Python's dict.
 *
 * This is *experimental*. It may be useful to have a dict-like type
 * in JavaScript, hence this, but it may turn out to be a distraction,
 * hence why it's in a separate module.
 */
var Dict = function(initial) {
    if (initial !== undefined) {
        this.update(initial);
    }
};

// Static members.
Y.mix(Dict, {

    fromKeys: function(keys, def) {
        var dict = new Dict();
        Y.Array.each(keys, function(key) { dict[key] = def; });
        return dict;
    }

}, true);

// Prototype members.
Y.mix(Dict.prototype, {

    clear: function() {
        var del = function(key) { delete this[key]; };
        this.keys().forEach(del, this);
    },

    copy: function() {
        return new Dict(this);
    },

    get: function(key, def) {
        return this.hasOwnProperty(key) ? this[key] : def;
    },

    hasKey: function(key) {
        return this.hasOwnProperty(key);
    },

    items: function() {
        return this.keys().map(function(key) {
            return {key: key, value: this[key]};
        }, this);
    },

    keys: function() {
        return Y.Object.keys(this);
    },

    pop: function(key, def) {
        var value;
        if (this.hasOwnProperty(key)) {
            value = this[key];
            delete this[key];
            return value;
        }
        else {
            return def;
        }
    },

    popItem: function() {
        var key, value;
        for (key in this) {
            if (this.hasOwnProperty(key)) {
                value = this[key];
                delete this[key];
                return {key: key, value: value};
            }
        }
        return undefined;
    },

    setDefault: function(key, def) {
        if (this.hasOwnProperty(key)) {
            return this[key];
        }
        else {
            this[key] = def;
            return def;
        }
    },

    /**
     * Update the Dict in place.
     *
     * If source is an object, its *own* properties are copied. If
     * source is array-like, each entry should either be a {key,
     * value} object or a [key, value] array.
     *
     * @param {Object|Dict|Array} source
     */
    update: function(source) {
        var key;
        if (isArray(source)) {
            Y.each(source, function(item) {
                if (isArray(item)) {
                    this[item[0]] = item[1];
                }
                else {
                    this[item.key] = item.value;
                }
            }, this);
        }
        else {
            for (key in source) {
                if (source.hasOwnProperty(key)) {
                    this[key] = source[key];
                }
            }
        }
    },

    values: function() {
        return Y.Object.values(this);
    },

    isEmpty: function() {
        return Y.Object.isEmpty(this);
    },

    isSame: function(other) {
        var key, keys = Y.Object.keys(this),
            other_key, other_keys = Y.Object.keys(other);
        if (keys.length !== other_keys.length) {
            return false;
        }
        keys.sort(); other_keys.sort();
        while (keys.length > 0) {
            key = keys.pop(); other_key = other_keys.pop();
            if (key !== other_key || this[key] !== other[key]) {
                return false;
            }
        }
        return true;
    }

}, true);

// Exports.
namespace.Dict = Dict;

}, "0.1", {requires: ["yui-base"]});
