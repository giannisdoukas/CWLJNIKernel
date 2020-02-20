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
from uuid import uuid4

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

    def execute(self) -> Tuple[StringIO, StringIO, Optional[Exception]]:
        args = [self._workflow_path, *self._data_paths]
        stdout = StringIO()
        stderr = StringIO()

        if self._cwltool_main(argsl=args, stderr=stderr, stdout=stdout) != 0:
            return stdout, stderr, RuntimeError('On Kernel Exception: Error on executing workflow')
        return stdout, stderr, None

    @classmethod
    def _cwltool_main(cls,
                      argsl: Optional[List[str]] = None,
                      args: Optional[argparse.Namespace] = None,
                      stdin: IO[Any] = sys.stdin,
                      stdout: Optional[Union[TextIO, StreamWriter]] = None,
                      stderr: IO[Any] = sys.stderr,
                      versionfunc: Callable[[], str] = versionstring,
                      logger_handler: Optional[logging.Handler] = None,
                      custom_schema_callback: Optional[Callable[[], None]] = None,
                      executor: Optional[JobExecutor] = None,
                      loadingContext: Optional[LoadingContext] = None,
                      runtimeContext: Optional[RuntimeContext] = None,
                      input_required: bool = True,
                      ) -> int:

        if not stdout:  # force UTF-8 even if the console is configured differently
            if hasattr(sys.stdout, "encoding") and sys.stdout.encoding != "UTF-8":
                if hasattr(sys.stdout, "detach"):
                    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
                else:
                    stdout = getwriter("utf-8")(sys.stdout)  # type: ignore
            else:
                stdout = sys.stdout

        _logger.removeHandler(defaultStreamHandler)
        stderr_handler = logger_handler
        if stderr_handler is not None:
            _logger.addHandler(stderr_handler)
        else:
            coloredlogs.install(logger=_logger, stream=stderr)
            stderr_handler = _logger.handlers[-1]
        workflowobj = None
        prov_log_handler = None  # type: Optional[logging.StreamHandler]
        try:
            if args is None:
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

            if runtimeContext is None:
                runtimeContext = RuntimeContext(vars(args))
            else:
                runtimeContext = runtimeContext.copy()

            # If on Windows platform, a default Docker Container is used if not
            # explicitely provided by user
            if onWindows() and not runtimeContext.default_container:
                # This docker image is a minimal alpine image with bash installed
                # (size 6 mb). source: https://github.com/frol/docker-alpine-bash
                runtimeContext.default_container = windows_default_container_id

            # If caller parsed its own arguments, it may not include every
            # cwltool option, so fill in defaults to avoid crashing when
            # dereferencing them in args.
            for key, val in get_default_args().items():
                if not hasattr(args, key):
                    setattr(args, key, val)

            configure_logging(args, stderr_handler, runtimeContext)

            if args.version:
                print(versionfunc())
                return 0
            _logger.info(versionfunc())

            if args.print_supported_versions:
                print("\n".join(supported_cwl_versions(args.enable_dev)))
                return 0

            if not args.workflow:
                if os.path.isfile("CWLFile"):
                    setattr(args, "workflow", "CWLFile")
                else:
                    _logger.error("CWL document required, no input file was provided")
                    arg_parser().print_help()
                    return 1
            if args.relax_path_checks:
                command_line_tool.ACCEPTLIST_RE = command_line_tool.ACCEPTLIST_EN_RELAXED_RE

            if args.ga4gh_tool_registries:
                ga4gh_tool_registries[:] = args.ga4gh_tool_registries
            if not args.enable_ga4gh_tool_registry:
                del ga4gh_tool_registries[:]

            setup_schema(args, custom_schema_callback)

            if args.provenance:
                if argsl is None:
                    raise Exception("argsl cannot be None")
                if setup_provenance(args, argsl, runtimeContext) is not None:
                    return 1

            loadingContext = setup_loadingContext(loadingContext, runtimeContext, args)

            uri, tool_file_uri = resolve_tool_uri(
                args.workflow,
                resolver=loadingContext.resolver,
                fetcher_constructor=loadingContext.fetcher_constructor,
            )

            try_again_msg = (
                "" if args.debug else ", try again with --debug for more information"
            )

            try:
                job_order_object, input_basedir, jobloader = load_job_order(
                    args,
                    stdin,
                    loadingContext.fetcher_constructor,
                    loadingContext.overrides_list,
                    tool_file_uri,
                )

                if args.overrides:
                    loadingContext.overrides_list.extend(
                        load_overrides(
                            file_uri(os.path.abspath(args.overrides)), tool_file_uri
                        )
                    )

                loadingContext, workflowobj, uri = fetch_document(uri, loadingContext)

                if args.print_deps and loadingContext.loader:
                    printdeps(
                        workflowobj, loadingContext.loader, stdout, args.relative_deps, uri
                    )
                    return 0

                loadingContext, uri = resolve_and_validate_document(
                    loadingContext,
                    workflowobj,
                    uri,
                    preprocess_only=(args.print_pre or args.pack),
                    skip_schemas=args.skip_schemas,
                )

                if loadingContext.loader is None:
                    raise Exception("Impossible code path.")
                processobj, metadata = loadingContext.loader.resolve_ref(uri)
                processobj = cast(CommentedMap, processobj)
                if args.pack:
                    stdout.write(
                        print_pack(loadingContext.loader, processobj, uri, metadata)
                    )
                    return 0

                if args.provenance and runtimeContext.research_obj:
                    # Can't really be combined with args.pack at same time
                    runtimeContext.research_obj.packed_workflow(
                        print_pack(loadingContext.loader, processobj, uri, metadata)
                    )

                if args.print_pre:
                    stdout.write(
                        json_dumps(
                            processobj, indent=4, sort_keys=True, separators=(",", ": ")
                        )
                    )
                    return 0

                tool = make_tool(uri, loadingContext)
                if args.make_template:
                    make_template(tool)
                    return 0

                if args.validate:
                    print("{} is valid CWL.".format(args.workflow))
                    return 0

                if args.print_rdf:
                    stdout.write(
                        printrdf(tool, loadingContext.loader.ctx, args.rdf_serializer)
                    )
                    return 0

                if args.print_dot:
                    printdot(tool, loadingContext.loader.ctx, stdout)
                    return 0

                if args.print_targets:
                    for f in ("outputs", "steps", "inputs"):
                        if tool.tool[f]:
                            _logger.info("%s%s targets:", f[0].upper(), f[1:-1])
                            stdout.write(
                                "  "
                                + "\n  ".join([shortname(t["id"]) for t in tool.tool[f]])
                                + "\n"
                            )
                    return 0

                if args.target:
                    ctool = choose_target(args, tool, loadingContext)
                    if ctool is None:
                        return 1
                    else:
                        tool = ctool

                if args.print_subgraph:
                    if "name" in tool.tool:
                        del tool.tool["name"]
                    stdout.write(
                        json_dumps(
                            tool.tool, indent=4, sort_keys=True, separators=(",", ": ")
                        )
                    )
                    return 0

            except (validate.ValidationException) as exc:
                _logger.error(
                    "Tool definition failed validation:\n%s", str(exc), exc_info=args.debug
                )
                return 1
            except (RuntimeError, WorkflowException) as exc:
                _logger.error(
                    "Tool definition failed initialization:\n%s",
                    str(exc),
                    exc_info=args.debug,
                )
                return 1
            except Exception as exc:
                _logger.error(
                    "I'm sorry, I couldn't load this CWL file%s.\nThe error was: %s",
                    try_again_msg,
                    str(exc) if not args.debug else "",
                    exc_info=args.debug,
                )
                return 1

            if isinstance(tool, int):
                return tool

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
                return 1

            if args.cachedir:
                if args.move_outputs == "move":
                    runtimeContext.move_outputs = "copy"
                runtimeContext.tmp_outdir_prefix = args.cachedir

            runtimeContext.secret_store = getdefault(
                runtimeContext.secret_store, SecretStore()
            )
            runtimeContext.make_fs_access = getdefault(
                runtimeContext.make_fs_access, StdFsAccess
            )

            if not executor:
                if args.parallel:
                    temp_executor = MultithreadedJobExecutor()
                    runtimeContext.select_resources = temp_executor.select_resources
                    real_executor = temp_executor  # type: JobExecutor
                else:
                    real_executor = SingleJobExecutor()
            else:
                real_executor = executor

            try:
                runtimeContext.basedir = input_basedir

                if isinstance(tool, ProcessGenerator):
                    tfjob_order = {}  # type: MutableMapping[str, Any]
                    if loadingContext.jobdefaults:
                        tfjob_order.update(loadingContext.jobdefaults)
                    if job_order_object:
                        tfjob_order.update(job_order_object)
                    tfout, tfstatus = real_executor(
                        tool.embedded_tool, tfjob_order, runtimeContext
                    )
                    if tfstatus != "success":
                        raise WorkflowException(
                            "ProcessGenerator failed to generate workflow"
                        )
                    tool, job_order_object = tool.result(tfjob_order, tfout, runtimeContext)
                    if not job_order_object:
                        job_order_object = None

                try:
                    initialized_job_order_object = init_job_order(
                        job_order_object,
                        args,
                        tool,
                        jobloader,
                        stdout,
                        print_input_deps=args.print_input_deps,
                        relative_deps=args.relative_deps,
                        make_fs_access=runtimeContext.make_fs_access,
                        input_basedir=input_basedir,
                        secret_store=runtimeContext.secret_store,
                        input_required=input_required,
                    )
                except SystemExit as err:
                    return err.code

                del args.workflow
                del args.job_order

                conf_file = getattr(
                    args, "beta_dependency_resolvers_configuration", None
                )  # str
                use_conda_dependencies = getattr(
                    args, "beta_conda_dependencies", None
                )  # str

                if conf_file or use_conda_dependencies:
                    runtimeContext.job_script_provider = DependenciesConfiguration(args)
                else:
                    runtimeContext.find_default_container = functools.partial(
                        find_default_container,
                        default_container=runtimeContext.default_container,
                        use_biocontainers=args.beta_use_biocontainers,
                    )

                (out, status) = real_executor(
                    tool, initialized_job_order_object, runtimeContext, logger=_logger
                )

                if out is not None:
                    if runtimeContext.research_obj is not None:
                        runtimeContext.research_obj.create_job(out, None, True)

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
                            functools.partial(add_sizes, runtimeContext.make_fs_access("")),
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
                    return 1
                _logger.info("Final process status is %s", status)
                return 0

            except (validate.ValidationException) as exc:
                _logger.error(
                    "Input object failed validation:\n%s", str(exc), exc_info=args.debug
                )
                return 1
            except UnsupportedRequirement as exc:
                _logger.error(
                    "Workflow or tool uses unsupported feature:\n%s",
                    str(exc),
                    exc_info=args.debug,
                )
                return 33
            except WorkflowException as exc:
                _logger.error(
                    "Workflow error%s:\n%s",
                    try_again_msg,
                    strip_dup_lineno(str(exc)),
                    exc_info=args.debug,
                )
                return 1
            except Exception as exc:  # pylint: disable=broad-except
                _logger.error(
                    "Unhandled error%s:\n  %s",
                    try_again_msg,
                    str(exc),
                    exc_info=args.debug,
                )
                return 1

        finally:
            if (
                    args
                    and runtimeContext
                    and runtimeContext.research_obj
                    and workflowobj
                    and loadingContext
            ):
                research_obj = runtimeContext.research_obj
                if loadingContext.loader is not None:
                    research_obj.generate_snapshot(
                        prov_deps(workflowobj, loadingContext.loader, uri)
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
