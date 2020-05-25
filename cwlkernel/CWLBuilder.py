from abc import ABC, abstractmethod
import yaml
from cwlkernel.cwlrepository.CWLComponent import WorkflowComponent, CWLTool, CWLWorkflow
from io import StringIO


class CWLBuilder(ABC):
    @abstractmethod
    def build(self) -> WorkflowComponent:
        pass


class CWLSnippetBuilder(CWLBuilder):
    _code: str

    def __init__(self):
        self._code = ""

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
        code = yaml.load(StringIO(self._code), yaml.Loader)
        if 'id' not in code:
            raise ValueError("the workflow must contain an id")
        if code['class'] == 'CommandLineTool':
            return CWLTool(code.get('id'), code)
        elif code['class'] == 'Workflow':
            return CWLWorkflow(code.get('id'), code)

    def clear(self):
        self._code = ""
