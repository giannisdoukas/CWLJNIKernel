import json
import os
import tempfile
import unittest
from cwlkernel.CWLLoggerStorageManager import CWLLoggerStorageManager
from cwlkernel.CWLLogger import CWLLogger

class TestCWLLoggerStorageManager(unittest.TestCase):

    def test_load(self):
        storage_path = tempfile.mkdtemp()
        logger_storage = CWLLoggerStorageManager(storage_path)
        data = CWLLogger.to_dict()
        custom_log_fn = os.path.join(storage_path, 'dummy_log_data.kcwl.json')
        with open(custom_log_fn, 'w') as f:
            json.dump(data, f, indent=2)

        loaded_logs = list(logger_storage.load())
        self.assertListEqual([data], loaded_logs)

        custom_log_fn2 = os.path.join(storage_path, 'dummy_log_data2.kcwl.json')
        with open(custom_log_fn2, 'w') as f:
            data2 = CWLLogger.to_dict()
            json.dump(data2, f, indent=2)
        # results are order with modification time so it must be inside
        loaded_logs = list(logger_storage.load())
        self.assertListEqual([data2, data], loaded_logs)

        custom_log_fn3 = os.path.join(storage_path, 'dummy_log_data3.kcwl.json')
        with open(custom_log_fn3, 'w') as f:
            data3 = CWLLogger.to_dict()
            json.dump(data3, f, indent=2)
        # results are order with modification time so it must be inside
        loaded_logs = list(logger_storage.load(2))
        self.assertListEqual([data3, data2], loaded_logs)


    def test_save(self):
        raise NotImplementedError()


if __name__ == '__main__':
    unittest.main()
