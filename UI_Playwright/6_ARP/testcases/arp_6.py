from definition.settings import *


@paramunittest.parametrized(
    {"uuid": "SOSAIOT-TC-ARP-01", "jira": ""},
    {"uuid": "SOSAIOT-TC-ARP-02", "jira": ""},
    {"uuid": "SOSAIOT-TC-ARP-03", "jira": ""},
    {"uuid": "SOSAIOT-TC-ARP-04", "jira": ""},
    {"uuid": "SOSAIOT-TC-ARP-05", "jira": ""},
    {"uuid": "SOSAIOT-TC-ARP-06", "jira": ""},
)
class Test_check_ui_arp_result(Test):

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
