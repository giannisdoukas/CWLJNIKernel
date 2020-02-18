import unittest

from cwlkernel.CWLLogger import CWLLogger


class CWLLoggerTests(unittest.TestCase):
    def test_get_infrastructure_metrics(self):
        logger = CWLLogger()
        metrics = logger.collect_infrastructure_metrics()
        self.assertIsNotNone(metrics.cpu_metrics)
        self.assertIsNotNone(metrics.vmemory_metrics)
        self.assertIsNotNone(metrics.disk_partition)
        self.assertIsNotNone(metrics.disk_usage)
