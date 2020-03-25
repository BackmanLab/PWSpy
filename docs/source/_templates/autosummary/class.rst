{% extends "!autosummary/class.rst" %}

{% block methods %}
{% if methods %}
      .. autosummary::
         :toctree:
      {% for item in methods %}
         {%- if not item.startswith('_') or item in ['__call__'] %}
         {{ name }}.{{ item }}
         {%- endif -%}
      {%- endfor %}
{% endif %}
{% endblock %}

{% block attributes %}
{% if attributes %}
      .. autosummary::
         :toctree:
      {% for item in attributes %}
         {%- if not item.startswith('_') %}
         {{ name }}.{{ item }}
         {%- endif -%}
      {%- endfor %}
{% endif %}
{% endblock %}