import functools
import logging
import os
import sys
import tempfile
import traceback
from pathlib import Path
from subprocess import DEVNULL
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    NoReturn, cast, IO, MutableMapping, MutableSequence)
from uuid import uuid4, UUID

from cwltool.context import RuntimeContext, LoadingContext
from cwltool.executors import JobExecutor
from cwltool.factory import Factory
from cwltool.load_tool import fetch_document
from cwltool.loghandler import _logger
from cwltool.main import ProvLogFormatter, prov_deps
from cwltool.process import add_sizes
from cwltool.provenance import ResearchObject
from cwltool.stdfsaccess import StdFsAccess
from cwltool.utils import CWLObjectType, visit_class, DEFAULT_TMP_PREFIX
from ruamel import yaml

from .IOManager import IOFileManager


class JupyterFactory(Factory):

    def __init__(self, root_directory: str,
                 executor: Optional[JobExecutor] = None,
                 loading_context: Optional[LoadingContext] = None,
                 runtime_context: Optional[RuntimeContext] = None, ):
        super().__init__(
            executor=executor,
            loading_context=loading_context,
            runtime_context=runtime_context,
        )
        self.runtime_context.outdir = root_directory
        self.runtime_context.basedir = root_directory
        self.runtime_context.default_stdout = DEVNULL
        self.runtime_context.default_stderr = DEVNULL
        # If on MacOS platform, TMPDIR must be set to be under one of the
        # shared volumes in Docker for Mac
        # More info: https://dockstore.org/docs/faq
        if sys.platform == "darwin":
            default_mac_path = "/private/tmp/docker_tmp"
            if self.runtime_context.tmp_outdir_prefix == DEFAULT_TMP_PREFIX:
                self.runtime_context.tmp_outdir_prefix = default_mac_path
            if self.runtime_context.tmpdir_prefix == DEFAULT_TMP_PREFIX:
                self.runtime_context.tmpdir_prefix = default_mac_path


class ProvenanceFactory(JupyterFactory):

    def __init__(self,
                 workflow_uri_path: str,
                 root_directory: str,
                 stove_provenance_directory: str,
                 executor: Optional[JobExecutor] = None,
                 loading_context: Optional[LoadingContext] = None,
                 runtime_context: Optional[RuntimeContext] = None) -> None:
        """Easy way to load a CWL document for execution."""
        super().__init__(
            root_directory=root_directory,
            executor=executor,
            loading_context=loading_context,
            runtime_context=runtime_context
        )
        self.store_provenance_directory = stove_provenance_directory
        self.loading_context, self.workflow_object, self.uri = fetch_document(workflow_uri_path, self.loading_context)
        make_fs_access = self.runtime_context.make_fs_access \
            if self.runtime_context.make_fs_access is not None else StdFsAccess
        ro = ResearchObject(
            make_fs_access(""),
        )
        self.runtime_context.research_obj = ro
        log_file_io = ro.open_log_file_for_activity(ro.engine_uuid)
        prov_log_handler = logging.StreamHandler(cast(IO[str], log_file_io))
        prov_log_handler.setFormatter(ProvLogFormatter())
        _logger.addHandler(prov_log_handler)
        _logger.debug("[provenance] Logging to %s", log_file_io)


class CoreExecutor:

    def __init__(self, file_manager: IOFileManager, provenance_directory: Optional[Path]):
        self.file_manager = file_manager
        self._workflow_path = None
        self._data_paths = []
        self.provenance_directory = provenance_directory if provenance_directory is not None else tempfile.mkdtemp()

    def set_data(self, data: List[str]) -> List[str]:
        self._data_paths = [self.file_manager.write(f'{str(uuid4())}.yml', d.encode()) for d in data]
        return self._data_paths

    def set_workflow_path(self, workflow_str: str) -> str:
        """
        :param workflow_str: the cwl
        :return: the path where we executor stored the workflow
        """
        self._workflow_path = workflow_str
        return self._workflow_path

    def execute(self, provenance=False) -> Tuple[UUID, Dict, Optional[Exception], Optional[ResearchObject]]:
        """
        :param provenance: Execute with provenance enabled/disabled.
        :return: Run ID, dict with new files, exception if there is any.
        """
        exception_to_return = None
        run_id = uuid4()
        factory: JupyterFactory
        if not provenance:
            factory = JupyterFactory(self.file_manager.ROOT_DIRECTORY)
        else:
            provenance_dir = os.path.join(self.provenance_directory.as_posix(), 'provenance')
            factory = ProvenanceFactory(
                Path(self._workflow_path).as_uri(),
                self.file_manager.ROOT_DIRECTORY,
                provenance_dir
            )
        old_directory = os.getcwd()
        os.chdir(self.file_manager.ROOT_DIRECTORY)
        executable = factory.make(self._workflow_path)
        data = {}
        for data_file in self._data_paths:
            with open(data_file) as f:
                new_data = yaml.load(f, Loader=yaml.Loader)
                data = {**new_data, **data}
        try:
            result: Dict = executable(**data)
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            result = {}
            exception_to_return = e

        if provenance:
            self._store_provenance(cast(ProvenanceFactory, factory), result)
        os.chdir(old_directory)
        return run_id, result, exception_to_return, factory.runtime_context.research_obj

    @classmethod
    def _store_provenance(cls, factory: ProvenanceFactory, out) -> None:
        """Proxy method to cwltool's logic"""
        runtime_context = factory.runtime_context
        loading_context = factory.loading_context
        workflow_object = factory.workflow_object
        uri = factory.uri

        if runtime_context.research_obj is not None:
            runtime_context.research_obj.create_job(out, True)

            def remove_at_id(doc: CWLObjectType) -> None:
                for key in list(doc.keys()):
                    if key == "@id":
                        del doc[key]
                    else:
                        value = doc[key]
                        if isinstance(value, MutableMapping):
                            remove_at_id(value)
                        elif isinstance(value, MutableSequence):
                            for entry in value:
                                if isinstance(entry, MutableMapping):
                                    remove_at_id(entry)

            remove_at_id(out)
            visit_class(
                out,
                ("File",),
                functools.partial(add_sizes, runtime_context.make_fs_access("")),
            )

            research_obj = runtime_context.research_obj
            if loading_context.loader is not None:
                research_obj.generate_snapshot(
                    prov_deps(workflow_object, loading_context.loader, uri)
                )

            research_obj.close(factory.store_provenance_directory)

    @classmethod
    def validate_input_files(cls, yaml_input: Dict, cwd: Path) -> NoReturn:
        for arg in yaml_input:
            if isinstance(yaml_input[arg], dict) and 'class' in yaml_input[arg] and yaml_input[arg]['class'] == 'File':
                selector = 'location' if 'location' in yaml_input[arg] else 'path'
                file_path = Path(yaml_input[arg][selector])
                if not file_path.is_absolute():
                    file_path = cwd / file_path
                if not file_path.exists():
                    raise FileNotFoundError(file_path)
