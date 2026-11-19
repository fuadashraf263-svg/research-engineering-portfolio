"""Versioned identity constants shared by Axiomata v0 contract code."""

EXECUTION_SEMANTICS = "axiomata.execution.exact_quantity_replay/0.1.0"
COMPILER_CONTRACT = "axiomata.compiler.contract/0.1.0"
RUNTIME_CONTRACT = "axiomata.axvm/0.1.0"
FUNCTION_COMPILER_CONTRACT = "axiomata.compiler.contract/0.2.0"
FUNCTION_RUNTIME_CONTRACT = "axiomata.functions.exact/0.1.0"
CONTROL_COMPILER_CONTRACT = "axiomata.compiler.contract/0.3.0"
CONTROL_RUNTIME_CONTRACT = "axiomata.functions.control/0.1.0"
BLOCK_COMPILER_CONTRACT = "axiomata.compiler.contract/0.4.0"
BLOCK_RUNTIME_CONTRACT = "axiomata.functions.control/0.1.0"
MODULE_COMPILER_CONTRACT = "axiomata.compiler.contract/0.5.0"
MODULE_RUNTIME_CONTRACT = "axiomata.functions.control/0.1.0"
AGGREGATE_CONTROL_EXECUTION_SEMANTICS = (
    "axiomata.execution.aggregate-control-replay/0.1.0"
)
AGGREGATE_CONTROL_COMPILER_CONTRACT = "axiomata.compiler.contract/0.6.0"
AGGREGATE_CONTROL_RUNTIME_CONTRACT = (
    "axiomata.functions.aggregate-control/0.1.0"
)
DEPENDENCY_IDENTITIES = [
    "axiomata.axir/0.1.0",
    "axiomata.axm/0.1.0",
    "axiomata.axvm/0.1.0",
    "axiomata.diagnostics/0.1.0",
    "axiomata.units.si/0.1.0",
]
FUNCTION_DEPENDENCY_IDENTITIES = [
    "axiomata.axir.functions/0.1.0",
    "axiomata.axm.functions/0.1.0",
    "axiomata.axm/0.1.0",
    "axiomata.diagnostics/0.1.0",
    "axiomata.functions.exact/0.1.0",
    "axiomata.units.si/0.1.0",
]
CONTROL_DEPENDENCY_IDENTITIES = [
    "axiomata.axir.control/0.1.0",
    "axiomata.axm.conditionals/0.1.0",
    "axiomata.axm.functions/0.1.0",
    "axiomata.axm/0.1.0",
    "axiomata.diagnostics/0.1.0",
    "axiomata.functions.control/0.1.0",
    "axiomata.units.si/0.1.0",
]
BLOCK_DEPENDENCY_IDENTITIES = [
    "axiomata.axir.control/0.1.0",
    "axiomata.axm.blocks/0.1.0",
    "axiomata.axm.conditionals/0.1.0",
    "axiomata.axm.functions/0.1.0",
    "axiomata.axm/0.1.0",
    "axiomata.diagnostics/0.1.0",
    "axiomata.functions.control/0.1.0",
    "axiomata.units.si/0.1.0",
]
MODULE_DEPENDENCY_IDENTITIES = [
    "axiomata.axg.modules/0.1.0",
    "axiomata.axir.control/0.1.0",
    "axiomata.axm.blocks/0.1.0",
    "axiomata.axm.conditionals/0.1.0",
    "axiomata.axm.functions/0.1.0",
    "axiomata.axm.modules/0.1.0",
    "axiomata.axm/0.1.0",
    "axiomata.diagnostics/0.1.0",
    "axiomata.functions.control/0.1.0",
    "axiomata.package.lock/0.1.0",
    "axiomata.units.si/0.1.0",
]
AGGREGATE_CONTROL_DEPENDENCY_IDENTITIES = [
    "axiomata.axg.aggregate-control/0.1.0",
    "axiomata.axir.aggregate-control/0.1.0",
    "axiomata.axm.struct-control/0.1.0",
    "axiomata.axm.structs/0.1.0",
    "axiomata.diagnostics/0.1.0",
    "axiomata.functions.aggregate-control/0.1.0",
    "axiomata.units.si/0.1.0",
    "axiomata.values.aggregates/0.1.0",
]
