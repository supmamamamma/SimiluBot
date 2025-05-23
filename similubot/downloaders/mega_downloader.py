"""MEGA downloader module for SimiluBot using MegaCMD."""
import logging
import os
import re
import subprocess
import time
from typing import Optional, Tuple

class MegaDownloader:
    """
    Downloader for MEGA links using MegaCMD.

    Handles downloading files from MEGA links to a local directory using
    the official MEGA command-line tool (MegaCMD) for better reliability.
    """

    # Regular expression to match MEGA links
    # This pattern handles various MEGA link formats:
    # - https://mega.nz/file/ABCDEF#GHIJKLMNO (new format)
    # - https://mega.nz/#!ABCDEF!GHIJKLMNO (old format)
    # - https://mega.nz/folder/ABCDEF#GHIJKLMNO (folder links)
    MEGA_LINK_PATTERN = r'https?://mega\.nz/(?:file/[^/\s#]+(?:#[^/\s]+)?|folder/[^/\s#]+(?:#[^/\s]+)?|#!?[^/\s!]+(?:![^/\s]+)?)'

    def __init__(self, temp_dir: str = "./temp"):
        """
        Initialize the MEGA downloader.

        Args:
            temp_dir: Directory to store downloaded files
        """
        self.logger = logging.getLogger("similubot.downloader.mega")
        self.temp_dir = temp_dir

        # Ensure temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            self.logger.debug(f"Created temporary directory: {self.temp_dir}")

        # Check if MegaCMD is available
        self._check_megacmd_availability()
        self.logger.debug("Initialized MegaCMD downloader")

    def _check_megacmd_availability(self) -> None:
        """
        Check if MegaCMD is available on the system.

        Raises:
            RuntimeError: If MegaCMD is not found or not working
        """
        try:
            # Try to run mega-version to check if MegaCMD is available
            result = subprocess.run(
                ["mega-version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version_info = result.stdout.strip()
                self.logger.info(f"MegaCMD found: {version_info}")
            else:
                raise RuntimeError(f"MegaCMD check failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("MegaCMD check timed out - command may be hanging")
        except FileNotFoundError:
            raise RuntimeError(
                "MegaCMD not found. Please install MegaCMD from https://mega.nz/cmd"
            )
        except Exception as e:
            raise RuntimeError(f"Error checking MegaCMD availability: {str(e)}")

    def _escape_mega_url(self, url: str) -> str:
        """
        Escape special characters in MEGA URLs for shell execution.

        Args:
            url: MEGA URL to escape

        Returns:
            Escaped URL safe for shell execution
        """
        # Escape exclamation marks for shell compatibility
        return url.replace('!', r'\!')

    def _run_megacmd_command(self, command: list, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Run a MegaCMD command and return the result.

        Args:
            command: List of command arguments
            timeout: Command timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            self.logger.debug(f"Running MegaCMD command: {' '.join(command)}")

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.temp_dir
            )

            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if success:
                self.logger.debug(f"Command succeeded: {stdout}")
            else:
                self.logger.error(f"Command failed (code {result.returncode}): {stderr}")

            return success, stdout, stderr

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            self.logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error running command: {str(e)}"
            self.logger.error(error_msg)
            return False, "", error_msg

    def is_mega_link(self, url: str) -> bool:
        """
        Check if a URL is a valid MEGA link.

        Args:
            url: URL to check

        Returns:
            True if the URL is a valid MEGA link, False otherwise
        """
        is_valid = bool(re.match(self.MEGA_LINK_PATTERN, url))
        self.logger.debug(f"MEGA link validation: {url} -> {'Valid' if is_valid else 'Invalid'}")
        return is_valid

    def extract_mega_links(self, text: str) -> list:
        """
        Extract MEGA links from text.

        Args:
            text: Text to extract links from

        Returns:
            List of MEGA links found in the text
        """
        return re.findall(self.MEGA_LINK_PATTERN, text)

    def download(self, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download a file from a MEGA link using MegaCMD.

        Args:
            url: MEGA link to download

        Returns:
            Tuple containing:
                - Success status (True/False)
                - Path to downloaded file if successful, None otherwise
                - Error message if failed, None otherwise
        """
        if not self.is_mega_link(url):
            error_msg = f"Invalid MEGA link: {url}"
            self.logger.error(error_msg)
            return False, None, error_msg

        try:
            self.logger.info(f"Downloading file from MEGA: {url}")
            self.logger.debug(f"Download destination: {self.temp_dir}")

            # Escape the URL for shell execution
            escaped_url = self._escape_mega_url(url)

            # Use mega-get to download the file
            command = ["mega-get", escaped_url, self.temp_dir]
            success, stdout, stderr = self._run_megacmd_command(command, timeout=600)

            if not success:
                error_msg = f"MegaCMD download failed: {stderr}"
                self.logger.error(error_msg)
                return False, None, error_msg

            # Find the downloaded file in the temp directory
            # MegaCMD downloads files with their original names
            downloaded_files = []
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                if os.path.isfile(file_path):
                    # Check if this file was recently created (within last 60 seconds)
                    file_mtime = os.path.getmtime(file_path)
                    current_time = time.time()
                    if current_time - file_mtime < 60:
                        downloaded_files.append(file_path)

            if not downloaded_files:
                error_msg = "Download completed but no new files found in temp directory"
                self.logger.error(error_msg)
                return False, None, error_msg

            # Use the most recently modified file
            file_path = max(downloaded_files, key=os.path.getmtime)

            if not os.path.exists(file_path):
                error_msg = "Download failed: File not found after download"
                self.logger.error(error_msg)
                return False, None, error_msg

            file_size = os.path.getsize(file_path)
            self.logger.info(f"Download successful: {os.path.basename(file_path)} ({file_size} bytes)")

            return True, file_path, None

        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def get_file_info(self, url: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Get information about a file from a MEGA link without downloading it.

        Args:
            url: MEGA link to get information for

        Returns:
            Tuple containing:
                - Success status (True/False)
                - File info dictionary if successful, None otherwise
                - Error message if failed, None otherwise
        """
        if not self.is_mega_link(url):
            error_msg = f"Invalid MEGA link: {url}"
            self.logger.error(error_msg)
            return False, None, error_msg

        try:
            self.logger.info(f"Getting file info from MEGA: {url}")

            # Escape the URL for shell execution
            escaped_url = self._escape_mega_url(url)

            # Use mega-ls to get file information
            # Note: mega-ls on a public link shows basic file info
            command = ["mega-ls", escaped_url]
            success, stdout, stderr = self._run_megacmd_command(command, timeout=30)

            if not success:
                error_msg = f"Failed to get file info: {stderr}"
                self.logger.error(error_msg)
                return False, None, error_msg

            if not stdout:
                error_msg = "No file information returned"
                self.logger.error(error_msg)
                return False, None, error_msg

            # Parse the output to extract file information
            # MegaCMD ls output format varies, but typically shows filename and size
            lines = stdout.strip().split('\n')
            file_info = {}

            for line in lines:
                line = line.strip()
                if line and not line.startswith('FILENAME') and not line.startswith('---'):
                    # Try to extract filename and size from the line
                    # Format is typically: filename    size    date
                    parts = line.split()
                    if len(parts) >= 2:
                        # First part is usually filename, second part might be size
                        file_info['name'] = parts[0]
                        # Try to parse size if it looks like a number or has size units
                        for part in parts[1:]:
                            if any(unit in part.upper() for unit in ['B', 'KB', 'MB', 'GB', 'TB']):
                                file_info['size_str'] = part
                                break
                            elif part.replace(',', '').replace('.', '').isdigit():
                                try:
                                    # Try to parse as integer (remove commas but keep decimal point for float)
                                    if '.' in part:
                                        file_info['size_bytes'] = int(float(part.replace(',', '')))
                                    else:
                                        file_info['size_bytes'] = int(part.replace(',', ''))
                                except ValueError:
                                    # If parsing fails, just store as string
                                    file_info['size_str'] = part
                                break
                    break

            if not file_info:
                # If parsing failed, just return the raw output
                file_info = {'raw_output': stdout}

            self.logger.info(f"File info retrieved successfully")
            self.logger.debug(f"File info: {file_info}")

            return True, file_info, None

        except Exception as e:
            error_msg = f"Failed to get file info: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
