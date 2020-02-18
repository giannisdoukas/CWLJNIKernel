from typing import Dict, Tuple, Callable
import os

class CWLExecuteConfigurator:
    # property "Name of the property": ("default", validator)
    properties: Dict[str, Tuple[str, Callable]] = {
        'CWLKERNEL_MODE': ('SIMPLE', lambda value: value.upper() in {'SIMPLE'}), # no case sensitive
        'CWLKERNEL_BOOT_DIRECTORY': ('/tmp/CWLKERNEL_DATA', lambda value: True)
    }



    def __init__(self):
        for property, (default_value, validator) in self.properties.items():
            value = os.environ.get(property, default_value)
            if not validator(value):
                raise RuntimeError("Value {0} is not allowed for property {1}".format(value, property))
            self.__setattr__(
                property,
                value
            )
