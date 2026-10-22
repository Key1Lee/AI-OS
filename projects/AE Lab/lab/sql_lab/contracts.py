from __future__ import annotations
from dataclasses import asdict, dataclass, field
import hashlib
import json
import re

VERSION = 'ae-sql-lab-v1'
MODES = ('learning', 'practice', 'interview')
PATTERNS = ('transaction_fact', 'event_fact', 'periodic_snapshot', 'accumulating_snapshot',
            'factless_fact', 'dimension', 'scd1', 'scd2', 'bridge', 'aggregate_fact', 'gold')

@dataclass(frozen=True)
class ForeignKey:
    columns: tuple[str, ...]
    table: str
    target: tuple[str, ...]
    cardinality: str = 'N:1'
    temporal: bool = False

@dataclass(frozen=True)
class Table:
    name: str
    entity: str
    grain: str
    columns: dict[str, str]
    primary_key: tuple[str, ...]
    natural_key: tuple[str, ...]
    pattern: str
    foreign_keys: tuple[ForeignKey, ...] = ()
    event_time: str | None = None
    processing_time: str | None = None
    effective_dates: tuple[str, ...] = ()
    aggregation: str = 'Non-additive identifiers; counts only at declared grain.'
    parents: tuple[str, ...] = ()
    model_sql: str | None = None
    uniqueness: str = 'Declared primary key is unique and non-null.'

    def __post_init__(self):
        if not re.fullmatch('[a-z][a-z0-9_]*', self.name) or self.pattern not in PATTERNS:
            raise ValueError('Invalid table identity or modeling pattern')
        for key in (*self.primary_key, *self.natural_key):
            if key not in self.columns:
                raise ValueError(f'{self.name}: missing key column {key}')

    def public(self):
        value = asdict(self)
        value.pop('model_sql')
        value['key_kind'] = 'natural' if self.primary_key == self.natural_key else 'surrogate/version key; natural key has different semantics'
        value['valid_join_paths'] = [f'{self.name}.{",".join(f.columns)} → {f.table}.{",".join(f.target)} ({f.cardinality})' +
                                   (' using [valid_from, valid_to) as-of predicate' if f.temporal else '') for f in self.foreign_keys]
        value['expected_output_grain'] = self.grain
        return value

@dataclass(frozen=True)
class Domain:
    id: str
    title: str
    tables: tuple[Table, ...]
    slice: str = 'extension'

    def table(self, name):
        return next(t for t in self.tables if t.name == name)

@dataclass(frozen=True)
class Challenge:
    id: str
    domain: str
    title: str
    area: str
    difficulty: int
    context: str
    inputs: tuple[str, ...]
    output: tuple[str, ...]
    output_key: tuple[str, ...]
    output_grain: str
    concepts: tuple[str, ...]
    assumptions: tuple[str, ...]
    followup: str
    oracle: str
    solution: str
    hint: str
    kind: str = 'sql'
    checkpoints: tuple[str, ...] = ()
    manual_criteria: tuple[str, ...] = ()
    output_types: dict[str, str] = field(default_factory=dict)
    joins: dict[str, str] = field(default_factory=dict)
    ordered: bool = False

    def public(self):
        value = asdict(self)
        for secret in ('solution', 'oracle', 'checkpoints'):
            value.pop(secret)
        value.pop('hint')
        value['provenance'] = 'Original AE Lab scenario; skill alignment with cited public curriculum.'
        return value


def fingerprint(value):
    if hasattr(value, '__dataclass_fields__'):
        value = asdict(value)
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
