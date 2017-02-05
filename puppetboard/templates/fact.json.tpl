{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {% for fact_h in facts -%}
      {%- if not loop.first %},{%- endif -%}
      [
        {%- if not fact -%}
          {{ fact_h.name | jsonprint }}
          {%- if node or value %},{% endif -%}
        {%- endif -%}
        {%- if not node -%}
          {% filter jsonprint %}<a href="{{ url_for('node', env=current_env, node_name=fact_h.node) }}">{{ fact_h.node }}</a>{% endfilter %}
          {%- if not value %},{% endif -%}
        {%- endif -%}
        {%- if not value -%}
          {%- if fact_h.value is mapping -%}
            {% filter jsonprint %}<a href="{{ url_for('fact', env=current_env, fact=fact_h.name, value=fact_h.value) }}"><pre>{{ fact_h.value | jsonprint }}</pre></a>{% endfilter %}
          {%- else -%}
            {% filter jsonprint %}<a href="{{ url_for('fact', env=current_env, fact=fact_h.name, value=fact_h.value) }}"><pre>{{ fact_h.value }}</pre></a>{% endfilter %}
          {%- endif -%}
        {%- endif -%}
      ]
    {% endfor -%}
  ]
  {%- if render_graph %},
  "chart": [
    {% for fact_h in facts | map('format_attribute', 'value', '{0}') | groupby('value') -%}
    {%- if not loop.first %},{%- endif -%}
    {
      "label": {{ fact_h.grouper | replace("\n", " ") | jsonprint }},
      "value": {{ fact_h.list|length }}
    }
    {% endfor %}
  ]
  {% endif %}
}
