#!/usr/bin/env python3
# run_test.py - Run Playwright Automation Test Entrance
import argparse
import subprocess
import shutil
from colorama import init, Fore, Style
from config.settings import Settings, datetime, sys
from config.logger import get_logger

# Initialize colorama
init(autoreset=True)

logger = get_logger("runner")


def print_banner():
    """Print Start banner information"""
    banner = f"""
    {Fore.CYAN}{'='*60}
    {Fore.YELLOW} Playwright Automation Test Framework
    {Fore.CYAN}{'='*60}
    {Fore.GREEN}Project Root Directory: {Settings.ROOT_DIR}
    {Fore.GREEN}Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    {Fore.CYAN}{'='*60}{Style.RESET_ALL}
    """
    print(banner)


def parse_arguments():
    """Analyze command-line arguments"""
    parser = argparse.ArgumentParser(description='Run Playwright Automation Test ')

    # Test Running options
    parser.add_argument('--tests', '-t', nargs='+',
                        help='specify test files or directories to run')
    parser.add_argument('--mark', '-m',
                        help='run tests with the specified mark (example: auto_login)')
    parser.add_argument('--keyword', '-k',
                        help='run tests that match the given keyword expression')

    # Environment configuration
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit', 'all'],
                        default='chromium',
                        help='Browser type (Default: chromium)')
    parser.add_argument('--headed', action='store_true',
                        help='Use headed mode (with UI)')
    parser.add_argument('--slowmo', type=int, default=0,
                        help='Options to slow down Playwright actions (ms), for debug (Default: 0)')
    parser.add_argument('--retries', type=int, default=1,
                        help='Retry failed tests times (Default: 1)')
    parser.add_argument('--timeout', type=int, default=30,
                        help='Timeout for each test (s) (Default: 30)')
    parser.add_argument('--password', default='password2',
                        help='password for login (Default: S0nic@uto)')
    parser.add_argument('--fw_ip', default='192.168.168.168',
                        help='firewall ip of DUT(Default: 192.168.168.168)')

    # Reporter and logger options
    parser.add_argument('--csv_report', action='store_true', default=True,
                        help='Generate CSV report (Default: True) ')
    parser.add_argument('--csv_filename',
                        help='CSV report file name')

    # Other options
    parser.add_argument('--dry_run', action='store_true',
                        help='Dry run mode, only collect tests without executing them')
    parser.add_argument('--debug', action='store_true',
                        help='debug mode, enable verbose logging')

    return parser.parse_args()


def generate_csv_filename():
    """Generate CSV report filename with timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"csv_results_{timestamp}.csv"


def build_pytest_command(args, csv_file_path):
    """build pytest command based on arguments"""
    cmd = ['pytest']

    # Test files or directories
    if args.tests:
        cmd.extend(args.tests)
    else:
        cmd.append(f'{Settings.ROOT_DIR}/tests/')  # Default test directory

    # Mark selection
    if args.mark:
        cmd.extend(['-m', args.mark])

    # Keyword selection
    if args.keyword:
        cmd.extend(['-k', args.keyword])

    # Running options
    cmd.extend([
        '--tb=short',  # short traceback
        '--strict-markers',
        '--disable-warnings',
        '-s',
        '-v'
    ])

    #  Add csv report file option when --csv_report is specified
    if args.csv_report:
        cmd.extend(['--csv_file', str(csv_file_path)])

    # self-specified arguments
    cmd.append(f'--browser={args.browser}')
    if args.headed:
        cmd.append('--headed')
    cmd.extend([
        f'--password={args.password}',
        f'--slowmo={args.slowmo}',
        f'--fw_ip={args.fw_ip}',
    ])

    # debug mode
    if args.debug:
        cmd.extend(['-v', '-s', '--log-cli-level=DEBUG'])

    # Dry run mode, only collect tests
    if args.dry_run:
        cmd.extend(['--collect-only'])

    return cmd


def run_tests(pytest_cmd):
    """Run tests"""
    logger.info(f"{Fore.CYAN}Run commands: {' '.join(pytest_cmd)}{Style.RESET_ALL}")

    try:
        # Run tests
        result = subprocess.run(
            pytest_cmd,
            cwd=Settings.ROOT_DIR,
            check=False,
            capture_output=False,  # Capture output for logging
            text=True
        )

        if result.returncode != 0:
            logger.error(f"{Fore.RED}Tests failed! {result.stderr} {Style.RESET_ALL}")
        return result.returncode

    except KeyboardInterrupt:
        logger.info(f"\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
        return 130
    except Exception as e:
        logger.error(f"{Fore.RED}Error Exception: {e}{Style.RESET_ALL}")
        return 1


def show_csv_report(csv_file_path):
    """show CSV report content"""
    if not csv_file_path.exists():
        print(f"{Fore.YELLOW}Warning: CSV report file not found: {csv_file_path}{Style.RESET_ALL}")
        return

    with open(csv_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print("\nCSV Report Content (First 10 lines):")
        for _, line in enumerate(lines[:10]):
            print(f"  {line.strip()}")


def show_log_result(log_file_path):
    """show log report content"""
    if not log_file_path.exists():
        print(f"{Fore.YELLOW}Warning: LOG report file not found: {log_file_path}{Style.RESET_ALL}")
        return

    with open(log_file_path, 'r', encoding='utf-8') as f:
        out = f.read()
        print(f"\nLOG Report Content:\n{out}")


def main():
    """Main function to run tests"""
    # Analyze command-line arguments
    args = parse_arguments()

    # # 参数校验
    # if not args.fw_ip:
    #     logger.error(f"Invalid firewall IP: {args.fw_ip}")
    #     sys.exit(1)
    Settings.FIREWALL_IP = args.fw_ip
    Settings.BASE_URL = f"https://{args.fw_ip}/sonicui/7"

    #  Print banner
    print_banner()

    # Setup CSV file paths
    if args.csv_filename:
        csv_file_path = Settings.ROOT_DIR / "reports" / args.csv_filename
    else:
        csv_file_path = Settings.ROOT_DIR / "reports" / Settings.CSV_FILE_NAME

    # Ensure directories exist
    csv_file_path.parent.mkdir(parents=True, exist_ok=True)

    # build pytest command
    pytest_cmd = build_pytest_command(args, csv_file_path)

    # Record start time
    start_time = datetime.now()
    logger.info(f"Start time: {start_time}")

    # Run tests
    exit_code = run_tests(pytest_cmd)

    # Record end time
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"End time: {end_time} (Duration: {duration:.2f}s)")

    # show CSV report
    if args.csv_report and csv_file_path.exists():
        show_csv_report(csv_file_path)

    # show LOG report
    log_file_path = Settings.ROOT_DIR / "logs" / Settings.LOG_FILE_NAME
    # if log_file_path.exists():
    #     show_log_result(log_file_path) #debug

    # Clean up temporary files
    if not args.debug:
        cleanup_temp_files()

    return exit_code


def cleanup_temp_files():
    """Clean up temporary files"""
    temp_dirs = [
        Settings.ROOT_DIR / '__pycache__',
        Settings.ROOT_DIR / '.pytest_cache',
        Settings.ROOT_DIR / 'tests' / '__pycache__',
    ]

    for temp_dir in temp_dirs:
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Test Error Exception: {e}", exc_info=True)
        sys.exit(1)
