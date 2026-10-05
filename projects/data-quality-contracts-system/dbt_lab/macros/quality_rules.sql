{% test quality_unique_key(model, columns, null_policy='fail') %}
with keyed as (
    select *, count(*) over (partition by {{ columns | join(', ') }}) as key_count
    from {{ model }}
)
select * from keyed
where
{% if null_policy == 'fail' %}
    ({% for column in columns %}{{ column }} is null{% if not loop.last %} or {% endif %}{% endfor %}) or
{% endif %}
    (({% for column in columns %}{{ column }} is not null{% if not loop.last %} and {% endif %}{% endfor %}) and key_count > 1)
{% endtest %}

{% test quality_completeness(model, column_name, minimum_rate) %}
with counts as (
    select count(*) as total, count({{ column_name }}) as filled from {{ model }}
)
select * from counts where total = 0 or filled < total * cast('{{ minimum_rate }}' as decimal(38,18))
{% endtest %}

{% test quality_accepted_values(model, column_name, values) %}
select * from {{ model }}
where {{ column_name }} is null or {{ column_name }} not in (
{% for value in values %}'{{ value | replace("'", "''") }}'{% if not loop.last %},{% endif %}{% endfor %}
)
{% endtest %}

{% test quality_relationship(model, column_name, to, field) %}
select c.* from {{ model }} c
where c.{{ column_name }} is null
   or not exists (select 1 from {{ to }} p where p.{{ field }} = c.{{ column_name }})
   or exists (select 1 from {{ to }} p where p.{{ field }} is not null group by p.{{ field }} having count(*) > 1)
{% endtest %}
