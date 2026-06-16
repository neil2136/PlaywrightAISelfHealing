from definition.settings import *


class TestConfigPC2(Test):
    uuid = 'NonTC'
    description = 'Initialize PC2 testbed'
    goto_teardown = True

    def test_00_setup_ssh_key(self):
        # 1. Generate SSH key pair (if not exists)
        PC1_LOGIN.send_command('[ -f ~/.ssh/id_rsa ] || ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa -q')
       
        # 2. Read public key content
        pubkey_output = PC1_LOGIN.send_command('cat ~/.ssh/id_rsa.pub')
        pubkey = pubkey_output.strip()
        logger.info(f'Public key: {pubkey}')
       
        # 3. Add public key to PC2 (using existing PC2 connection)
        PC2_LOGIN.send_command('mkdir -p ~/.ssh')
        PC2_LOGIN.send_command('chmod 700 ~/.ssh')
        PC2_LOGIN.send_command(f'echo "{pubkey}" >> ~/.ssh/authorized_keys')
        PC2_LOGIN.send_command('chmod 600 ~/.ssh/authorized_keys')
 
        # 4. Test passwordless SSH login
        out = PC1_LOGIN.send_command(f'ssh -o StrictHostKeyChecking=no root@{PC2_ETH0_IP} "echo completed SSH key setup"')
        logger.info(f'test output: {out}')
        Assertion.assert_regular(out, "completed SSH key setup", "ERR: SSH key setup failed!")

    def test_01_initialize_pytest_bin_script(self):
        logger.info('Copy pytest bin files ......')
        PC2_LOGIN.send_command(f"mkdir -p {CaseParam.testbed_path}")
        PC2_LOGIN.send_command(f"cp -rf {BIN_PATH}/* {CaseParam.testbed_path}")
        logger.info('Check copy result ......')
        out = PC2_LOGIN.send_command(f"ls {CaseParam.testbed_path}")
        logger.info('Check "test" in output ......')
        rc = 'tests' in out
        Assertion.assert_equal(rc, True, "ERR: Copy test script failed!")
    
    def test_02_copy_client_ssl_script(self):
        logger.info('Copy test Client SSL script files ......')
        tests_path = CaseParam.testbed_path + '/tests'
        PC2_LOGIN.send_command(f"cp -rf {SCRIPT_PATH}/128_DPI_SSL_CLIENT_SSL/* {tests_path}")
        logger.info('Check copy result ......')
        out = PC2_LOGIN.send_command(f"ls {tests_path}")
        logger.info('Check "client_ssl" in output ......')
        rc = 'client_ssl' in out
        Assertion.assert_equal(rc, True, "ERR: Copy Client SSL script failed!")
