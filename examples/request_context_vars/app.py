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
<h1>Request Context Variables Example (Enabled)</h1>
<p>This route has <code>REQUEST_CONTEXT_VARS_ENABLED = True</code></p>

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

<p><a href="/compare">Compare with variables accessed directly from request object</a></p>
"""
    )


@app.route("/compare")
def compare():
    return render_template_string(
        """
<h1>Compare: Accessing Variables Directly</h1>
<p>This shows how to access request info without the request context vars mechanism:</p>

<h2>From request object:</h2>
<ul>
    <li><strong>request.method:</strong> {{ request.method }}</li>
    <li><strong>request.path:</strong> {{ request.path }}</li>
    <li><strong>request.remote_addr:</strong> {{ request.remote_addr }}</li>
    <li><strong>request.user_agent:</strong> {{ request.user_agent }}</li>
</ul>

<h2>request_context_var_processor Variables (not injected here):</h2>
<ul>
    <li><strong>request_id:</strong> {{ request_id }} (only available when REQUEST_CONTEXT_VARS_ENABLED is True)</li>
    <li><strong>custom_message:</strong> {{ custom_message is undefined }} (undefined)</li>
</ul>

<p><a href="/">Back to enabled example</a></p>
"""
    )


def create_disabled_app():
    disabled_app = Flask("disabled_app")
    disabled_app.config["REQUEST_CONTEXT_VARS_ENABLED"] = False

    @disabled_app.route("/")
    def disabled_index():
        return render_template_string(
            """
<h1>Request Context Variables Example (Disabled)</h1>
<p>This app has <code>REQUEST_CONTEXT_VARS_ENABLED = False</code></p>

<h2>Check if variables are injected:</h2>
<ul>
    <li><strong>request_id is undefined:</strong> {{ request_id is undefined }}</li>
    <li><strong>remote_addr is undefined:</strong> {{ remote_addr is undefined }}</li>
    <li><strong>user_agent is undefined:</strong> {{ user_agent is undefined }}</li>
    <li><strong>request_method is undefined:</strong> {{ request_method is undefined }}</li>
    <li><strong>request_path is undefined:</strong> {{ request_path is undefined }}</li>
</ul>

<h2>But you can still use request object:</h2>
<ul>
    <li><strong>request.method:</strong> {{ request.method }}</li>
    <li><strong>request.path:</strong> {{ request.path }}</li>
</ul>

<p>Note: request object is always available in templates through the default context processor.</p>
"""
        )

    return disabled_app


if __name__ == "__main__":
    print("=" * 60)
    print("Request Context Variables Example")
    print("=" * 60)
    print()
    print("To run the ENABLED example (default):")
    print("  flask --app examples/request_context_vars/app:app run")
    print()
    print("To run the DISABLED example:")
    print("  flask --app examples/request_context_vars/app:create_disabled_app run --port 5001")
    print()
    print("Or run the enabled app directly:")
    app.run(debug=True, port=5000)
