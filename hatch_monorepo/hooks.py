from hatchling.plugin import hookimpl

from .plugin import MonorepoEnvironment


@hookimpl
def hatch_register_environment():
    return MonorepoEnvironment
