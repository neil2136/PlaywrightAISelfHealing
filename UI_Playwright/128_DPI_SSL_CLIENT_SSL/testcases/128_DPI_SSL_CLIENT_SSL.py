from definition.settings import *

@paramunittest.parametrized(
    {"uuid": "SOSAIOT-TC-95316", "jira": ""},
    {"uuid": "SOSAIOT-TC-95317", "jira": ""},
    {"uuid": "SOSAIOT-TC-95318", "jira": ""},
    {"uuid": "SOSAIOT-TC-95319", "jira": ""},
    {"uuid": "SOSAIOT-TC-95320", "jira": ""},
    {"uuid": "SOSAIOT-TC-95321", "jira": ""},
    {"uuid": "SOSAIOT-TC-95322", "jira": ""},
    {"uuid": "SOSAIOT-TC-95323", "jira": ""},
    {"uuid": "SOSAIOT-TC-95324", "jira": ""},
    {"uuid": "SOSAIOT-TC-95325", "jira": ""},
    {"uuid": "SOSAIOT-TC-95326", "jira": ""},
    {"uuid": "SOSAIOT-TC-95327", "jira": ""},
    {"uuid": "SOSAIOT-TC-95328", "jira": ""},
    {"uuid": "SOSAIOT-TC-95329", "jira": ""},
    {"uuid": "SOSAIOT-TC-95330", "jira": ""},
    {"uuid": "SOSAIOT-TC-95331", "jira": ""},
    {"uuid": "SOSAIOT-TC-95332", "jira": ""},
    {"uuid": "SOSAIOT-TC-95333", "jira": ""},
)
class Test_Check_Result(Test):

    def setParameters(self, uuid, jira):
        self.uuid = uuid
        self.description = show_testcase_info(TESTPLAN, self.uuid, description=True)['title']
        self.jira = jira

    def test_00_show_testcase_info(self):
        show_testcase_info(TESTPLAN, self.uuid)
        Assertion.assert_equal(True, True, "ERR: show test case info failed")

    def test_01_check_result(self):
        logger.info('Test Logs:')
        test_log = re.search(rf'Test case {self.uuid} START.*Test case {self.uuid} END', CaseParam.logs, re.S)
        test_log = test_log.group() if test_log else None
        logger.info(test_log)
        
        rc_dict = CaseParam.result_dict.get(self.uuid)
        rc = rc_dict.get('status') if rc_dict else 'skipped'
        if rc == 'failed':
            logger.error(rc_dict.get('error_message')) 
        Assertion.assert_regular(rc, 'passed', "ERR: Check result failed! ")