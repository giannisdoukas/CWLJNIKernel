from io import StringIO
import argparse
import functools
import io
import logging
import os
import sys
from codecs import StreamWriter, getwriter
from io import StringIO
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    List,
    MutableMapping,
    MutableSequence,
    Optional,
    TextIO,
    Tuple,
    Union,
    cast,
)
from uuid import uuid4, UUID

import coloredlogs
from cwltool import command_line_tool
from cwltool.argparser import arg_parser, get_default_args
from cwltool.context import LoadingContext, RuntimeContext, getdefault
from cwltool.cwlrdf import printdot, printrdf
from cwltool.errors import WorkflowException, UnsupportedRequirement
from cwltool.executors import JobExecutor, MultithreadedJobExecutor, SingleJobExecutor
from cwltool.load_tool import resolve_tool_uri, load_overrides, fetch_document, resolve_and_validate_document, make_tool
from cwltool.loghandler import _logger, defaultStreamHandler
from cwltool.main import configure_logging, supported_cwl_versions, setup_schema, \
    setup_provenance, setup_loadingContext, load_job_order, printdeps, print_pack, make_template, choose_target, \
    init_job_order, prov_deps, check_working_directories, find_default_container
from cwltool.mutation import MutationManager
from cwltool.process import (
    add_sizes,
    shortname,
)
from cwltool.procgenerator import ProcessGenerator
from cwltool.resolver import ga4gh_tool_registries
from cwltool.secrets import SecretStore
from cwltool.software_requirements import DependenciesConfiguration
from cwltool.stdfsaccess import StdFsAccess
from cwltool.utils import versionstring, onWindows, windows_default_container_id, DEFAULT_TMP_PREFIX, visit_class
from ruamel.yaml.comments import CommentedMap
from schema_salad import validate
from schema_salad.ref_resolver import file_uri, uri_file_path
from schema_salad.sourceline import strip_dup_lineno
from schema_salad.utils import json_dumps

from .IOManager import IOFileManager


