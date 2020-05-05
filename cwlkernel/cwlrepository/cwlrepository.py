from collections import Iterable
from copy import deepcopy
from typing import Dict, Iterator, Optional


class ToolsRepository(Iterable):
    class __SingletonToolsRepository__:
        _registry: Dict

        def __init__(self):
            self._registry = {}

        def validate(self, tool: Dict):
            """
            :raises TypeError if the tool is not type of dict
            :raises MissingIdError if there is not id in the tool/inputs/outputs
            :param tool:
            :return:
            """
            if not isinstance(tool, dict):
                raise TypeError(f'Tool should be type of dict and not {type(tool)}')
            if 'id' not in tool:
                raise MissingIdError('Missing tool\'s id')
            if 'inputs' in tool and 'id':
                for input in tool['inputs']:
                    if 'id' not in input:
                        raise MissingIdError(f'Missing id for input: {input}')
            if 'outputs' in tool and 'id':
                for output in tool['outputs']:
                    if 'id' not in output:
                        raise MissingIdError(f'Missing id for outputs: {output}')

        def register_tool(self, tool: Dict) -> None:
            self.validate(tool)
            if tool['id'] in self._registry:
                raise KeyError(f'Dublicate key error: {tool["id"]}')
            self._registry[tool['id']] = deepcopy(tool)

        def register_tools(self, *args):
            for tool in args:
                self.register_tool(tool)

        def get_by_id(self, id: str) -> Optional[Dict]:
            return self._registry.get(id, None)

        def __iter__(self) -> Iterator[Dict]:
            for tool in self._registry.values():
                yield tool

        def delete(self):
            self._registry = {}

    __repo__: __SingletonToolsRepository__ = None

    def __init__(self):
        if ToolsRepository.__repo__ is None:
            ToolsRepository.__repo__ = ToolsRepository.__SingletonToolsRepository__()

    def __getattr__(self, item):
        return getattr(ToolsRepository.__repo__, item)

    def __iter__(self) -> Iterator[Dict]:
        for tool in ToolsRepository.__repo__:
            yield tool

    @classmethod
    def get_instance(cls) -> Optional:
        return cls.__repo__


class MissingIdError(Exception):
    pass
