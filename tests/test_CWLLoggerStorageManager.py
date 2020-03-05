import json
import os
import tempfile
import unittest

from cwlkernel.CWLLogger import CWLLogger
from cwlkernel.CWLLoggerStorageManager import CWLLoggerStorageManager


class TestCWLLoggerStorageManager(unittest.TestCase):

    maxDiff = None

    def test_load(self):
        storage_path = tempfile.mkdtemp()
        logger_storage = CWLLoggerStorageManager(storage_path)
        cwllogger = CWLLogger(tempfile.mkdtemp())
        data = cwllogger.to_dict()
        custom_log_fn = os.path.join(storage_path, 'dummy_log_data.kcwl.json')
        with open(custom_log_fn, 'w') as f:
            json.dump(data, f, indent=2)

        loaded_logs = list(logger_storage.load())
        self.assertListEqual([data], loaded_logs)

        custom_log_fn2 = os.path.join(storage_path, 'dummy_log_data2.kcwl.json')
        with open(custom_log_fn2, 'w') as f:
            data2 = cwllogger.to_dict()
            json.dump(data2, f, indent=2)
        # results are order with modification time so it must be inside
        loaded_logs = list(logger_storage.load())
        d = [data2, data]
        self.assertListEqual(
            d, loaded_logs,
            f'Results are not the same: ---------\n{json.dumps(d, indent=2)}\n-------\n{json.dumps(loaded_logs, indent=2)}'
        )

        custom_log_fn3 = os.path.join(storage_path, 'dummy_log_data3.kcwl.json')
        with open(custom_log_fn3, 'w') as f:
            data3 = CWLLogger(tempfile.mkdtemp()).to_dict()
            json.dump(data3, f, indent=2)
        # results are order with modification time so it must be inside
        loaded_logs = list(logger_storage.load(2))
        self.assertListEqual([data3, data2], loaded_logs)

    def test_save(self):
        import jsonschema
        schema_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..',
            'cwlkernel',
            'loggerSchema.schema.json'
        )
        with open(schema_path) as f:
            schema = json.load(f)

        storage_path = tempfile.mkdtemp()
        logger_storage_manager = CWLLoggerStorageManager(storage_path)

        new_file = logger_storage_manager.save(CWLLogger(storage_path).to_dict())

        self.assertTrue(os.path.isfile(new_file))
        log_data = list(logger_storage_manager.load(1))[0]
        jsonschema.validate(log_data, schema)


if __name__ == '__main__':
    unittest.main()
