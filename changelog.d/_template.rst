{% for section, _ in sections.items() %}
{% set underline = "-" %}
{% if sections[section] %}
{{ versiondata.version }}
{{ underline * versiondata.version|length }}

{% for category, val in sections[section].items() %}
{{ category }}
{{ "~" * category|length }}

{% for text, values in val|dictsort %}
-   {{ text }}
{% endfor %}

{% endfor %}
{% else %}
No significant changes.

{% endif %}
{% endfor %}
