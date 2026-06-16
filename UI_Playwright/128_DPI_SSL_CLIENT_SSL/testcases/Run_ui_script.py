from definition.settings import *

class TestUI_Playwright(Test):
    uuid = 'NonTC'
    description = 'Run GUI AO script and get result'
    goto_teardown = True

    def test_01_start_ui_script(self):
        runner = f'{CaseParam.testbed_path}/run_tests.py'
        out = PC2_LOGIN.send_command(f'python3 {runner} --password {G_PASSWORD_NEW}')
        Assertion.assert_regular(out, 'Start time', "ERR: Start AO script failed!")

    def test_02_read_result_csv(self):
        # PC2_LOGIN.send_command(f'cp -rf {CaseParam.testbed_path}/reports/{CaseParam.csv_filename} {SCRIPT_PATH}')
        report_path = f'{CaseParam.testbed_path}/reports/{CaseParam.csv_filename}'
        PC1_LOGIN.send_command(f'scp -r root@{PC2_ETH0_IP}:{report_path} /tmp/')
        with open(f'/tmp/{CaseParam.csv_filename}', encoding='utf-8', newline='') as f:
            rd = csv.reader(f)
            for row in rd:
                logger.info(row)
                CaseParam.result_dict.update({row[0]: {'status': row[1], 'error_message': row[2]}})
        Assertion.assert_equal(bool(CaseParam.result_dict), True, "ERR: Read result csv failed!")

    def test_03_record_all_logs(self):
        log = f'{CaseParam.testbed_path}/logs/{CaseParam.log_filename}'
        out = PC2_LOGIN.send_command(f'cat {log}')
        rc = 'Test session started' in out
        CaseParam.logs = out
        logger.info(CaseParam.logs)
        Assertion.assert_equal(rc, True, "ERR: display all logs failed!")