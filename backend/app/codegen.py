"""
Turns a mission's codeTemplate + the slots filled so far into an actual
rendered file. This is what makes the "editor" real instead of decorative —
what the user sees is what actually gets written, not a styled mockup.

Unfilled slots render as a clearly-marked placeholder rather than crashing,
so the preview updates live as the user fills each field in the UI.
"""
import json
from jinja2 import Environment, BaseLoader, Undefined


class _PlaceholderUndefined(Undefined):
    """Renders unfilled Jinja variables as an obvious TODO instead of erroring."""

    def __str__(self):
        return f"<TODO: {self._undefined_name}>"


def _safe_tojson(value):
    """
    Custom tojson filter: falls back to a quoted placeholder string for
    unfilled slots instead of crashing (the built-in filter calls
    json.dumps() directly on the value, which errors on our Undefined type).
    """
    if isinstance(value, Undefined):
        return json.dumps(str(value))
    return json.dumps(value)


_env = Environment(loader=BaseLoader(), undefined=_PlaceholderUndefined)
_env.filters["tojson"] = _safe_tojson


def render_mission_code(mission: dict, filled_values: dict) -> str:
    template = _env.from_string(mission["codeTemplate"])
    # Only pass values that are actually set (skip None/"" so placeholders show)
    context = {k: v for k, v in filled_values.items() if v not in (None, "")}
    return template.render(**context)


def render_finalize_string(template_str: str, context: dict) -> str:
    """Used for agent name/role/goal templates in a campaign's `finalize` block."""
    template = _env.from_string(template_str)
    return template.render(**context)
