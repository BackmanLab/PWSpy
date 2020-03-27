{% set mystring = name | escape + ' (:mod:`' + fullname | escape + '`)' %}
{{mystring | underline}}

.. automodule:: {{ fullname }}

   {% block docstring %}
   {% endblock %}

