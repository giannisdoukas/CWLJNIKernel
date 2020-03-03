from collections import namedtuple
from typing import NamedTuple, List

import psutil


class CWLLogger:

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

    @classmethod
    def to_dict(cls):
        metrics = cls .collect_infrastructure_metrics()._asdict()
        for key in ['cpu_metrics', 'vmemory_metrics']:
            metrics[key] = {**metrics[key]._asdict()}
        for key in ['disk_partition']:
            metrics[key] = [{**m._asdict()} for m in metrics[key]]
        for key in ['disk_usage']:
            metrics[key] = [{m[0]: {**m[1]._asdict()}} for m in metrics[key]]
        hostname = cls.get_hostname()
        return {**metrics, 'hostname': hostname}

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
