from collections import namedtuple
from typing import NamedTuple

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
        hostname = cls.get_hostname()
        return {**metrics, 'hostname': hostname}