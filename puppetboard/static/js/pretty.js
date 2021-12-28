function pretty_print(to_show) {

    if (Object.prototype.toString.call(to_show) === "[object String]") {

        // Print plain string as-is to avoid making it surrounded with ""
        to_show = '<span class="string">' + to_show + '</span>';

    } else {

        // Pretty-print the JSON, with syntax highlight
        // Based on https://stackoverflow.com/a/7220510/2693875

        let is_complex = false;

        to_show = JSON.stringify(to_show, null, 4); // spacing level = 4
        to_show = to_show.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        to_show = to_show.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
            let cls = 'number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    is_complex = true
                    cls = 'key';
                } else {
                    cls = 'string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'boolean';
            } else if (/null/.test(match)) {
                cls = 'null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });

        if (is_complex) {
            // Add pre tag for indentation to be visible
            to_show = '<pre class="json">' + to_show + '</pre>'
        }

    }

    return to_show
}
