import json
import os
import socket
import unittest
import tempfile
from cwlkernel.CWLLogger import CWLLogger


class TestCWLLogger(unittest.TestCase):

    tmp_dir = tempfile.mkdtemp()
    maxDiff = None

    def test_get_infrastructure_metrics(self):
        logger = CWLLogger(self.tmp_dir)
        metrics = logger.collect_infrastructure_metrics()
        self.assertIsNotNone(metrics.cpu_metrics)
        self.assertIsNotNone(metrics.vmemory_metrics)
        self.assertIsNotNone(metrics.disk_partition)
        self.assertIsNotNone(metrics.disk_usage)

    def test_get_hostname(self):
        logger = CWLLogger(self.tmp_dir)
        hostname = logger.get_hostname()
        self.assertEqual(hostname, socket.gethostname())
        self.assertTrue(len(hostname) > 0)
        self.assertIsInstance(hostname, str)

    def test_to_dict(self):
        logger = CWLLogger(self.tmp_dir)
        dict_log = logger.to_dict()
        import jsonschema
        schema_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..',
            'cwlkernel',
            'loggerSchema.schema.json'
        )
        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(dict_log, schema)

    def test_get_running_kernels(self):
        import subprocess
        kernel = subprocess.Popen(["python", "-m", "cwlkernel"])
        pids = []
        try:
            pids = CWLLogger.get_running_kernels()
        except Exception:
            pass
        finally:
            kernel.kill()
        self.assertIn(kernel.pid, pids)

    def test_get_logs_from_past_kernels(self):
        new_dir = tempfile.mkdtemp()
        logger = CWLLogger(new_dir)
        logger.save()
        self.assertListEqual(
            [logger.to_dict()['process_id']],
            [l['process_id'] for l in logger.load()]
        )