# /config/csv_reporter.py, CSV Reporter Module
from config.logger import get_logger
from config.settings import csv, Dict, Any, Path


logger = get_logger('csv_reporter')


class CSVReporter:
    """CSVReporter"""

    CSV_HEADERS = [
        'uuid',
        'status',
        'error_message',
    ]

    def __init__(self, csv_file_path: Path):
        self.csv_file_path = csv_file_path
        self._ensure_csv_file()
        logger.info(f"CSV Report file: {csv_file_path}")

    def _ensure_csv_file(self):
        """ensure CSV file exists with valid headers"""
        self.csv_file_path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = True
        if self.csv_file_path.exists():
            try:
                with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line == 'uuid,status,error_message':
                        needs_header = False
            except Exception:
                pass
        if needs_header:
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
                writer.writeheader()

    def record_test_result(self, test_data: Dict[str, Any]):
        """record test result to CSV file"""
        try:
            with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)

                # make sure only known headers are written
                filtered_data = {k: test_data.get(k, '') for k in self.CSV_HEADERS}
                writer.writerow(filtered_data)

                # log csv record
                status = test_data.get('status', 'unknown')
                uuid = test_data.get('uuid', 'unknown')
                if status == 'passed':
                    logger.info(f"------ {uuid} - Passed")
                elif status == 'failed':
                    logger.error(f"------- {uuid} - Failed: {test_data.get('error_message', 'Unknown Error')}")
                elif status == 'skipped':
                    logger.warning(f"------- {uuid} - Skipped")

        except Exception as e:
            logger.error(f"Record test result failed: {e}")

    def show_summary_statistics(self, csv_file: Path):
        """show csv summary statistics"""
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            if len(rows) < 2:
                logger.info("No test results found in the CSV file.")
                return

            # Use header row to find column index (fallback to 1 for 'status')
            header = rows[0]
            data_rows = rows[1:]
            try:
                status_idx = header.index('status')
            except ValueError:
                status_idx = 1

            total = len(data_rows)
            passed = sum(1 for row in data_rows if len(row) > status_idx and row[status_idx] == 'passed')
            failed = sum(1 for row in data_rows if len(row) > status_idx and row[status_idx] == 'failed')
            skipped = sum(1 for row in data_rows if len(row) > status_idx and row[status_idx] == 'skipped')

            logger.info("=" * 50)
            logger.info("Test Summary Statistics:")
            logger.info(f"Total  : {total}")
            logger.info(f"Passed : {passed}")
            logger.info(f"Failed : {failed}")
            logger.info(f"Skipped: {skipped}")

            if total > 0:
                pass_rate = (passed / total) * 100
                logger.info(f"Pass Rate: {pass_rate:.1f}%")

            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Get summary statistics failed: {e}")
