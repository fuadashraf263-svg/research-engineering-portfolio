"""Dimensional and semantic quantity rules for the Axiomata v0.1 kernel."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Final

from .diagnostics import (
    SEMANTIC_DIVISION_BY_ZERO,
    SEMANTIC_INVALID_OPERATION,
    SEMANTIC_TYPE_MISMATCH,
    SEMANTIC_UNKNOWN_TYPE,
    SEMANTIC_UNKNOWN_UNIT,
)
from .errors import AxiomataError, Span

Dimension = tuple[int, int, int, int, int, int, int]

ZERO: Final[Dimension] = (0, 0, 0, 0, 0, 0, 0)
LENGTH: Final[Dimension] = (0, 1, 0, 0, 0, 0, 0)
AREA: Final[Dimension] = (0, 2, 0, 0, 0, 0, 0)
VOLUME: Final[Dimension] = (0, 3, 0, 0, 0, 0, 0)
MASS: Final[Dimension] = (1, 0, 0, 0, 0, 0, 0)
TIME: Final[Dimension] = (0, 0, 1, 0, 0, 0, 0)
FORCE: Final[Dimension] = (1, 1, -2, 0, 0, 0, 0)
PRESSURE: Final[Dimension] = (1, -1, -2, 0, 0, 0, 0)
ENERGY: Final[Dimension] = (1, 2, -2, 0, 0, 0, 0)
POWER: Final[Dimension] = (1, 2, -3, 0, 0, 0, 0)
SPEED: Final[Dimension] = (0, 1, -1, 0, 0, 0, 0)
TEMPERATURE: Final[Dimension] = (0, 0, 0, 0, 1, 0, 0)


@dataclass(frozen=True)
class TypeSpec:
    name: str
    dimension: Dimension
    kind: str
    si_unit: str


TYPES: Final[dict[str, TypeSpec]] = {
    "Dimensionless": TypeSpec("Dimensionless", ZERO, "dimensionless", "1"),
    "Length": TypeSpec("Length", LENGTH, "length", "m"),
    "Area": TypeSpec("Area", AREA, "area", "m2"),
    "Volume": TypeSpec("Volume", VOLUME, "volume", "m3"),
    "Mass": TypeSpec("Mass", MASS, "mass", "kg"),
    "Time": TypeSpec("Time", TIME, "time", "s"),
    "Speed": TypeSpec("Speed", SPEED, "speed", "m_per_s"),
    "Force": TypeSpec("Force", FORCE, "force", "N"),
    "Pressure": TypeSpec("Pressure", PRESSURE, "pressure", "Pa"),
    "Energy": TypeSpec("Energy", ENERGY, "energy", "J"),
    "Torque": TypeSpec("Torque", ENERGY, "torque", "Nm"),
    "Power": TypeSpec("Power", POWER, "power", "W"),
    "AbsoluteTemperature": TypeSpec(
        "AbsoluteTemperature", TEMPERATURE, "absolute_temperature", "K"
    ),
    "TemperatureDifference": TypeSpec(
        "TemperatureDifference", TEMPERATURE, "temperature_difference", "K"
    ),
}

TYPE_BY_KIND: Final[dict[str, TypeSpec]] = {
    type_spec.kind: type_spec for type_spec in TYPES.values()
}


@dataclass(frozen=True)
class Unit:
    symbol: str
    factor_to_si: Fraction
    type_spec: TypeSpec


def _decimal(text: str) -> Fraction:
    return Fraction(Decimal(text))


UNITS: Final[dict[str, Unit]] = {
    "m": Unit("m", _decimal("1"), TYPES["Length"]),
    "mm": Unit("mm", _decimal("0.001"), TYPES["Length"]),
    "cm": Unit("cm", _decimal("0.01"), TYPES["Length"]),
    "km": Unit("km", _decimal("1000"), TYPES["Length"]),
    "in": Unit("in", _decimal("0.0254"), TYPES["Length"]),
    "ft": Unit("ft", _decimal("0.3048"), TYPES["Length"]),
    "m2": Unit("m2", _decimal("1"), TYPES["Area"]),
    "mm2": Unit("mm2", _decimal("0.000001"), TYPES["Area"]),
    "m3": Unit("m3", _decimal("1"), TYPES["Volume"]),
    "mm3": Unit("mm3", _decimal("0.000000001"), TYPES["Volume"]),
    "kg": Unit("kg", _decimal("1"), TYPES["Mass"]),
    "g": Unit("g", _decimal("0.001"), TYPES["Mass"]),
    "s": Unit("s", _decimal("1"), TYPES["Time"]),
    "min": Unit("min", _decimal("60"), TYPES["Time"]),
    "h": Unit("h", _decimal("3600"), TYPES["Time"]),
    "N": Unit("N", _decimal("1"), TYPES["Force"]),
    "kN": Unit("kN", _decimal("1000"), TYPES["Force"]),
    "Pa": Unit("Pa", _decimal("1"), TYPES["Pressure"]),
    "kPa": Unit("kPa", _decimal("1000"), TYPES["Pressure"]),
    "MPa": Unit("MPa", _decimal("1000000"), TYPES["Pressure"]),
    "J": Unit("J", _decimal("1"), TYPES["Energy"]),
    "Nm": Unit("Nm", _decimal("1"), TYPES["Torque"]),
    "W": Unit("W", _decimal("1"), TYPES["Power"]),
    "mps": Unit("mps", _decimal("1"), TYPES["Speed"]),
    "K": Unit("K", _decimal("1"), TYPES["AbsoluteTemperature"]),
    "dK": Unit("dK", _decimal("1"), TYPES["TemperatureDifference"]),
}


@dataclass(frozen=True)
class Quantity:
    """A quantity normalized to SI base units, retaining its semantic kind."""

    value: Fraction
    dimension: Dimension
    kind: str
    si_unit: str
    source_unit: str | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "magnitude": magnitude_json(self.value),
            "dimension": list(self.dimension),
            "quantity_kind": f"isq:{self.kind}",
            "unit": f"si:{self.si_unit}",
        }


def decimal_text(value: Fraction) -> str:
    """Stable exact decimal form, valid only for terminating fractions."""
    if value == 0:
        return "0"
    denominator = value.denominator
    power_two = 0
    power_five = 0
    while denominator % 2 == 0:
        denominator //= 2
        power_two += 1
    while denominator % 5 == 0:
        denominator //= 5
        power_five += 1
    if denominator != 1:
        raise ValueError("exact rational does not have a terminating decimal representation")
    scale = max(power_two, power_five)
    numerator = value.numerator * (2 ** (scale - power_two)) * (5 ** (scale - power_five))
    sign = "-" if numerator < 0 else ""
    digits = str(abs(numerator))
    if scale == 0:
        return sign + digits
    digits = digits.rjust(scale + 1, "0")
    text = sign + digits[:-scale] + "." + digits[-scale:]
    return text.rstrip("0").rstrip(".")


def magnitude_json(value: Fraction) -> dict[str, object]:
    """Lossless canonical magnitude, decimal when possible and rational otherwise."""
    try:
        return {"decimal": decimal_text(value)}
    except ValueError:
        return {
            "rational": {
                "numerator": str(value.numerator),
                "denominator": str(value.denominator),
            }
        }


def literal(number: str, unit_name: str | None, span: Span) -> Quantity:
    try:
        value = Fraction(Decimal(number))
    except InvalidOperation as exc:
        raise AxiomataError(
            SEMANTIC_INVALID_OPERATION, f"invalid decimal literal '{number}'", span
        ) from exc
    if unit_name is None:
        return Quantity(value, ZERO, "dimensionless", "1")
    unit = UNITS.get(unit_name)
    if unit is None:
        raise AxiomataError(
            SEMANTIC_UNKNOWN_UNIT, f"unknown unit '{unit_name}'", span
        )
    return Quantity(
        value * unit.factor_to_si,
        unit.type_spec.dimension,
        unit.type_spec.kind,
        unit.type_spec.si_unit,
        unit_name,
    )


def assert_declared_type(quantity: Quantity, type_name: str, span: Span) -> Quantity:
    expected = TYPES.get(type_name)
    if expected is None:
        raise AxiomataError(
            SEMANTIC_UNKNOWN_TYPE, f"unknown quantity type '{type_name}'", span
        )
    if quantity.dimension != expected.dimension or quantity.kind != expected.kind:
        raise AxiomataError(
            SEMANTIC_TYPE_MISMATCH,
            f"expected {type_name}, got {describe(quantity)}",
            span,
        )
    return quantity


def describe(quantity: Quantity) -> str:
    return f"{quantity.kind} with dimension {list(quantity.dimension)}"


def _same(left: Quantity, right: Quantity, span: Span, operation: str) -> None:
    if left.dimension != right.dimension or left.kind != right.kind:
        raise AxiomataError(
            SEMANTIC_TYPE_MISMATCH,
            f"cannot {operation} {left.kind} and {right.kind}; "
            "matching dimensions alone are not enough",
            span,
        )


def add(left: Quantity, right: Quantity, span: Span) -> Quantity:
    _same(left, right, span, "add")
    return Quantity(left.value + right.value, left.dimension, left.kind, left.si_unit)


def subtract(left: Quantity, right: Quantity, span: Span) -> Quantity:
    _same(left, right, span, "subtract")
    return Quantity(left.value - right.value, left.dimension, left.kind, left.si_unit)


def negate(value: Quantity) -> Quantity:
    return Quantity(-value.value, value.dimension, value.kind, value.si_unit)


def multiply_result_type(
    left_kind: str, right_kind: str, span: Span | None = None
) -> TypeSpec:
    if left_kind == "dimensionless":
        return TYPE_BY_KIND[right_kind]
    if right_kind == "dimensionless":
        return TYPE_BY_KIND[left_kind]
    kinds = frozenset((left_kind, right_kind))
    if kinds == {"length"}:
        return TYPES["Area"]
    if kinds == {"area", "length"}:
        return TYPES["Volume"]
    raise AxiomataError(
        SEMANTIC_INVALID_OPERATION,
        f"multiplication of {left_kind} and {right_kind} is ambiguous in v0.1; "
        "use an explicit domain model",
        span,
    )


def multiply(left: Quantity, right: Quantity, span: Span) -> Quantity:
    result = multiply_result_type(left.kind, right.kind, span)
    return Quantity(
        left.value * right.value,
        result.dimension,
        result.kind,
        result.si_unit,
    )


def divide_result_type(
    left_kind: str, right_kind: str, span: Span | None = None
) -> TypeSpec:
    if right_kind == "dimensionless":
        return TYPE_BY_KIND[left_kind]
    if left_kind == right_kind:
        return TYPES["Dimensionless"]
    if left_kind == "length" and right_kind == "time":
        return TYPES["Speed"]
    if left_kind == "force" and right_kind == "area":
        return TYPES["Pressure"]
    raise AxiomataError(
        SEMANTIC_INVALID_OPERATION,
        f"division of {left_kind} by {right_kind} is not defined in v0.1", span
    )


def divide(left: Quantity, right: Quantity, span: Span) -> Quantity:
    if right.value == 0:
        raise AxiomataError(SEMANTIC_DIVISION_BY_ZERO, "division by zero", span)
    if left.kind == right.kind and left.dimension != right.dimension:
        raise AxiomataError(
            SEMANTIC_INVALID_OPERATION,
            f"division of {left.kind} by {right.kind} is not defined in v0.1",
            span,
        )
    result = divide_result_type(left.kind, right.kind, span)
    return Quantity(
        left.value / right.value,
        result.dimension,
        result.kind,
        result.si_unit,
    )


def compare(left: Quantity, right: Quantity, operator: str, span: Span) -> bool:
    _same(left, right, span, "compare")
    return {
        ">": left.value > right.value,
        ">=": left.value >= right.value,
        "<": left.value < right.value,
        "<=": left.value <= right.value,
        "==": left.value == right.value,
        "!=": left.value != right.value,
    }[operator]
