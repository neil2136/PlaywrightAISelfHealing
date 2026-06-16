# __Author__ = 'xzhan'
import sys
import os
import unittest
from runner.unittest.suite import UnittestSuite

sys.path.append(os.environ["PYTHON_SONICOS_HOME"] + '/UI_Playwright/128_DPI_SSL_CLIENT_SSL/')
sys.path.append(os.environ["PYTHON_COMMON_HOME"])


def suite():
    testcases_list = [
        'config.init_testbed.TestRestoreDUT',
        'config.init_testbed.TestUploadFirmware',
        'definition.init_fw_configure',
        'definition.init_pc_configure',
        'testcases.Run_ui_script',
        'testcases.128_DPI_SSL_CLIENT_SSL',
    ]
    suites = unittest.TestLoader().loadTestsFromNames(testcases_list)
    return suites


if __name__ == '__main__':
    st = UnittestSuite(sys.argv, suite())
    st.run()
