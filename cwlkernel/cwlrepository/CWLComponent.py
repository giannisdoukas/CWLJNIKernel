import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from io import StringIO
from typing import Dict, List, Union, Optional

from ruamel import yaml


class WorkflowComponent(ABC):
    _id: str

    def __init__(self, workflow_id: str, component: Optional[Dict]):
        self._id: str = workflow_id
        if component is not None:
            if isinstance(component['inputs'], Dict):
                component['inputs'] = self._convert_inputs_from_dict_to_list(component['inputs'])
            if isinstance(component['outputs'], Dict):
                component['outputs'] = self._convert_inputs_from_dict_to_list(component['outputs'])

    @property
    def id(self) -> str:
        return self._id

    @abstractmethod
    def to_yaml(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> Dict:
        pass

    @property
    @abstractmethod
    def inputs(self) -> List[Dict]:
        pass

    @property
    @abstractmethod
    def outputs(self) -> List[Dict]:
        pass

    @abstractmethod
    def compose_requirements(self) -> Dict:
        pass

    @classmethod
    def _convert_inputs_from_dict_to_list(cls, inputs: Dict) -> List[Dict]:
        return [{'id': id, **cwl_input} for id, cwl_input in inputs.items()]

    @classmethod
    def _convert_outputs_from_dict_to_list(cls, outputs: Dict) -> List[Dict]:
        return [{'id': id, **cwl_output} for id, cwl_output in outputs.items()]

    def get_output(self, output_id: str) -> Optional[Dict]:
        for out in self.outputs:
            if out['id'] == output_id:
                return out
        return None

    def get_input(self, input_id: str) -> Optional[Dict]:
        for inp in self.inputs:
            if inp['id'] == input_id:
                return inp
        return None


class CWLTool(WorkflowComponent):

    def __init__(self, workflow_id: str, command_line_tool: Dict):
        super().__init__(workflow_id, command_line_tool)
        self._command_line_tool = command_line_tool

    @property
    def command_line_tool(self) -> Dict:
        return self._command_line_tool

    @command_line_tool.setter
    def command_line_tool(self, command_line_tool: Dict):
        self._command_line_tool = command_line_tool

    def to_yaml(self) -> str:
        yaml_text = StringIO()
        yaml.dump(self.command_line_tool, yaml_text)
        return yaml_text.getvalue()

    def to_dict(self) -> Dict:
        return deepcopy(self.command_line_tool)

    @property
    def inputs(self) -> List[Dict]:
        return deepcopy(self._command_line_tool['inputs'])

    @property
    def outputs(self) -> List[Dict]:
        return deepcopy(self._command_line_tool['outputs'])

    def _packed_steps(self) -> Dict:
        to_return = self.to_dict()
        to_return.pop('cwlVersion')
        return to_return

    def compose_requirements(self) -> Dict:
        return {}


class CWLWorkflow(WorkflowComponent):

    def __init__(self, workflow_id: str, workflow: Optional[Dict] = None) -> None:
        super().__init__(workflow_id, workflow)
        if workflow is None:
            self._inputs: List[Dict] = []
            self._outputs: List[Dict] = []
            self._steps: Dict = {}
            self._requirements: Dict = {}
        else:
            self._inputs: List[Dict] = deepcopy(workflow['inputs'])
            self._outputs: List[Dict] = deepcopy(workflow['outputs'])
            self._steps: Dict = deepcopy(workflow['steps'])
            self._requirements = {}
            if 'requirements' in workflow:
                self._requirements: Dict = deepcopy(workflow['requirements'])

    @property
    def steps(self):
        steps = {}
        for step in self._steps:
            steps[step] = deepcopy(self._steps[step])
            if not isinstance(steps[step]['run'], str):
                steps[step]['run'] = steps[step]['run'][1]
        return deepcopy(steps)

    def add(self, component: WorkflowComponent, step_name: str, run_reference: Optional[str] = None) -> None:
        if run_reference is None:
            run_reference = f'{component.id}.cwl'
        self._steps[step_name] = {
            'run': (component, run_reference),
            'in': {},
            'out': []
        }
        self._requirements = {**self._requirements, **component.compose_requirements()}

    def remove(self, component: WorkflowComponent) -> None:
        raise NotImplementedError()

    def add_input(self, workflow_input: Dict, step_id: str, in_step_id: str):
        self._inputs.append(workflow_input)
        self._steps[step_id]['in'][in_step_id] = workflow_input['id']
        self._inputs = list({inp['id']: inp for inp in self._inputs}.values())

    def add_output_source(self, output_ref: str, type_of: str):
        references = output_ref.split('/')
        output_id = references[-1]
        references = references[:-1]
        self._outputs.append(
            {'id': output_id, 'type': type_of, 'outputSource': output_ref}
        )
        self._steps[references[0]]['out'].append(output_id)
        self._steps[references[0]]['out'] = list(set(self._steps[references[0]]['out']))

    def to_yaml(self) -> str:
        yaml_text = StringIO()
        result = self.to_dict()
        yaml.dump(result, yaml_text)
        yaml_str = yaml_text.getvalue()
        return yaml_str

    def to_dict(self) -> Dict:
        return {
            'cwlVersion': 'v1.0',
            'class': 'Workflow',
            'id': self.id,
            'inputs': self._inputs,
            'outputs': self._outputs,
            'steps': self.steps,
            'requirements': self._requirements
        }

    def validate(self):
        raise NotImplementedError()

    def add_step_in_out(self, connect: Union[str, dict], step_in_name: str, step_in: str,
                        step_out: Optional[str] = None, step_out_id: Optional[str] = None):
        self._steps[step_in]['in'][step_in_name] = deepcopy(connect)
        if step_out is not None and step_out_id is not None:
            self._steps[step_out]['out'].append(step_out_id)

    @property
    def inputs(self) -> List[Dict]:
        return deepcopy(self._inputs)

    @property
    def outputs(self) -> List[Dict]:
        return deepcopy(self._outputs)

    def compose_requirements(self) -> Dict:
        return {'SubworkflowFeatureRequirement': {}}


class WorkflowComponentFactory:
    def get_workflow_component(self, yaml_string: str) -> WorkflowComponent:
        component = yaml.safe_load(StringIO(yaml_string))
        if 'id' not in component:
            component['id'] = str(uuid.uuid4())
        if component['class'] == 'CommandLineTool':
            return CWLTool(component['id'], component)
        elif component['class'] == 'Workflow':
            return CWLWorkflow(component['id'], component)
        else:
            raise NotImplementedError(f"class f{component['class']} is not supported")


if __name__ == '__main__':
    pass