class CoreExecutor:

    def __init__(self, file_manager: IOFileManager):
        self.file_manager = file_manager
        self._workflow_path = None
        self._data_paths = []

    def set_data(self, data: List[str]) -> List[str]:
        self._data_paths = [self.file_manager.write(f'{str(uuid4())}.yml', d.encode()) for d in data]
        return self._data_paths

    def set_workflow(self, workflow_str: str) -> str:
        """
        :param workflow_str: the cwl
        :return: the path where we executor stored the workflow
        """
        self._workflow_path = self.file_manager.write(f'{str(uuid4())}.cwl', workflow_str.encode())
        return self._workflow_path

    def execute(self) -> Tuple[UUID, List[str], StringIO, StringIO, Optional[Exception]]:
        """
        :return: Run ID, List of new files, stdout, stderr, exception if there is any
        """
        run_id = uuid4()
        args = [self._workflow_path, *self._data_paths]
        stdout = StringIO()
        stderr = StringIO()

        try:
            created_files = self._cwltool_main(argsl=args, stderr=stderr, stdout=stdout)
            return run_id, created_files, stdout, stderr, None
        except Exception as e:
            return run_id, [], stdout, stderr, e


    @classmethod
    def _check_workflow_file(cls, args):
        if not args.workflow:
            if os.path.isfile("CWLFile"):
                setattr(args, "workflow", "CWLFile")
            else:
                _logger.error("CWL document required, no input file was provided")
                arg_parser().print_help()
                raise RuntimeError("CWL document required, no input file was provided")

    @classmethod
    def _cwltool_main(cls,
                      argsl: Optional[List[str]] = None,
                      stdin: IO[Any] = sys.stdin,
                      stdout: Optional[Union[TextIO, StreamWriter]] = None,
                      stderr: IO[Any] = sys.stderr,
                      logger_handler: Optional[logging.Handler] = None,
                      loading_context: Optional[LoadingContext] = None,
                      runtime_context: Optional[RuntimeContext] = None,
                      input_required: bool = True,
                      ) -> List[str]:
        """

        :param argsl:
        :param stdin:
        :param stdout:
        :param stderr:
        :param logger_handler:
        :param loading_context:
        :param runtime_context:
        :param input_required:
        :return: A list of the paths of created files by the workflow
        """

        stdout = cls._force_utf8_to_stream(stdout)

        stderr_handler = cls._init_cwl_logger(logger_handler, stderr)

        workflowobj = None
        prov_log_handler = None  # type: Optional[logging.StreamHandler]
        try:
            args, argsl = cls._parse_cwl_options(argsl)
            runtime_context = cls._init_runtime_context(argsl, args, runtime_context)
            configure_logging(args, stderr_handler, runtime_context)
            _logger.info(versionstring())
            cls._check_workflow_file(args)

            setup_schema(args, None)

            loading_context = setup_loadingContext(loading_context, runtime_context, args)

            uri, tool_file_uri = resolve_tool_uri(
                args.workflow,
                resolver=loading_context.resolver,
                fetcher_constructor=loading_context.fetcher_constructor,
            )

            try_again_msg = (
                "" if args.debug else ", try again with --debug for more information"
            )

            try:
                job_order_object, input_basedir, jobloader = load_job_order(
                    args,
                    stdin,
                    loading_context.fetcher_constructor,
                    loading_context.overrides_list,
                    tool_file_uri,
                )

                if args.overrides:
                    loading_context.overrides_list.extend(
                        load_overrides(
                            file_uri(os.path.abspath(args.overrides)), tool_file_uri
                        )
                    )

                loading_context, workflowobj, uri = fetch_document(uri, loading_context)

                loading_context, uri = resolve_and_validate_document(
                    loading_context,
                    workflowobj,
                    uri,
                    preprocess_only=(args.print_pre or args.pack),
                    skip_schemas=args.skip_schemas,
                )

                if loading_context.loader is None:
                    raise Exception("Impossible code path.")
                processobj, metadata = loading_context.loader.resolve_ref(uri)
                processobj = cast(CommentedMap, processobj)

                if args.provenance and runtime_context.research_obj:
                    # Can't really be combined with args.pack at same time
                    runtime_context.research_obj.packed_workflow(
                        print_pack(loading_context.loader, processobj, uri, metadata)
                    )

                tool = make_tool(uri, loading_context)

            except (validate.ValidationException) as exc:
                _logger.error(
                    "Tool definition failed validation:\n%s", str(exc), exc_info=args.debug
                )
                raise exc
            except (RuntimeError, WorkflowException) as exc:
                _logger.error(
                    "Tool definition failed initialization:\n%s",
                    str(exc),
                    exc_info=args.debug,
                )
                raise exc
            except Exception as exc:
                _logger.error(
                    "I'm sorry, I couldn't load this CWL file%s.\nThe error was: %s",
                    try_again_msg,
                    str(exc) if not args.debug else "",
                    exc_info=args.debug,
                )
                raise exc

            if isinstance(tool, int):
                return tool

            cls._set_runtime_tmp_directories(runtime_context)

            if args.cachedir:
                if args.move_outputs == "move":
                    runtime_context.move_outputs = "copy"
                runtime_context.tmp_outdir_prefix = args.cachedir

            runtime_context.secret_store = getdefault(
                runtime_context.secret_store, SecretStore()
            )
            runtime_context.make_fs_access = getdefault(
                runtime_context.make_fs_access, StdFsAccess
            )

            real_executor = cls._init_job_executor(args, runtime_context)

            try:
                runtime_context.basedir = input_basedir

                if isinstance(tool, ProcessGenerator):
                    tfjob_order = {}  # type: MutableMapping[str, Any]
                    if loading_context.jobdefaults:
                        tfjob_order.update(loading_context.jobdefaults)
                    if job_order_object:
                        tfjob_order.update(job_order_object)
                    tfout, tfstatus = real_executor(
                        tool.embedded_tool, tfjob_order, runtime_context
                    )
                    if tfstatus != "success":
                        raise WorkflowException(
                            "ProcessGenerator failed to generate workflow"
                        )
                    tool, job_order_object = tool.result(tfjob_order, tfout, runtime_context)
                    if not job_order_object:
                        job_order_object = None

                initialized_job_order_object = cls._init_job_order(args, input_basedir, input_required,
                                                                   job_order_object, jobloader, runtime_context, stdout,
                                                                   tool)

                conf_file = getattr(
                    args, "beta_dependency_resolvers_configuration", None
                )  # str
                use_conda_dependencies = getattr(
                    args, "beta_conda_dependencies", None
                )  # str

                if conf_file or use_conda_dependencies:
                    runtime_context.job_script_provider = DependenciesConfiguration(args)
                else:
                    runtime_context.find_default_container = functools.partial(
                        find_default_container,
                        default_container=runtime_context.default_container,
                        use_biocontainers=args.beta_use_biocontainers,
                    )

                (out, status) = real_executor(
                    tool, initialized_job_order_object, runtime_context, logger=_logger
                )
                _logger.info(f'OUT::: {out}')
                if out is not None:
                    if runtime_context.research_obj is not None:
                        runtime_context.research_obj.create_job(out, None, True)

                        def remove_at_id(doc: MutableMapping[str, Any]) -> None:
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

                    def loc_to_path(obj):  # type: (Dict[str, Any]) -> None
                        for field in ("path", "nameext", "nameroot", "dirname"):
                            if field in obj:
                                del obj[field]
                        if obj["location"].startswith("file://"):
                            obj["path"] = uri_file_path(obj["location"])

                    visit_class(out, ("File", "Directory"), loc_to_path)

                    # Unsetting the Generation from final output object
                    visit_class(out, ("File",), MutationManager().unset_generation)

                    if isinstance(out, str):
                        stdout.write(out)
                    else:
                        stdout.write(json_dumps(out, indent=4, ensure_ascii=False))
                    stdout.write("\n")
                    if hasattr(stdout, "flush"):
                        stdout.flush()

                if status != "success":
                    _logger.warning("Final process status is %s", status)
                    raise RuntimeError("Final process status is %s", status)


                _logger.info("Final process status is %s", status)
                return [output_binding['location'] for output_binding in out.values()]

            except (validate.ValidationException) as exc:
                _logger.error(
                    "Input object failed validation:\n%s", str(exc), exc_info=args.debug
                )
                raise exc
            except UnsupportedRequirement as exc:
                _logger.error(
                    "Workflow or tool uses unsupported feature:\n%s",
                    str(exc),
                    exc_info=args.debug,
                )
                raise exc
            except WorkflowException as exc:
                _logger.error(
                    "Workflow error%s:\n%s",
                    try_again_msg,
                    strip_dup_lineno(str(exc)),
                    exc_info=args.debug,
                )
                raise exc
            except Exception as exc:  # pylint: disable=broad-except
                _logger.error(
                    "Unhandled error%s:\n  %s",
                    try_again_msg,
                    str(exc),
                    exc_info=args.debug,
                )
                raise exc

        finally:
            if (
                    args
                    and runtime_context
                    and runtime_context.research_obj
                    and workflowobj
                    and loading_context
            ):
                research_obj = runtime_context.research_obj
                if loading_context.loader is not None:
                    research_obj.generate_snapshot(
                        prov_deps(workflowobj, loading_context.loader, uri)
                    )
                else:
                    _logger.warning(
                        "Unable to generate provenance snapshot "
                        " due to missing loadingContext.loader."
                    )
                if prov_log_handler is not None:
                    # Stop logging so we won't half-log adding ourself to RO
                    _logger.debug(
                        "[provenance] Closing provenance log file %s", prov_log_handler
                    )
                    _logger.removeHandler(prov_log_handler)
                    # Ensure last log lines are written out
                    prov_log_handler.flush()
                    # Underlying WritableBagFile will add the tagfile to the manifest
                    prov_log_handler.stream.close()
                    prov_log_handler.close()
                research_obj.close(args.provenance)

            _logger.removeHandler(stderr_handler)
            _logger.addHandler(defaultStreamHandler)

    @classmethod
    def _init_job_order(cls, args, input_basedir, input_required, job_order_object, jobloader, runtime_context, stdout,
                        tool):
        try:
            initialized_job_order_object = init_job_order(
                job_order_object,
                args,
                tool,
                jobloader,
                stdout,
                print_input_deps=args.print_input_deps,
                relative_deps=args.relative_deps,
                make_fs_access=runtime_context.make_fs_access,
                input_basedir=input_basedir,
                secret_store=runtime_context.secret_store,
                input_required=input_required,
            )
        except SystemExit as err:
            raise RuntimeError("cannot init job order: " + str(err))

        del args.workflow
        del args.job_order
        return initialized_job_order_object

    @classmethod
    def _set_runtime_tmp_directories(cls, runtimeContext):
        # If on MacOS platform, TMPDIR must be set to be under one of the
        # shared volumes in Docker for Mac
        # More info: https://dockstore.org/docs/faq
        if sys.platform == "darwin":
            default_mac_path = "/private/tmp/docker_tmp"
            if runtimeContext.tmp_outdir_prefix == DEFAULT_TMP_PREFIX:
                runtimeContext.tmp_outdir_prefix = default_mac_path
            if runtimeContext.tmpdir_prefix == DEFAULT_TMP_PREFIX:
                runtimeContext.tmpdir_prefix = default_mac_path
        if check_working_directories(runtimeContext) is not None:
            raise RuntimeError("Failed to check working directories for runtime context")

    @classmethod
    def _init_job_executor(cls, args, runtimeContext):
        if args.parallel:
            temp_executor = MultithreadedJobExecutor()
            runtimeContext.select_resources = temp_executor.select_resources
            real_executor = temp_executor  # type: JobExecutor
        else:
            real_executor = SingleJobExecutor()
        return real_executor

    @classmethod
    def _init_runtime_context(cls, argsl, args, runtimeContext):
        runtimeContext = RuntimeContext(vars(args)) if runtimeContext is None else runtimeContext.copy()
        # If on Windows platform, a default Docker Container is used if not
        # explicitely provided by user
        if onWindows() and not runtimeContext.default_container:
            # This docker image is a minimal alpine image with bash installed
            # (size 6 mb). source: https://github.com/frol/docker-alpine-bash
            runtimeContext.default_container = windows_default_container_id

        if args.provenance:
            if argsl is None:
                raise Exception("argsl cannot be None")
            if setup_provenance(args, argsl, runtimeContext) is not None:
                return 1

        return runtimeContext

    @classmethod
    def _parse_cwl_options(cls, argsl):
        if argsl is None:
            argsl = sys.argv[1:]
        addl = []  # type: List[str]
        if "CWLTOOL_OPTIONS" in os.environ:
            addl = os.environ["CWLTOOL_OPTIONS"].split(" ")
        args = arg_parser().parse_args(addl + argsl)
        if args.record_container_id:
            if not args.cidfile_dir:
                args.cidfile_dir = os.getcwd()
            del args.record_container_id

        # If caller parsed its own arguments, it may not include every
        # cwltool option, so fill in defaults to avoid crashing when
        # dereferencing them in args.
        for key, val in get_default_args().items():
            if not hasattr(args, key):
                setattr(args, key, val)

        if args.relax_path_checks:
            command_line_tool.ACCEPTLIST_RE = command_line_tool.ACCEPTLIST_EN_RELAXED_RE

        if args.ga4gh_tool_registries:
            ga4gh_tool_registries[:] = args.ga4gh_tool_registries
        if not args.enable_ga4gh_tool_registry:
            del ga4gh_tool_registries[:]

        return args, argsl

    @classmethod
    def _init_cwl_logger(cls, logger_handler, stderr):
        # _logger.removeHandler(defaultStreamHandler)
        stderr_handler = logger_handler
        if stderr_handler is not None:
            _logger.addHandler(stderr_handler)
        else:
            coloredlogs.install(logger=_logger, stream=stderr)
            stderr_handler = _logger.handlers[-1]
        return stderr_handler

    @classmethod
    def _force_utf8_to_stream(cls, stdout):
        if not stdout:  # force UTF-8 even if the console is configured differently
            if hasattr(sys.stdout, "encoding") and sys.stdout.encoding != "UTF-8":
                if hasattr(sys.stdout, "detach"):
                    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
                else:
                    stdout = getwriter("utf-8")(sys.stdout)  # type: ignore
            else:
                stdout = sys.stdout
        return stdout
