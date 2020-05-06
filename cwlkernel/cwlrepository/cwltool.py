from copy import deepcopy
from typing import Dict, Union
from ruamel import yaml
from io import StringIO


class Tool:
    _tool: Dict

    def __init__(self, tool: Dict):
        self._tool = tool

    @classmethod
    def from_yaml(cls, yaml_str: str):
        # FIXME: use pack function from cwltool
        return cls(yaml.load(StringIO(yaml_str), Loader=yaml.Loader))

    def __getitem__(self, item):
        return self._tool[item]

    def start_composing(self, other, new_id: str):
        return Composer(self, other, new_id)

    def __contains__(self, item):
        return item in self._tool

class Workflow:
    _workflow: Dict


class Port:
    INPUT = 0
    OUTPUT = 1
    types = [INPUT, OUTPUT]
    type: int
    description: Dict

    def __init__(self, type: int, description: Dict):
        """
        :raises TypeError
        :param type:
        :param description:
        """
        if type not in self.types:
            raise TypeError()
        self.type = type
        self.description = description


class Composer:
    _tool1: Union[Workflow, Tool]
    _tool2: Union[Workflow, Tool]
    _composed_tool: Workflow

    def __init__(self, tool1, tool2, id: str):
        self._id = id
        self._tool1 = tool1
        self._tool2 = tool2

    def pending_ports(self) -> Dict:
        return {

            self._tool1['id']: {
                'inputs': deepcopy(self._tool1['inputs']),
                'outputs': deepcopy(self._tool1['outputs'])
            },
            self._tool2['id']: {
                'inputs': deepcopy(self._tool2['inputs']),
                'outputs': deepcopy(self._tool2['outputs'])
            }
        }

    def connect_port(self, input: Port, output: Port):
        raise NotImplementedError()

    def build(self) -> Workflow:
        raise NotImplementedError()
