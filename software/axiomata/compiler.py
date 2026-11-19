"""AXM v0.1 compiler: source -> validated canonical AXG model."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .canonical import canonical_json, hashed_record, sha256_digest
from .diagnostics import (
    SEMANTIC_DUPLICATE_NAME,
    SEMANTIC_DIVISION_BY_ZERO,
    SEMANTIC_EXPORT,
    SEMANTIC_FRAME,
    SEMANTIC_GEOMETRY,
    SEMANTIC_INVALID_OPERATION,
    SEMANTIC_REQUIREMENT_FAILED,
    SEMANTIC_TYPE_MISMATCH,
    SEMANTIC_UNIT_SYSTEM,
    SEMANTIC_UNKNOWN_NAME,
    SEMANTIC_UNKNOWN_TYPE,
    AXVM_ARITHMETIC,
    AXVM_RESOURCE_LIMIT,
)
from .axir_functions import (
    AXIR_FUNCTION_IDENTITY,
    AxirFunctionBinary,
    AxirFunctionCall,
    AxirFunctionConstant,
    AxirFunctionDefinition,
    AxirFunctionModule,
    AxirFunctionParameter,
    AxirFunctionReturn,
    lower_axir_function_module,
    validate_axir_function_module,
)
from .axm_functions import (
    AxmFunctionCatalog,
    AxmFunctionParameterType,
    AxmFunctionSignature,
    lower_axm_function_definition,
)
from .exact_functions import (
    ExactFunctionExecutionError,
    ExactFunctionModule,
    execute_exact_function,
)
from .errors import AxiomataError, Span
from .syntax import (
    BinaryExpr,
    CallExpr,
    ConditionalExpr,
    EntityStmt,
    ExportStmt,
    Expr,
    FrameStmt,
    FunctionStmt,
    GeometryStmt,
    LetStmt,
    LiteralExpr,
    MeasureStmt,
    Model,
    NameExpr,
    RequireStmt,
    UnaryExpr,
    UnitSystemStmt,
    parse,
)
from .units import (
    LENGTH,
    TYPES,
    VOLUME,
    Quantity,
    add,
    assert_declared_type,
    compare,
    divide,
    literal,
    multiply,
    negate,
    subtract,
)

GEOMETRY_PROFILES = frozenset({"step.basic", "stl.basic", "dxf.basic"})
SCALAR_PROFILES = frozenset({"csv.scalar", "mat.scalar", "m.scalar", "pdf.scalar"})


@dataclass(frozen=True)
class GeometryValue:
    name: str
    kind: str
    frame: str
    dimensions: tuple[Quantity, Quantity, Quantity]
    volume: Quantity


@dataclass(frozen=True)
class FrameValue:
    name: str
    identity: str
    parent: str
    rotation: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]
    translation: tuple[Quantity, Quantity, Quantity]


IDENTITY_ROTATION = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
FRAME_ROTATIONS = {
    "aligned": IDENTITY_ROTATION,
    "rotated_z90": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "rotated_z180": ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "rotated_z270": ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
}


@dataclass(frozen=True)
class Compilation:
    model: Model
    axg: dict[str, Any]
    functions: AxmFunctionCatalog
    function_ir: AxirFunctionModule
    quantities: dict[str, Quantity]

    @property
    def semantic_digest(self) -> str:
        return self.axg["semantic_digest"]

    @property
    def revision_digest(self) -> str:
        return self.axg["revision_digest"]

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.axg)


def _identity(model_name: str, category: str, name: str) -> str:
    return f"axm://local/{model_name}/{category}/{name}"


def _node(record: dict[str, Any]) -> dict[str, Any]:
    """Create a complete v0 node envelope before content-addressing it."""
    complete = dict(record)
    complete["claims"] = []
    complete["provenance"] = []
    complete["lifecycle"] = "DRAFT"
    return hashed_record(complete)


def _quantity_node(model_name: str, name: str, value: Quantity) -> dict[str, Any]:
    return _node(
        {
            "identity": _identity(model_name, "quantity", name),
            "type": "axm.core:Quantity",
            "schema_version": "0.1.0",
            "properties": {"name": name, "value": value.to_json()},
        }
    )


def _function_node(
    model_name: str,
    signature: AxmFunctionSignature,
    definition: AxirFunctionDefinition,
    names_by_id: dict[int, str],
) -> dict[str, Any]:
    body: list[dict[str, Any]] = []
    for operation in definition.operations:
        if isinstance(operation, AxirFunctionParameter):
            body.append(
                {
                    "destination": operation.destination,
                    "index": operation.index,
                    "op": "parameter",
                    "quantity_kind": f"isq:{operation.static_kind}",
                }
            )
        elif isinstance(operation, AxirFunctionConstant):
            body.append(
                {
                    "destination": operation.destination,
                    "op": "constant",
                    "quantity_kind": f"isq:{operation.static_kind}",
                    "value": operation.value.to_json(),
                }
            )
        elif isinstance(operation, AxirFunctionBinary):
            body.append(
                {
                    "destination": operation.destination,
                    "left": operation.left,
                    "op": operation.opcode.value,
                    "quantity_kind": f"isq:{operation.static_kind}",
                    "right": operation.right,
                }
            )
        elif isinstance(operation, AxirFunctionCall):
            body.append(
                {
                    "arguments": list(operation.arguments),
                    "callee": _identity(
                        model_name, "function", names_by_id[operation.callee]
                    ),
                    "destination": operation.destination,
                    "op": "call",
                    "quantity_kind": f"isq:{operation.static_kind}",
                }
            )
        elif isinstance(operation, AxirFunctionReturn):
            body.append({"op": "return", "value": operation.value})
        else:
            raise TypeError(
                f"unknown AxIR function operation {type(operation).__name__}"
            )
    return _node(
        {
            "identity": _identity(model_name, "function", signature.name),
            "type": "axm.core:ExactFunction",
            "schema_version": "0.1.0",
            "properties": {
                "body": body,
                "name": signature.name,
                "parameters": [
                    {
                        "name": parameter.name,
                        "quantity_kind": f"isq:{parameter.kind}",
                    }
                    for parameter in signature.parameters
                ],
                "result_kind": f"isq:{signature.result}",
                "semantics": AXIR_FUNCTION_IDENTITY,
            },
        }
    )


def _geometry_node(model_name: str, value: GeometryValue) -> dict[str, Any]:
    length, width, height = value.dimensions
    return _node(
        {
            "identity": _identity(model_name, "geometry", value.name),
            "type": "axm.geometry:Box",
            "schema_version": "0.1.0",
            "properties": {
                "name": value.name,
                "frame": value.frame,
                "length": length.to_json(),
                "width": width.to_json(),
                "height": height.to_json(),
                "analytic_volume": value.volume.to_json(),
            },
        }
    )


def _entity_type_uri(type_name: str) -> str:
    parts = type_name.split(".")
    if len(parts) < 2:
        return f"axm.user:{type_name}@0.1.0"
    return f"axm.{'.'.join(parts[:-1])}:{parts[-1]}@0.1.0"


def _entity_node(model_name: str, stmt: EntityStmt) -> dict[str, Any]:
    return _node(
        {
            "identity": _identity(model_name, "entity", stmt.name),
            "type": _entity_type_uri(stmt.type_name),
            "schema_version": "0.1.0",
            "properties": {"name": stmt.name},
        }
    )


def _frame_node(value: FrameValue) -> dict[str, Any]:
    is_identity = value.rotation == IDENTITY_ROTATION and all(
        coordinate.value == 0 for coordinate in value.translation
    )
    transform: object
    if is_identity:
        transform = "axm.geometry:IdentityRigidTransform@0.1.0"
    else:
        transform = {
            "kind": "axm.geometry:AxisAlignedRigidTransform@0.1.0",
            "rotation": [list(row) for row in value.rotation],
            "translation": {
                "x": value.translation[0].to_json(),
                "y": value.translation[1].to_json(),
                "z": value.translation[2].to_json(),
            },
        }
    return _node(
        {
            "identity": value.identity,
            "type": "axm.geometry:Frame",
            "schema_version": "0.1.0",
            "properties": {
                "name": value.name,
                "parent": value.parent,
                "transform": transform,
            },
        }
    )


def _requirement_node(
    model_name: str, ordinal: int, stmt: RequireStmt, passed: bool
) -> dict[str, Any]:
    return _node(
        {
            "identity": _identity(model_name, "requirement", f"r{ordinal}"),
            "type": "axm.requirements:Invariant",
            "schema_version": "0.1.0",
            "properties": {
                "operator": stmt.operator,
                "passed": passed,
            },
        }
    )


def _export_node(model_name: str, target: str, profile: str) -> dict[str, Any]:
    safe_profile = profile.replace(".", "_")
    return _node(
        {
            "identity": _identity(model_name, "export", f"{target}_{safe_profile}"),
            "type": "axm.artifact:ExportRequest",
            "schema_version": "0.1.0",
            "properties": {"target": target, "profile": profile, "state": "planned"},
        }
    )


TYPE_BY_KIND = {specification.kind: specification for specification in TYPES.values()}


def _kind_from_type(type_name: str, span: Span) -> str:
    specification = TYPES.get(type_name)
    if specification is None:
        raise AxiomataError(
            SEMANTIC_UNKNOWN_TYPE,
            f"unknown quantity type '{type_name}'",
            span,
        )
    return specification.kind


def _sample(kind: str) -> Quantity:
    specification = TYPE_BY_KIND[kind]
    return Quantity(
        Fraction(1),
        specification.dimension,
        specification.kind,
        specification.si_unit,
    )


def _first_conditional(expr: Expr) -> ConditionalExpr | None:
    if isinstance(expr, ConditionalExpr):
        return expr
    if isinstance(expr, UnaryExpr):
        return _first_conditional(expr.value)
    if isinstance(expr, BinaryExpr):
        return _first_conditional(expr.left) or _first_conditional(expr.right)
    if isinstance(expr, CallExpr):
        for argument in expr.arguments:
            found = _first_conditional(argument)
            if found is not None:
                return found
    return None


def _reject_control_expressions_in_base_profile(model: Model) -> None:
    expressions: list[Expr] = []
    for statement in model.statements:
        if isinstance(statement, FunctionStmt):
            if isinstance(statement.body, Expr):
                expressions.append(statement.body)
        elif isinstance(statement, LetStmt):
            expressions.append(statement.expression)
        elif isinstance(statement, FrameStmt):
            expressions.extend(statement.arguments)
        elif isinstance(statement, GeometryStmt):
            expressions.extend(statement.arguments)
        elif isinstance(statement, RequireStmt):
            expressions.extend((statement.left, statement.right))
        for expression in expressions:
            conditional = _first_conditional(expression)
            if conditional is not None:
                raise AxiomataError(
                    SEMANTIC_INVALID_OPERATION,
                    "conditional expression requires the AXM control profile",
                    conditional.span,
                )
        expressions.clear()


def _infer_kind(
    expr: Expr,
    environment: dict[str, Quantity],
    locals_: dict[str, str],
    functions: AxmFunctionCatalog,
    allow_globals: bool,
) -> str:
    if isinstance(expr, LiteralExpr):
        return literal(expr.spelling, expr.unit, expr.span).kind
    if isinstance(expr, NameExpr):
        local = locals_.get(expr.name)
        if local is not None:
            return local
        global_value = environment.get(expr.name)
        if global_value is not None:
            if not allow_globals:
                raise AxiomataError(
                    SEMANTIC_INVALID_OPERATION,
                    f"function body cannot capture model quantity '{expr.name}'",
                    expr.span,
                )
            return global_value.kind
        raise AxiomataError(
            SEMANTIC_UNKNOWN_NAME, f"unknown quantity '{expr.name}'", expr.span
        )
    if isinstance(expr, UnaryExpr):
        if expr.operator != "-":
            raise AxiomataError(
                SEMANTIC_INVALID_OPERATION,
                f"unsupported unary operator '{expr.operator}'",
                expr.span,
            )
        return _infer_kind(
            expr.value, environment, locals_, functions, allow_globals
        )
    if isinstance(expr, BinaryExpr):
        left = _sample(
            _infer_kind(expr.left, environment, locals_, functions, allow_globals)
        )
        right = _sample(
            _infer_kind(expr.right, environment, locals_, functions, allow_globals)
        )
        if expr.operator == "+":
            return add(left, right, expr.span).kind
        if expr.operator == "-":
            return subtract(left, right, expr.span).kind
        if expr.operator == "*":
            return multiply(left, right, expr.span).kind
        if expr.operator == "/":
            return divide(left, right, expr.span).kind
        raise AxiomataError(
            SEMANTIC_INVALID_OPERATION,
            f"unsupported binary operator '{expr.operator}'",
            expr.span,
        )
    if isinstance(expr, CallExpr):
        function = functions.get(expr.callee)
        if function is None:
            raise AxiomataError(
                SEMANTIC_UNKNOWN_NAME,
                f"unknown function '{expr.callee}'",
                expr.span,
            )
        if len(expr.arguments) != len(function.parameters):
            raise AxiomataError(
                SEMANTIC_TYPE_MISMATCH,
                f"function '{expr.callee}' expects {len(function.parameters)} "
                f"arguments, got {len(expr.arguments)}",
                expr.span,
            )
        for index, (argument, parameter) in enumerate(
            zip(expr.arguments, function.parameters, strict=True), start=1
        ):
            actual = _infer_kind(
                argument, environment, locals_, functions, allow_globals
            )
            if actual != parameter.kind:
                raise AxiomataError(
                    SEMANTIC_TYPE_MISMATCH,
                    f"argument {index} of function '{expr.callee}' expects "
                    f"{parameter.kind}, got {actual}",
                    argument.span,
                )
        return function.result
    if isinstance(expr, ConditionalExpr):
        left = _infer_kind(
            expr.condition_left, environment, locals_, functions, allow_globals
        )
        right = _infer_kind(
            expr.condition_right, environment, locals_, functions, allow_globals
        )
        if left != right:
            raise AxiomataError(
                SEMANTIC_TYPE_MISMATCH,
                "conditional comparison operands must have the same quantity kind",
                expr.span,
            )
        when_true = _infer_kind(
            expr.when_true, environment, locals_, functions, allow_globals
        )
        when_false = _infer_kind(
            expr.when_false, environment, locals_, functions, allow_globals
        )
        if when_true != when_false:
            raise AxiomataError(
                SEMANTIC_TYPE_MISMATCH,
                "conditional branches must have the same quantity kind",
                expr.span,
            )
        return when_true
    raise TypeError(f"unknown expression type {type(expr).__name__}")


def _evaluate(
    expr: Expr,
    environment: dict[str, Quantity],
    functions: AxmFunctionCatalog,
    exact_functions: ExactFunctionModule,
) -> Quantity:
    if isinstance(expr, LiteralExpr):
        return literal(expr.spelling, expr.unit, expr.span)
    if isinstance(expr, NameExpr):
        if expr.name not in environment:
            raise AxiomataError(
                SEMANTIC_UNKNOWN_NAME, f"unknown quantity '{expr.name}'", expr.span
            )
        return environment[expr.name]
    if isinstance(expr, UnaryExpr):
        if expr.operator == "-":
            return negate(_evaluate(expr.value, environment, functions, exact_functions))
        raise AxiomataError(
            SEMANTIC_INVALID_OPERATION,
            f"unsupported unary operator '{expr.operator}'",
            expr.span,
        )
    if isinstance(expr, BinaryExpr):
        left = _evaluate(expr.left, environment, functions, exact_functions)
        right = _evaluate(expr.right, environment, functions, exact_functions)
        if expr.operator == "+":
            return add(left, right, expr.span)
        if expr.operator == "-":
            return subtract(left, right, expr.span)
        if expr.operator == "*":
            return multiply(left, right, expr.span)
        if expr.operator == "/":
            return divide(left, right, expr.span)
        raise AxiomataError(
            SEMANTIC_INVALID_OPERATION,
            f"unsupported binary operator '{expr.operator}'",
            expr.span,
        )
    if isinstance(expr, CallExpr):
        function = functions.get(expr.callee)
        if function is None:
            raise AxiomataError(
                SEMANTIC_UNKNOWN_NAME,
                f"unknown function '{expr.callee}'",
                expr.span,
            )
        if len(expr.arguments) != len(function.parameters):
            raise AxiomataError(
                SEMANTIC_TYPE_MISMATCH,
                f"function '{expr.callee}' expects {len(function.parameters)} "
                f"arguments, got {len(expr.arguments)}",
                expr.span,
            )
        argument_values = []
        for index, (argument, parameter) in enumerate(
            zip(expr.arguments, function.parameters, strict=True), start=1
        ):
            value = _evaluate(argument, environment, functions, exact_functions)
            if value.kind != parameter.kind:
                raise AxiomataError(
                    SEMANTIC_TYPE_MISMATCH,
                    f"argument {index} of function '{expr.callee}' expects "
                    f"{parameter.kind}, got {value.kind}",
                    argument.span,
                )
            argument_values.append(value)
        arguments = tuple(argument_values)
        try:
            return execute_exact_function(
                exact_functions, function.identity, arguments
            )
        except ExactFunctionExecutionError as error:
            if error.code == AXVM_ARITHMETIC and error.message.endswith(
                "division by zero"
            ):
                raise AxiomataError(
                    SEMANTIC_DIVISION_BY_ZERO,
                    "division by zero",
                    expr.span,
                ) from error
            message = (
                "function execution resource limit exceeded"
                if error.code == AXVM_RESOURCE_LIMIT
                else error.message
            )
            raise AxiomataError(
                SEMANTIC_INVALID_OPERATION, message, expr.span
            ) from error
    if isinstance(expr, ConditionalExpr):
        left = _evaluate(
            expr.condition_left, environment, functions, exact_functions
        )
        right = _evaluate(
            expr.condition_right, environment, functions, exact_functions
        )
        selected = expr.when_true if compare(
            left, right, expr.operator, expr.span
        ) else expr.when_false
        return _evaluate(selected, environment, functions, exact_functions)
    raise TypeError(f"unknown expression type {type(expr).__name__}")


def _require_length_kind(
    value: Quantity, label: str, span: Span, code: str = SEMANTIC_TYPE_MISMATCH
) -> None:
    if value.dimension != LENGTH or value.kind != "length":
        raise AxiomataError(code, f"{label} must be Length", span)


def _require_positive_length(value: Quantity, label: str, span: Span) -> None:
    _require_length_kind(value, label, span, SEMANTIC_GEOMETRY)
    if value.value <= 0:
        raise AxiomataError(
            SEMANTIC_GEOMETRY, f"{label} must be greater than zero", span
        )


def _volume(length: Quantity, width: Quantity, height: Quantity) -> Quantity:
    return Quantity(
        length.value * width.value * height.value,
        VOLUME,
        "volume",
        "m3",
    )


def compile_source(source: str) -> Compilation:
    model = parse(source)
    _reject_control_expressions_in_base_profile(model)
    environment: dict[str, Quantity] = {}
    geometries: dict[str, GeometryValue] = {}
    frames: dict[str, FrameValue] = {}
    entities: set[str] = set()
    all_names: set[str] = set()
    functions: AxmFunctionCatalog = {}
    function_names_by_id: dict[int, str] = {}
    function_definitions = []
    exact_functions = ExactFunctionModule(())
    exact_functions_current = True
    nodes: list[dict[str, Any]] = []
    pending_exports: list[ExportStmt] = []
    unit_system_seen = False
    requirement_ordinal = 0

    def runtime_functions() -> ExactFunctionModule:
        nonlocal exact_functions, exact_functions_current
        if not exact_functions_current:
            function_ir = AxirFunctionModule(tuple(function_definitions))
            exact_functions = lower_axir_function_module(function_ir)
            exact_functions_current = True
        return exact_functions

    def reserve(name: str, span: Span) -> None:
        if name == "WorldFrame":
            raise AxiomataError(
                SEMANTIC_DUPLICATE_NAME,
                "name 'WorldFrame' conflicts with built-in frame",
                span,
            )
        if name in all_names:
            raise AxiomataError(
                SEMANTIC_DUPLICATE_NAME, f"duplicate model name '{name}'", span
            )
        all_names.add(name)

    for stmt in model.statements:
        if isinstance(stmt, UnitSystemStmt):
            if unit_system_seen:
                raise AxiomataError(
                    SEMANTIC_UNIT_SYSTEM,
                    "unit_system may be declared only once",
                    stmt.span,
                )
            if stmt.name != "SI":
                raise AxiomataError(
                    SEMANTIC_UNIT_SYSTEM,
                    "only unit_system SI is supported in v0.1",
                    stmt.span,
                )
            unit_system_seen = True
        elif isinstance(stmt, FunctionStmt):
            if stmt.exported:
                raise AxiomataError(
                    SEMANTIC_INVALID_OPERATION,
                    "exported function requires the AXM module profile",
                    stmt.span,
                )
            reserve(stmt.name, stmt.span)
            if not isinstance(stmt.body, Expr):
                raise AxiomataError(
                    SEMANTIC_INVALID_OPERATION,
                    "function block requires the AXM block profile",
                    stmt.body.span,
                )
            if len(functions) >= 4_096:
                raise AxiomataError(
                    SEMANTIC_INVALID_OPERATION,
                    "source function definition budget is exhausted",
                    stmt.span,
                )
            if len(stmt.parameters) > 65_535:
                raise AxiomataError(
                    SEMANTIC_INVALID_OPERATION,
                    "source function parameter budget is exhausted",
                    stmt.span,
                )
            parameter_names: set[str] = set()
            locals_: dict[str, str] = {}
            parameters: list[AxmFunctionParameterType] = []
            for parameter in stmt.parameters:
                if parameter.name in parameter_names:
                    raise AxiomataError(
                        SEMANTIC_DUPLICATE_NAME,
                        f"duplicate function parameter '{parameter.name}'",
                        parameter.span,
                    )
                parameter_names.add(parameter.name)
                kind = _kind_from_type(parameter.type_name, parameter.span)
                locals_[parameter.name] = kind
                parameters.append(AxmFunctionParameterType(parameter.name, kind))
            result = _kind_from_type(stmt.result_type_name, stmt.span)
            actual = _infer_kind(stmt.body, environment, locals_, functions, False)
            if actual != result:
                raise AxiomataError(
                    SEMANTIC_TYPE_MISMATCH,
                    f"function '{stmt.name}' result expects {stmt.result_type_name}, "
                    f"got {actual}",
                    stmt.body.span,
                )
            signature = AxmFunctionSignature(
                len(functions), stmt.name, tuple(parameters), result
            )
            functions[stmt.name] = signature
            function_names_by_id[signature.identity] = signature.name
            definition = lower_axm_function_definition(stmt, functions)
            function_definitions.append(definition)
            nodes.append(
                _function_node(
                    model.name, signature, definition, function_names_by_id
                )
            )
            exact_functions_current = False
        elif isinstance(stmt, LetStmt):
            reserve(stmt.name, stmt.span)
            _infer_kind(stmt.expression, environment, {}, functions, True)
            value = assert_declared_type(
                _evaluate(
                    stmt.expression, environment, functions, runtime_functions()
                ),
                stmt.type_name,
                stmt.span,
            )
            environment[stmt.name] = value
            nodes.append(_quantity_node(model.name, stmt.name, value))
        elif isinstance(stmt, EntityStmt):
            reserve(stmt.name, stmt.span)
            entities.add(stmt.name)
            nodes.append(_entity_node(model.name, stmt))
        elif isinstance(stmt, FrameStmt):
            reserve(stmt.name, stmt.span)
            parent = "axm.core:WorldFrame" if stmt.parent == "WorldFrame" else frames.get(stmt.parent)
            if parent is None:
                raise AxiomataError(
                    SEMANTIC_FRAME, f"unknown parent frame '{stmt.parent}'", stmt.span
                )
            parent_identity = parent if isinstance(parent, str) else parent.identity
            rotation = FRAME_ROTATIONS.get(stmt.operation)
            if rotation is None and stmt.operation != "translated":
                raise AxiomataError(
                    SEMANTIC_FRAME,
                    f"unsupported frame operation '{stmt.operation}'",
                    stmt.span,
                )
            if stmt.operation == "aligned" or stmt.operation.startswith("rotated_z"):
                if stmt.arguments:
                    raise AxiomataError(
                        SEMANTIC_FRAME,
                        f"frame operation '{stmt.operation}' does not accept translation values",
                        stmt.span,
                    )
                translation = (
                    Quantity(Fraction(0), LENGTH, "length", "m"),
                    Quantity(Fraction(0), LENGTH, "length", "m"),
                    Quantity(Fraction(0), LENGTH, "length", "m"),
                )
            else:
                if len(stmt.arguments) != 3:
                    raise AxiomataError(
                        SEMANTIC_FRAME,
                        "translated requires exactly x, y, and z lengths",
                        stmt.span,
                    )
                translation = tuple(
                    _evaluate(argument, environment, functions, runtime_functions())
                    for argument in stmt.arguments
                )
                for coordinate in translation:
                    _require_length_kind(
                        coordinate, "frame translation coordinate", stmt.span, SEMANTIC_FRAME
                    )
                rotation = IDENTITY_ROTATION
            frame = FrameValue(
                stmt.name,
                _identity(model.name, "frame", stmt.name),
                parent_identity,
                rotation,
                translation,
            )
            frames[stmt.name] = frame
            nodes.append(_frame_node(frame))
        elif isinstance(stmt, GeometryStmt):
            reserve(stmt.name, stmt.span)
            if stmt.operation != "box":
                raise AxiomataError(
                    SEMANTIC_GEOMETRY,
                    "only geometry operation box(...) is supported in v0.1",
                    stmt.span,
                )
            if len(stmt.arguments) != 3:
                raise AxiomataError(
                    SEMANTIC_GEOMETRY,
                    "box requires exactly length, width, and height",
                    stmt.span,
                )
            values = tuple(
                _evaluate(argument, environment, functions, runtime_functions())
                for argument in stmt.arguments
            )
            for label, value in zip(("box length", "box width", "box height"), values):
                _require_positive_length(value, label, stmt.span)
            selected_frame = "axm.core:WorldFrame" if stmt.frame is None else frames.get(stmt.frame)
            if selected_frame is None:
                raise AxiomataError(
                    SEMANTIC_FRAME, f"unknown geometry frame '{stmt.frame}'", stmt.span
                )
            frame_identity = selected_frame if isinstance(selected_frame, str) else selected_frame.identity
            geometry = GeometryValue(stmt.name, "box", frame_identity, values, _volume(*values))
            geometries[stmt.name] = geometry
            nodes.append(_geometry_node(model.name, geometry))
        elif isinstance(stmt, MeasureStmt):
            reserve(stmt.name, stmt.span)
            if stmt.operation != "volume":
                raise AxiomataError(
                    SEMANTIC_GEOMETRY,
                    "only measurement volume(...) is supported in v0.1",
                    stmt.span,
                )
            geometry = geometries.get(stmt.target)
            if geometry is None:
                raise AxiomataError(
                    SEMANTIC_UNKNOWN_NAME,
                    f"unknown geometry '{stmt.target}'",
                    stmt.span,
                )
            environment[stmt.name] = geometry.volume
            nodes.append(_quantity_node(model.name, stmt.name, geometry.volume))
        elif isinstance(stmt, RequireStmt):
            left = _evaluate(stmt.left, environment, functions, runtime_functions())
            right = _evaluate(stmt.right, environment, functions, runtime_functions())
            passed = compare(left, right, stmt.operator, stmt.span)
            if not passed:
                raise AxiomataError(
                    SEMANTIC_REQUIREMENT_FAILED,
                    f"requirement failed: {left.kind} {stmt.operator} {right.kind}",
                    stmt.span,
                )
            requirement_ordinal += 1
            nodes.append(_requirement_node(model.name, requirement_ordinal, stmt, passed))
        elif isinstance(stmt, ExportStmt):
            pending_exports.append(stmt)
        else:
            raise TypeError(f"unknown statement type {type(stmt).__name__}")

    if not unit_system_seen:
        raise AxiomataError(
            SEMANTIC_UNIT_SYSTEM, "unit_system SI; is required", model.span
        )

    for stmt in pending_exports:
        target_kind = "geometry" if stmt.target in geometries else "scalar" if stmt.target in environment else None
        if target_kind is None:
            raise AxiomataError(
                SEMANTIC_EXPORT, f"unknown export target '{stmt.target}'", stmt.span
            )
        allowed = GEOMETRY_PROFILES if target_kind == "geometry" else SCALAR_PROFILES
        for profile in stmt.profiles:
            if profile not in allowed:
                raise AxiomataError(
                    SEMANTIC_EXPORT,
                    f"profile '{profile}' cannot export {target_kind} target '{stmt.target}'",
                    stmt.span,
                )
            nodes.append(_export_node(model.name, stmt.target, profile))

    nodes.sort(key=lambda node: node["identity"])
    semantic_payload: dict[str, Any] = {
        "schema": "axg/0.1",
        "model_identity": f"axm://local/{model.name}/model",
        "parent_digests": [],
        "package_lock": [
            {"identity": "axm.core", "version": "0.1.0"},
            {"identity": "axm.geometry", "version": "0.1.0"},
            {"identity": "axm.requirements", "version": "0.1.0"},
            {"identity": "axm.artifact", "version": "0.1.0"},
        ],
        "policy_refs": [],
        "nodes": nodes,
        "edges": [],
        "artifact_refs": [],
        "provenance_refs": [],
    }
    semantic_digest = "sha256:" + sha256_digest(semantic_payload)
    axg = dict(semantic_payload)
    axg["semantic_digest"] = semantic_digest
    axg["revision_digest"] = "sha256:" + sha256_digest(axg)
    function_ir = AxirFunctionModule(tuple(function_definitions))
    validate_axir_function_module(function_ir)
    return Compilation(model, axg, functions, function_ir, dict(environment))
