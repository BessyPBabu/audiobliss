/**
 * Site-wide toast notifications. Two entry points:
 *   1. window.showToast(message, type) — call this from any AJAX success/error handler.
 *   2. Auto-fires on page load for Django messages rendered via partials/toast_messages.html.
 * `type` accepts Django message tags directly (success/error/warning/info/debug)
 * so no translation layer is needed between the backend and the toast color.
 */
(function () {
    var TOAST_COLORS = {
        success: '#2e7d32',
        error: '#c62828',
        warning: '#f39c12',
        info: '#2d70b3',
        debug: '#555555',
    };
    var DEFAULT_DURATION = 4000;
    var KNOWN_TAGS = ['success', 'error', 'warning', 'info', 'debug'];

    function resolveTag(tagString) {
        if (!tagString) return 'info';
        var tags = tagString.split(' ');
        for (var i = 0; i < tags.length; i++) {
            if (KNOWN_TAGS.indexOf(tags[i]) !== -1) return tags[i];
        }
        return 'info';
    }

    window.showToast = function (message, type, options) {
        if (typeof Toastify === 'undefined') {
            console.warn('Toastify not loaded; message was:', message);
            return;
        }
        var tag = TOAST_COLORS[type] ? type : resolveTag(type);
        Toastify({
            text: message,
            duration: (options && options.duration) || DEFAULT_DURATION,
            close: true,
            gravity: 'top',
            position: 'right',
            backgroundColor: TOAST_COLORS[tag] || TOAST_COLORS.info,
            stopOnFocus: true,
        }).showToast();
    };

    document.addEventListener('DOMContentLoaded', function () {
        var container = document.getElementById('django-messages');
        if (!container) return;
        var nodes = container.querySelectorAll('.django-message');
        nodes.forEach(function (node, index) {
            var text = node.getAttribute('data-text');
            var tag = resolveTag(node.getAttribute('data-tag'));
            // Small stagger so multiple messages don't all stack instantly
            setTimeout(function () {
                window.showToast(text, tag);
            }, index * 300);
        });
    });
})();