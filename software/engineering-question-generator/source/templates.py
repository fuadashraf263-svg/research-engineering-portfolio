"""Imports every template module so REGISTRY is fully populated."""
import core
import tmpl_math   # noqa
# additional batches appended below as they are created
try:
    import tmpl_mech  # noqa
except ImportError:
    pass
try:
    import tmpl_elec  # noqa
except ImportError:
    pass
try:
    import tmpl_civil  # noqa
except ImportError:
    pass
try:
    import tmpl_cse  # noqa
except ImportError:
    pass
try:
    import tmpl_chem  # noqa
except ImportError:
    pass
try:
    import tmpl_misc  # noqa
except ImportError:
    pass
REGISTRY = core.REGISTRY
