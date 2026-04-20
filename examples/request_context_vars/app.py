from flask import Flask, render_template_string

app = Flask(__name__)

app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True


@app.request_context_var_processor
def inject_custom_vars():
    return {
        "custom_message": "Hello from custom processor!",
        "processed": True,
    }


@app.route("/")
def index():
    return render_template_string(
        """
<h1>Request Context Variables Example</h1>
<h2>Default Injected Variables:</h2>
<ul>
    <li><strong>request_id:</strong> {{ request_id }}</li>
    <li><strong>remote_addr:</strong> {{ remote_addr }}</li>
    <li><strong>user_agent:</strong> {{ user_agent }}</li>
    <li><strong>request_method:</strong> {{ request_method }}</li>
    <li><strong>request_path:</strong> {{ request_path }}</li>
</ul>
<h2>Custom Processor Variables:</h2>
<ul>
    <li><strong>custom_message:</strong> {{ custom_message }}</li>
    <li><strong>processed:</strong> {{ processed }}</li>
</ul>
<h2>Notes:</h2>
<p>
    These variables are only injected when <code>REQUEST_CONTEXT_VARS_ENABLED</code>
    is set to <code>True</code>. The global Jinja environment is not polluted.
</p>
<p>
    Each request gets its own unique <code>request_id</code>, ensuring proper
    isolation even in concurrent environments.
</p>
"""
    )


@app.route("/disabled")
def disabled():
    app.config["REQUEST_CONTEXT_VARS_ENABLED"] = False
    result = render_template_string(
        """
<h1>Disabled Example</h1>
<p>request_id is undefined: {{ request_id is undefined }}</p>
<p>remote_addr is undefined: {{ remote_addr is undefined }}</p>
<p>user_agent is undefined: {{ user_agent is undefined }}</p>
"""
    )
    app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True
    return result


if __name__ == "__main__":
    app.run(debug=True)
