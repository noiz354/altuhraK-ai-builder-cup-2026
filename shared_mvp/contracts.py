"""Strict models compiled from the documented, small schema notation (no eval)."""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone
from typing import Any, Annotated, Union

from pydantic import BaseModel, ConfigDict, Field, create_model


class Invalid(ValueError):
    pass


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Parser:
    def __init__(self, text, prefix):
        self.text = re.sub(r'\s+', '', text)
        self.pos = 0
        self.prefix = prefix
        self.serial = 0

    def peek(self):
        return self.text[self.pos:self.pos + 1]

    def take(self, value):
        if not self.text.startswith(value, self.pos):
            raise Invalid(f'Invalid contract near position {self.pos}')
        self.pos += len(value)

    def word(self):
        start = self.pos
        while self.peek() and (self.peek().isalnum() or self.peek() == '_'):
            self.pos += 1
        if start == self.pos:
            raise Invalid('Expected contract identifier')
        return self.text[start:self.pos]

    def value(self):
        if self.peek() == '{':
            self.take('{')
            fields = {}
            while self.peek() != '}':
                name = self.word()
                self.take(':')
                fields[name] = (self.value(), ...)
                if self.peek() == ',':
                    self.take(',')
                elif self.peek() != '}':
                    raise Invalid('Expected field separator')
            self.take('}')
            self.serial += 1
            kind = create_model(f'{self.prefix}_{self.serial}', __base__=Strict, **fields)
        elif self.peek() == '[':
            self.take('[')
            inner = self.value()
            self.take(']')
            kind = Annotated[list[inner], Field(max_length=5000)]
        else:
            name = self.word()
            types = {'str': Annotated[str, Field(max_length=20000)], 'int': int,
                     'float': float, 'bool': bool,
                     'object': dict[str, Union[str, int, float, bool]]}
            if name not in types:
                raise Invalid('Unsupported schema type')
            kind = types[name]
        if self.peek() == '|':
            self.take('|null')
            kind = Union[kind, None]
        return kind


def model(text, prefix):
    parser = Parser(text, prefix)
    result = parser.value()
    if parser.pos != len(parser.text):
        raise Invalid('Unconsumed contract text')
    return result


def iso_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise Invalid('Timestamp must be ISO-8601 with timezone') from None


def iso_date(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
        return parsed
    except (ValueError, TypeError):
        raise Invalid('Date must be YYYY-MM-DD') from None


NONNEGATIVE = {'amount_minor', 'price_minor', 'budget_minor', 'stock_units', 'demand_units',
               'capacity_units', 'quantity', 'entitled_units', 'delivered_units', 'mass_kg',
               'capacity_kg', 'price_minor_per_kg', 'transport_minor_per_kg', 'sold_units',
               'units', 'on_hand', 'lead_time_days', 'velocity_1h', 'start_s', 'end_s',
               'duration_s', 'vibration_mm_s', 'width', 'height', 'x', 'y', 'w', 'h'}


def validate_values(value, field=''):
    if isinstance(value, dict):
        for name, item in value.items():
            validate_values(item, name)
    elif isinstance(value, list):
        for item in value:
            validate_values(item, field)
    elif value is not None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value) or (field in NONNEGATIVE and value < 0):
                raise Invalid(f'{field} must be finite and nonnegative')
            if field in {'width', 'height', 'w', 'h'} and value <= 0:
                raise Invalid(f'{field} must be positive')
        if isinstance(value, str):
            if (field.endswith('_id') or field in {'reference', 'currency'}) and not value.strip():
                raise Invalid(f'{field} cannot be blank')
            if field == 'currency' and not re.fullmatch('[A-Z]{3}', value):
                raise Invalid('currency must be three uppercase letters')
            if field in {'date', 'forecast_date', 'due_date'}:
                iso_date(value)
            if field in {'occurred_at', 'issued_at', 'expires_at', 'as_of'}:
                iso_time(value)


def validate_collections(data):
    count = 0
    for collection, rows in data.items():
        if not isinstance(rows, list):
            continue
        count += len(rows)
        if count > 5000:
            raise Invalid('Maximum 5000 records')
        seen = set()
        key = None
        if rows and isinstance(rows[0], dict):
            key = next((k for k in rows[0] if k.endswith('_id')), None)
        for row in rows:
            if key:
                if row[key] in seen:
                    raise Invalid(f'Duplicate {key} in {collection}')
                seen.add(row[key])
    return count


def validated(kind, data):
    clean = kind.model_validate(data).model_dump()
    validate_values(clean)
    return clean
