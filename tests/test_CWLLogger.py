import json
import os
import unittest
import socket
from cwlkernel.CWLLogger import CWLLogger


class TestCWLLogger(unittest.TestCase):
    def test_get_infrastructure_metrics(self):
        logger = CWLLogger()
        metrics = logger.collect_infrastructure_metrics()
        self.assertIsNotNone(metrics.cpu_metrics)
        self.assertIsNotNone(metrics.vmemory_metrics)
        self.assertIsNotNone(metrics.disk_partition)
        self.assertIsNotNone(metrics.disk_usage)

    def test_get_hostname(self):
        logger = CWLLogger()
        hostname = logger.get_hostname()
        self.assertEqual(hostname, socket.gethostname())
        self.assertTrue(len(hostname) > 0)
        self.assertIsInstance(hostname, str)

    def test_to_dict(self):
        logger = CWLLogger()
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
