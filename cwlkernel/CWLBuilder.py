from pathlib import Path
from abc import ABC, abstractmethod
from ruamel.yaml import ruamel
from cwlkernel.cwlrepository.CWLComponent import WorkflowComponent, CWLTool, CWLWorkflow
import os

class CWLBuilder(ABC):
    @abstractmethod
    def build(self) -> WorkflowComponent:
        pass


class CWLSnippetBuilder(CWLBuilder):
    _code: str
    _location: Path

    def __init__(self, location: Path):
        self._code = ""
        self._location = location

    def append(self, code: str, indent: int = 0) -> None:
        code = '\n'. \
            join([''.join([' ' for _ in range(indent)]) + line
                  for line in code.splitlines()])
        if self._code == "":
            self._code = str(code)
        else:
            self._code += '\n' + str(code)

    def get_current_code(self) -> str:
        return self._code

    def build(self) -> WorkflowComponent:
        code = ruamel.yaml.round_trip_load(self._code)
        with self._location.open('w') as f:
            ruamel.yaml.round_trip_dump(code, f)
        if code['class'] == 'CommandLineTool':
            return CWLTool(code.get('id', os.path.basename(self._location)), code)
        elif code['class'] == 'Workflow':
            return CWLWorkflow(code.get('id', os.path.basename(self._location)), code)