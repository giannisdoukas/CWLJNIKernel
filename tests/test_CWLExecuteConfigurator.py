import unittest
import os
from cwlkernel.CWLExecuteConfigurator import CWLExecuteConfigurator


class TestCWLExecuteConfigurator(unittest.TestCase):
    def test_load_CWLKERNEL_MODE(self):
        conf = CWLExecuteConfigurator()
        self.assertEqual(conf.CWLKERNEL_MODE, 'SIMPLE')

        os.environ['CWLKERNEL_MODE'] = 'simple'
        conf = CWLExecuteConfigurator()
        self.assertEqual(conf.CWLKERNEL_MODE, 'simple')

        os.environ['CWLKERNEL_MODE'] = 'something new'
        self.assertRaises(RuntimeError, CWLExecuteConfigurator)

    def test_load_CWLKERNEL_BOOT_DIRECTORY(self):
        conf = CWLExecuteConfigurator()
        self.assertEqual(conf.CWLKERNEL_BOOT_DIRECTORY, '/tmp/CWLKERNEL_DATA')

        os.environ['CWLKERNEL_BOOT_DIRECTORY'] = '/tmp/CWLKERNEL_DATA1'
        conf = CWLExecuteConfigurator()
        os.environ['CWLKERNEL_BOOT_DIRECTORY'] = '/tmp/CWLKERNEL_DATA'
        self.assertEqual(conf.CWLKERNEL_BOOT_DIRECTORY, '/tmp/CWLKERNEL_DATA1')

    def test_all_properties_have_default_value(self):
        conf = CWLExecuteConfigurator()
        for property in conf.properties:
            self.assertIsNotNone(conf.__getattribute__(property))

    def tearDown(self) -> None:
        try:
            os.environ.pop('CWLKERNEL_MODE')
        except KeyError:
            pass


if __name__ == '__main__':
    unittest.main()
