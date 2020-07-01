import os
from typing import Dict, Tuple, Callable


# TODO: use tempfile for windows compatibility

class CWLExecuteConfigurator:
    CWLKERNEL_MODE: str
    CWLKERNEL_BOOT_DIRECTORY: str
    CWLKERNEL_MAGIC_COMMANDS_DIRECTORY: str

    # property "Name of the property": ("default", validator)
    properties: Dict[str, Tuple[str, Callable]] = {
        'CWLKERNEL_MODE': ('SIMPLE', lambda value: value.upper() in {'SIMPLE'}),  # no case sensitive
        'CWLKERNEL_BOOT_DIRECTORY': ('/tmp/CWLKERNEL_DATA', lambda value: True),
        'CWLKERNEL_MAGIC_COMMANDS_DIRECTORY': (None, lambda value: value is None or os.path.isdir(value))
    }

    def __init__(self):
        """Kernel configurations."""
        for property_name, (default_value, validator) in self.properties.items():
            value = os.environ.get(property_name, default_value)
            if not validator(value):
                raise RuntimeError("Value {0} is not allowed for property {1}".format(value, property_name))
            self.__setattr__(
                property_name,
                value
            )
