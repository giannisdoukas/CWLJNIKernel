import os
from collections import namedtuple
from datetime import datetime
from typing import NamedTuple, List, Iterator, Dict

import psutil

from .CWLLoggerStorageManager import CWLLoggerStorageManager

_schema_full_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'loggerSchema.schema.json')


class CWLLogger:

    def __init__(self, root_directory):
        self.process_id = {"process_id": os.getpid(), "parent_process_id": os.getppid()}
        self._storage_manager = CWLLoggerStorageManager(root_directory)
        self._last_to_dict = None

    @classmethod
    def collect_infrastructure_metrics(cls) -> NamedTuple:
        cpu_metrics = psutil.cpu_times()
        vmemory_metrics = psutil.virtual_memory()
        disk_partitions = psutil.disk_partitions()
        disk_usage = [
            (partition.device, psutil.disk_usage(partition.mountpoint))
            for partition in disk_partitions
        ]

        Metrics = namedtuple(
            'Metrics',
            [
                'cpu_metrics',
                'vmemory_metrics',
                'disk_partition',
                'disk_usage'
            ]
        )
        return Metrics(cpu_metrics, vmemory_metrics, disk_partitions, disk_usage)

    @classmethod
    def get_hostname(cls) -> str:
        import socket
        return socket.gethostname()

    def to_dict(self):
        self._last_to_dict = datetime.utcnow().strftime('%Y%b%d%H%M%f')
        metrics = self.collect_infrastructure_metrics()._asdict()
        for key in ['cpu_metrics', 'vmemory_metrics']:
            metrics[key] = {**metrics[key]._asdict()}
        for key in ['disk_partition']:
            metrics[key] = [{**m._asdict()} for m in metrics[key]]
        for key in ['disk_usage']:
            metrics[key] = [{m[0]: {**m[1]._asdict()}} for m in metrics[key]]
        hostname = self.get_hostname()
        return {**metrics, 'hostname': hostname, "process_id": self.process_id, 'timestamp': self._last_to_dict}

    @classmethod
    def get_running_kernels(cls) -> List[int]:
        """
        :return: A list with the process ids of running kernels
        """
        pids = []
        for process in psutil.process_iter():
            try:
                cmdline = process.cmdline()
                if cmdline[1] == '-m' and cmdline[2] == "cwlkernel":
                    pids.append(process.pid)
            except (psutil.AccessDenied, IndexError, psutil.ZombieProcess):
                continue
        return pids

    def save(self):
        return self._storage_manager.save(self.to_dict())

    # def validate(self):
    #     with open(_schema_full_path) as f:
    #         schema = json.load(f)
    #     jsonschema.validate(self.to_dict(), schema)
    #     return self

    # @classmethod
    # def validate_dictionary(cls, dict_log):
    #     with open(_schema_full_path) as f:
    #         schema = json.load(f)
    #     try:
    #         jsonschema.validate(dict_log, schema)
    #         return True
    #     except jsonschema.ValidationError:
    #         return False

    def load(self, limit=None) -> Iterator[Dict]:
        return self._storage_manager.load(limit)
