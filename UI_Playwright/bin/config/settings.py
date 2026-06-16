# config/settings.py - Configuration Management
import os
import re
import csv
import pytest
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Settings:
    """Global Settings"""

    # Project Info
    PROJECT_NAME = "Playwright Automation Test Framework"
    VERSION = "1.0.0"
    AUTHOR = "xzhan"

    # Root Directory
    ROOT_DIR = project_root

    # Directories
    LOGS_DIR = ROOT_DIR / "logs"
    REPORTS_DIR = ROOT_DIR / "reports"
    SCREENSHOTS_DIR = ROOT_DIR / "screenshots"
    TEST_DATA_DIR = ROOT_DIR / "test_data"
    CONFIG_DIR = ROOT_DIR / "config"

    # Test Settings
    FIREWALL_IP = "192.168.168.168"
    BASE_URL = f"https://{FIREWALL_IP}/sonicui/7"
    USERNAME = 'admin'
    PASSWORD = 'S0nic@uto'
    DEFAULT_TIMEOUT = "30"
    LOG_FILE_NAME = "test_result.log"
    CSV_FILE_NAME = "Recorder.csv"
    Initialize_LOG = False

    # browser configurations
    BROWSERS = {
        "chromium": {
            "channel": "chrome",
            "headless": True,
            "slow_mo": 0,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"]
        }
    }

    @classmethod
    def setup_directories(cls):
        """Create necessary directories if they don't exist"""
        directories = [
            cls.LOGS_DIR,
            cls.REPORTS_DIR,
            cls.SCREENSHOTS_DIR,
            cls.TEST_DATA_DIR
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Initialize directories on module load
Settings.setup_directories()
