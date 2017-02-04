{%- import '_macros.html' as macros -%}
{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {% for node in fact_data -%}
      {%- if not loop.first %},{%- endif -%}
      [
        {%- for column in columns -%}
          {%- if not loop.first %},{%- endif -%}
          {%- if column in ['fqdn', 'hostname'] -%}
            {% filter jsonprint %}<a href="{{ url_for('node', env=current_env, node_name=node) }}">{{ node }}</a>{% endfilter %}
          {%- elif fact_data[node][column] -%}
            {{ fact_data[node][column] | jsonprint }}
          {%- else -%}
            ""
          {%- endif -%}
        {%- endfor -%}
      ]
    {% endfor -%}
  ]
}
