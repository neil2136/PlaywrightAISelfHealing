from math import log
import os
import sys
import re
import time
import copy
import requests
import unittest
import json
import csv
import paramunittest
from runner.settings import Params, logger
from runner.unittest.setup import Test, skip_if_dts, repeat_method
from runner.utils.assertion import Assertion
from runner.unittest.suite import UnittestSuite
from contextvars import ContextVar

# import contents from common_lib path
sys.path.append(os.environ["PYTHON_COMMON_HOME"])
sys.path.append(os.environ["PYTHON_SONICOS_HOME"])
from util.enhancedinfo import show_testcase_info
from utm import Firewall, G_PASSWORD_NEW
from networkdevice import Host
from util.openstack import Openstack



# import form branch lib contents for test suit
# sys.path.append(os.environ["PYTHON_SONICOS_HOME"])
from lib.modules.API.network import InterfaceIPv4Api
from lib.modules.API.system import AdminApi, StatusApi, SettingApi
from lib.modules.API.log import LogSettingsApi, LogMonitorApi
from lib.modules.API.users import UsersettingApi
from lib.modules.CLI.system import LicenseCli


# import from test suite root path like definition
playwright_path = os.environ["PYTHON_SONICOS_HOME"] + '/UI_Playwright/'
suite_path = playwright_path + '112_Network_Interfaces/'
sys.path.append(suite_path)
sys.path.append(suite_path + 'testcases')
TESTPLAN = suite_path + 'testplan/network_interfaces_112.json'
SCRIPT_PATH = suite_path + 'definition/script'
BIN_PATH = playwright_path + 'bin'

# Instantiate objects including common_lib import
OpenS = Openstack(Params.testbed)
PC1_ETH0_IP = OpenS.get_node_interface_ip('PC1', 'eth0')
PC1_ETH1_IP = OpenS.get_node_interface_ip('PC1', 'eth1')
PC2_ETH0_IP = OpenS.get_node_interface_ip('PC2', 'eth0')
PC2_ETH1_IP = OpenS.get_node_interface_ip('PC2', 'eth1')
logger.info(f'\n PC1_ETH0_IP: {PC1_ETH0_IP}'
            f'\n PC1_ETH1_IP: {PC1_ETH1_IP}'
            f'\n PC2_ETH0_IP: {PC2_ETH0_IP}'
            f'\n PC2_ETH1_IP: {PC2_ETH1_IP}'
            )
PC1_LOGIN = Host(PC1_ETH0_IP)
PC2_LOGIN = Host(PC2_ETH0_IP)

# parameters on the fw
class Parameter:
    FIREWALL = '192.168.168.168'
    X0_SUBNET = '192.168.168.0'
    X1_IP = '12.12.1.168'
    X1_GW = '12.12.1.1'
    X1_DNS1 = Params.G_DNS1
    X1_DNS2 = Params.G_DNS2
    # MASK = '255.255.255.0'
    # X2_IP = '12.12.1.168'
    # X2_GW = '12.12.1.1'
    # X2_DNS1 = Params.G_DNS1
    # X2_DNS2 = Params.G_DNS2
    MASK = '255.255.255.0'


# parameters used by suite cases
class CaseParam:
    testbed_path = "/tmp/UI_Playwright"
    csv_filename = "Recorder.csv"
    log_filename = "test_result.log"
    result_dict = {}
    err_case = []
    logs = ''


# Instantiate objects including API,CLI import
fw = Firewall(
            Parameter.FIREWALL,
            user='admin',
            password='password',
            supported_config_mode='api')
fw_cli = Firewall(
            Parameter.FIREWALL,
            user='admin',
            password='password',
            supported_config_mode='cli-ssh')

license_cli = LicenseCli(fw_cli)
admin_api = AdminApi(fw)
user_api = UsersettingApi(fw)
interface_api = InterfaceIPv4Api(fw)
status_api = StatusApi(fw)
log_set_api = LogSettingsApi(fw)
log_monitor_api = LogMonitorApi(fw)
setting_api = SettingApi(fw)

