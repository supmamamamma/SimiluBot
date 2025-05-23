"""MEGA downloader module for SimiluBot."""
import asyncio
import glob
import hashlib
import logging
import os
import re
import shutil
import tempfile
import time
import threading
from typing import List, Optional, Tuple, Callable, Any, Set
from mega import Mega

from similubot.utils.config_manager import ConfigManager

class MegaDownloader:
    """
    Downloader for MEGA links.

    Handles downloading files from MEGA links to a local directory.
    """

    # Regular expression to match MEGA links
    # This pattern handles various MEGA link formats:
    # - https://mega.nz/file/ABCDEF#GHIJKLMNO (new format)
    # - https://mega.nz/#!ABCDEF!GHIJKLMNO (old format)
    # - https://mega.nz/folder/ABCDEF#GHIJKLMNO (folder links)
    MEGA_LINK_PATTERN = r'https?://mega\.nz/(?:file/[^/\s#]+(?:#[^/\s]+)?|folder/[^/\s#]+(?:#[^/\s]+)?|#!?[^/\s!]+(?:![^/\s]+)?)'

    def __init__(self, config: Optional[ConfigManager] = None, temp_dir: Optional[str] = None):
        """
        Initialize the MEGA downloader.

        Args:
            config: Configuration manager
            temp_dir: Directory to store downloaded files (overrides config if provided)
        """
        self.logger = logging.getLogger("similubot.downloader.mega")

        # Use provided config or create a new one
        self.config = config or ConfigManager()

        # Use provided temp_dir or get from config
        self.temp_dir = temp_dir or self.config.get_download_temp_dir()

        # Get cache configuration
        self.max_cache_files = self.config.get_max_cache_files()
        self.hash_algorithm = self.config.get_hash_algorithm()

        self.logger.debug(f"Cache configuration: max_files={self.max_cache_files}, hash={self.hash_algorithm}")

        # Ensure temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            self.logger.debug(f"Created temporary directory: {self.temp_dir}")

        # Initialize MEGA client
        self.mega = Mega()
        self.mega_client = self.mega.login()
        self.logger.debug("Initialized MEGA client")

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

    def _get_temp_directory(self) -> str:
        """
        Get the system temporary directory where mega.py creates temporary files.

        Returns:
            Path to the temporary directory
        """
        return tempfile.gettempdir()

    def _scan_temp_files(self) -> Set[str]:
        """
        Scan the temporary directory for existing megapy_* files.

        Returns:
            Set of existing temporary file paths
        """
        temp_dir = self._get_temp_directory()
        try:
            # Use glob to find all megapy_* files in the temp directory
            pattern = os.path.join(temp_dir, "megapy_*")
            existing_files = set(glob.glob(pattern))
            self.logger.debug(f"Found {len(existing_files)} existing megapy temp files")
            return existing_files
        except Exception as e:
            self.logger.warning(f"Error scanning temp directory: {e}")
            return set()

    def _detect_new_temp_file(self, baseline_files: Set[str], timeout: int = 30) -> Optional[str]:
        """
        Detect a new temporary file created by mega.py after download starts.

        Args:
            baseline_files: Set of existing temp files before download
            timeout: Maximum time to wait for new file detection (seconds)

        Returns:
            Path to the new temporary file, or None if not detected
        """
        temp_dir = self._get_temp_directory()
        start_time = time.time()

        self.logger.debug(f"Looking for new temp files in: {temp_dir}")

        while time.time() - start_time < timeout:
            try:
                # Scan for new megapy_* files
                pattern = os.path.join(temp_dir, "megapy_*")
                current_files = set(glob.glob(pattern))

                # Find new files that weren't in the baseline
                new_files = current_files - baseline_files

                if new_files:
                    # Check each new file to see if it's actually being written to
                    for new_file in new_files:
                        if os.path.exists(new_file):
                            # Wait a bit to see if the file size changes (indicating active download)
                            initial_size = os.path.getsize(new_file)
                            time.sleep(1)

                            if os.path.exists(new_file):
                                current_size = os.path.getsize(new_file)
                                if current_size >= initial_size:  # File is growing or at least stable
                                    self.logger.debug(f"Detected active temp file: {new_file} (size: {current_size})")
                                    return new_file

                time.sleep(0.5)  # Check every 0.5 seconds

            except Exception as e:
                self.logger.warning(f"Error detecting new temp file: {e}")
                time.sleep(1)

        self.logger.warning(f"No new temp file detected within {timeout} seconds")
        return None

    def _move_temp_file_to_cache(self, temp_file_path: str, original_filename: str) -> Optional[str]:
        """
        Move a temporary file to our cache directory with hashed filename.

        Args:
            temp_file_path: Path to the temporary file
            original_filename: Original filename from MEGA

        Returns:
            Path to the final cached file, or None if move failed
        """
        try:
            # Generate hash from original filename
            filename_hash = self._hash_filename(original_filename)

            # Get file extension from original filename
            _, ext = os.path.splitext(original_filename)

            # Create final filename with hash and original extension
            final_filename = f"{filename_hash}{ext}"
            final_path = os.path.join(self.temp_dir, final_filename)

            self.logger.debug(f"Moving temp file: {temp_file_path} -> {final_path}")

            # Check if target file already exists
            if os.path.exists(final_path):
                self.logger.info(f"Target file already exists: {final_path}")
                # Remove the temporary file since we already have the target
                try:
                    os.remove(temp_file_path)
                    self.logger.debug(f"Removed temporary file: {temp_file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp file {temp_file_path}: {e}")
                return final_path

            # Move the file using shutil.move (handles cross-filesystem moves)
            shutil.move(temp_file_path, final_path)

            self.logger.info(f"Successfully moved file to: {final_path}")
            return final_path

        except Exception as e:
            self.logger.error(f"Failed to move temp file {temp_file_path}: {e}")
            return None

    def download(self, url: str, progress_callback: Optional[Callable] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download a file from a MEGA link with improved progress tracking and filename handling.

        Args:
            url: MEGA link to download
            progress_callback: Optional callback for progress updates

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

            # Clean cache before downloading to ensure we have space
            self._clean_cache()

            # Try to get file info first to check the filename
            success, file_info, _ = self.get_file_info(url)
            original_filename = None
            file_size = 0

            if success and file_info and 'name' in file_info:
                original_filename = file_info['name']
                file_size = file_info.get('size', 0)
                self.logger.debug(f"Original filename from info: {original_filename}, size: {file_size}")

                # Generate hash from original filename
                filename_hash = self._hash_filename(original_filename)

                # Get file extension
                _, ext = os.path.splitext(original_filename)

                # Check if file with this hash already exists
                hashed_filename = f"{filename_hash}{ext}"
                existing_file_path = os.path.join(self.temp_dir, hashed_filename)

                if os.path.exists(existing_file_path):
                    self.logger.info(f"File already exists in cache: {hashed_filename}")
                    # Update access time to mark as recently used
                    os.utime(existing_file_path, None)

                    # Call progress callback with 100% completion if provided
                    if progress_callback:
                        try:
                            if asyncio.iscoroutinefunction(progress_callback):
                                # For async callbacks, we need to schedule them properly
                                try:
                                    # Try to get the current event loop
                                    loop = asyncio.get_running_loop()
                                    # Schedule the coroutine to run in the loop
                                    asyncio.run_coroutine_threadsafe(
                                        progress_callback(file_size, file_size, 0), loop
                                    )
                                except RuntimeError:
                                    # No running loop, create a new one
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    try:
                                        loop.run_until_complete(progress_callback(file_size, file_size, 0))
                                    finally:
                                        loop.close()
                            else:
                                progress_callback(file_size, file_size, 0)
                        except Exception as e:
                            self.logger.warning(f"Progress callback error: {e}")

                    return True, existing_file_path, None

            # Download the file with improved progress tracking and filename handling
            if progress_callback and file_size > 0 and original_filename:
                file_path = self._download_with_improved_progress(url, original_filename, file_size, progress_callback)
            else:
                # Fallback to simple download without progress tracking
                file_path = self._download_simple(url, original_filename)

            if not file_path or not os.path.exists(file_path):
                error_msg = "Download failed: File not found after download"
                self.logger.error(error_msg)
                return False, None, error_msg

            actual_file_size = os.path.getsize(file_path)
            self.logger.info(f"Download successful: {os.path.basename(file_path)} ({actual_file_size} bytes)")

            return True, file_path, None

        except OSError as e:
            # Handle specific case of filename too long
            if "File name too long" in str(e):
                error_msg = f"Filename too long error: {str(e)}"
                self.logger.error(error_msg)
                self.logger.info("This error is being handled by using hashed filenames")
                # We'll return a more user-friendly error message
                return False, None, "Filename too long. The bot will use hashed filenames in future downloads."
            else:
                error_msg = f"Download failed with OS error: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                return False, None, error_msg
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def _download_simple(self, url: str, original_filename: Optional[str]) -> Optional[str]:
        """
        Simple download without progress tracking, with proper filename handling.

        Args:
            url: MEGA URL to download
            original_filename: Original filename from MEGA

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Start download in a separate thread to avoid blocking
            download_result: dict = {'file_path': None, 'error': None}

            def download_worker():
                try:
                    # Use a temporary directory to avoid filename issues
                    temp_download_dir = tempfile.mkdtemp()
                    self.logger.debug(f"Using temporary download directory: {temp_download_dir}")

                    # Download to temp directory first
                    file_path = self.mega_client.download_url(url, dest_path=temp_download_dir)
                    download_result['file_path'] = file_path
                except Exception as e:
                    download_result['error'] = str(e)

            download_thread = threading.Thread(target=download_worker)
            download_thread.start()
            download_thread.join()

            if download_result['error']:
                self.logger.error(f"Download error: {download_result['error']}")
                return None

            temp_file_path = download_result['file_path']
            if not temp_file_path or not os.path.exists(temp_file_path):
                self.logger.error("Download failed: No file returned")
                return None

            # Convert Path object to string if necessary
            if not isinstance(temp_file_path, str):
                temp_file_path = str(temp_file_path)

            # Move to our cache directory with hashed filename
            if original_filename:
                final_path = self._move_temp_file_to_cache(temp_file_path, original_filename)
                if final_path:
                    return final_path

            # Fallback: move to cache with original filename if available
            if original_filename:
                try:
                    final_path = os.path.join(self.temp_dir, os.path.basename(original_filename))
                    shutil.move(temp_file_path, final_path)
                    return final_path
                except Exception as e:
                    self.logger.warning(f"Failed to move with original filename: {e}")

            # Last resort: move with a generic name
            try:
                final_path = os.path.join(self.temp_dir, f"downloaded_file_{int(time.time())}")
                shutil.move(temp_file_path, final_path)
                return final_path
            except Exception as e:
                self.logger.error(f"Failed to move file: {e}")
                return None

        except Exception as e:
            self.logger.error(f"Simple download failed: {e}")
            return None

    def _download_with_improved_progress(self, url: str, original_filename: str, total_size: int, progress_callback: Callable) -> Optional[str]:
        """
        Download file with improved progress tracking that monitors actual temp files.

        Args:
            url: MEGA URL to download
            original_filename: Original filename from MEGA
            total_size: Total file size in bytes
            progress_callback: Progress callback function

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            self.logger.info(f"Starting download with progress tracking: {original_filename}")

            # Get baseline of existing temp files before download
            baseline_files = self._scan_temp_files()
            self.logger.debug(f"Baseline temp files: {len(baseline_files)}")

            # Start download in a separate thread
            download_result: dict = {'file_path': None, 'error': None, 'started': False, 'temp_file': None}

            def download_worker():
                try:
                    download_result['started'] = True
                    # Let mega.py use its default temp directory (/tmp) so we can monitor it
                    self.logger.debug("Starting MEGA download (using system temp directory)")

                    # Download using mega.py's default behavior
                    file_path = self.mega_client.download_url(url, dest_path=None)
                    download_result['file_path'] = file_path
                except Exception as e:
                    download_result['error'] = str(e)

            download_thread = threading.Thread(target=download_worker)
            download_thread.start()

            # Wait for download to start
            start_time = time.time()
            while not download_result['started'] and time.time() - start_time < 10:
                time.sleep(0.1)

            if not download_result['started']:
                self.logger.warning("Download did not start within 10 seconds")
                # Fallback to estimated progress
                self._simulate_progress(total_size, progress_callback, download_thread)
            else:
                # Try to detect the new temp file created by mega.py
                temp_file_path = self._detect_new_temp_file(baseline_files, timeout=15)

                if temp_file_path:
                    self.logger.info(f"Detected and monitoring temp file: {temp_file_path}")
                    download_result['temp_file'] = temp_file_path
                    # Monitor the detected temp file for progress
                    self._monitor_temp_file_progress(temp_file_path, total_size, progress_callback, download_thread)
                else:
                    self.logger.warning("Could not detect temp file, using estimated progress")
                    # Fallback to estimated progress
                    self._simulate_progress(total_size, progress_callback, download_thread)

            # Wait for download to complete
            download_thread.join()

            if download_result['error']:
                self.logger.error(f"Download error: {download_result['error']}")
                return None

            downloaded_file_path = download_result['file_path']
            if not downloaded_file_path:
                self.logger.error("Download failed: No file path returned")
                return None

            # Convert Path object to string if necessary
            if not isinstance(downloaded_file_path, str):
                downloaded_file_path = str(downloaded_file_path)

            # Check if the downloaded file exists
            if not os.path.exists(downloaded_file_path):
                self.logger.error(f"Download failed: File not found at {downloaded_file_path}")

                # Try to find the file in the temp directory if we detected a temp file
                if download_result['temp_file'] and os.path.exists(download_result['temp_file']):
                    self.logger.info(f"Using detected temp file: {download_result['temp_file']}")
                    downloaded_file_path = download_result['temp_file']
                else:
                    return None

            # Final progress update
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    # For async callbacks, we need to schedule them properly
                    try:
                        # Try to get the current event loop
                        loop = asyncio.get_running_loop()
                        # Schedule the coroutine to run in the loop
                        asyncio.run_coroutine_threadsafe(
                            progress_callback(total_size, total_size, 0), loop
                        )
                    except RuntimeError:
                        # No running loop, create a new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(progress_callback(total_size, total_size, 0))
                        finally:
                            loop.close()
                else:
                    progress_callback(total_size, total_size, 0)
            except Exception as e:
                self.logger.warning(f"Final progress callback error: {e}")

            # Move to our cache directory with hashed filename
            final_path = self._move_temp_file_to_cache(downloaded_file_path, original_filename)
            if final_path:
                return final_path

            # Fallback: return the downloaded file path
            return downloaded_file_path

        except Exception as e:
            self.logger.error(f"Download with progress failed: {e}")
            return None

    def _monitor_temp_file_progress(self, temp_file_path: str, total_size: int, progress_callback: Callable, download_thread: threading.Thread) -> None:
        """
        Monitor the progress of a temporary file during download.

        Args:
            temp_file_path: Path to the temporary file to monitor
            total_size: Total expected file size
            progress_callback: Progress callback function
            download_thread: Download thread to check if still running
        """
        last_size = 0
        last_time = time.time()
        last_update_time = time.time()
        stall_count = 0

        self.logger.debug(f"Starting progress monitoring for: {temp_file_path}")

        while download_thread.is_alive():
            try:
                current_time = time.time()
                current_size = 0

                if os.path.exists(temp_file_path):
                    current_size = os.path.getsize(temp_file_path)
                else:
                    # File might have been moved/renamed by mega.py
                    self.logger.debug(f"Temp file no longer exists: {temp_file_path}")
                    time.sleep(0.5)
                    continue

                # Calculate speed
                time_diff = current_time - last_time
                if time_diff >= 1.0:  # Update every second
                    size_diff = current_size - last_size
                    speed = size_diff / time_diff if time_diff > 0 else 0

                    # Check for stalled download
                    if size_diff == 0:
                        stall_count += 1
                        if stall_count > 10:  # 10 seconds without progress
                            self.logger.warning(f"Download appears stalled (no progress for {stall_count} seconds)")
                    else:
                        stall_count = 0

                    # Call progress callback
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            # For async callbacks, we need to schedule them properly
                            try:
                                # Try to get the current event loop
                                loop = asyncio.get_running_loop()
                                # Schedule the coroutine to run in the loop
                                asyncio.run_coroutine_threadsafe(
                                    progress_callback(current_size, total_size, speed), loop
                                )
                            except RuntimeError:
                                # No running loop, create a new one
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(progress_callback(current_size, total_size, speed))
                                finally:
                                    loop.close()
                        else:
                            progress_callback(current_size, total_size, speed)
                    except Exception as e:
                        self.logger.warning(f"Progress callback error: {e}")

                    last_size = current_size
                    last_time = current_time
                    last_update_time = current_time

                    # Log progress periodically
                    if current_size > 0:
                        progress_pct = (current_size / total_size) * 100 if total_size > 0 else 0
                        self.logger.debug(f"Download progress: {current_size}/{total_size} bytes ({progress_pct:.1f}%) - Speed: {speed:.1f} B/s")

                time.sleep(0.5)  # Check every 0.5 seconds

            except Exception as e:
                self.logger.warning(f"Error monitoring temp file progress: {e}")
                time.sleep(1)

        self.logger.debug("Download thread finished, stopping progress monitoring")

    def _simulate_progress(self, total_size: int, progress_callback: Callable, download_thread: threading.Thread) -> None:
        """
        Simulate download progress when actual temp file cannot be monitored.

        Args:
            total_size: Total expected file size
            progress_callback: Progress callback function
            download_thread: Download thread to check if still running
        """
        start_time = time.time()
        estimated_duration = max(total_size / (2 * 1024 * 1024), 10)  # Estimate based on 2MB/s, minimum 10 seconds

        while download_thread.is_alive():
            try:
                elapsed = time.time() - start_time
                progress = min((elapsed / estimated_duration) * 100, 95)  # Cap at 95% until download completes
                current_size = int((progress / 100) * total_size)
                speed = total_size / estimated_duration

                # Call progress callback
                try:
                    if asyncio.iscoroutinefunction(progress_callback):
                        # For async callbacks, we need to schedule them properly
                        try:
                            # Try to get the current event loop
                            loop = asyncio.get_running_loop()
                            # Schedule the coroutine to run in the loop
                            asyncio.run_coroutine_threadsafe(
                                progress_callback(current_size, total_size, speed), loop
                            )
                        except RuntimeError:
                            # No running loop, create a new one
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(progress_callback(current_size, total_size, speed))
                            finally:
                                loop.close()
                    else:
                        progress_callback(current_size, total_size, speed)
                except Exception as e:
                    self.logger.warning(f"Progress callback error: {e}")

                time.sleep(1)  # Update every second

            except Exception as e:
                self.logger.warning(f"Error simulating progress: {e}")
                time.sleep(1)



    def _hash_filename(self, filename: str) -> str:
        """
        Generate a hash for a filename.

        Args:
            filename: Original filename

        Returns:
            Hash string of the filename
        """
        # Create hash object based on configured algorithm
        if self.hash_algorithm == 'sha1':
            hash_obj = hashlib.sha1()
        elif self.hash_algorithm == 'sha256':
            hash_obj = hashlib.sha256()
        else:  # Default to MD5
            hash_obj = hashlib.md5()

        # Update hash with filename bytes
        hash_obj.update(filename.encode('utf-8', errors='replace'))

        # Return hexadecimal digest
        return hash_obj.hexdigest()

    def _rename_with_hash(self, file_path: str) -> str:
        """
        Rename a file using a hash of its original filename.

        Args:
            file_path: Path to the file

        Returns:
            New file path with hashed filename
        """
        # Get directory and filename
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)

        # Get file extension
        _, ext = os.path.splitext(filename)

        # Generate hash from original filename
        filename_hash = self._hash_filename(filename)

        # Create new filename with hash and original extension
        new_filename = f"{filename_hash}{ext}"
        new_file_path = os.path.join(directory, new_filename)

        self.logger.debug(f"Renaming file: {filename} -> {new_filename}")

        # Check if file with same hash already exists
        if os.path.exists(new_file_path):
            self.logger.info(f"File with hash {filename_hash} already exists, using existing file")
            # Remove the original file if it's different from the hash-named file
            if os.path.abspath(file_path) != os.path.abspath(new_file_path):
                try:
                    os.remove(file_path)
                    self.logger.debug(f"Removed duplicate file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove duplicate file {file_path}: {e}")
            return new_file_path

        # Rename the file
        try:
            os.rename(file_path, new_file_path)
            self.logger.debug(f"Renamed file to: {new_file_path}")
            return new_file_path
        except Exception as e:
            self.logger.error(f"Failed to rename file {file_path}: {e}")
            return file_path  # Return original path if rename fails

    def _clean_cache(self) -> None:
        """
        Clean up old cache files to maintain the maximum number of files.
        """
        try:
            # Get all files in the temp directory
            files = [os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir)
                    if os.path.isfile(os.path.join(self.temp_dir, f))]

            # If number of files is less than or equal to max_cache_files, no need to clean
            if len(files) <= self.max_cache_files:
                return

            # Sort files by modification time (oldest first)
            files.sort(key=os.path.getmtime)

            # Calculate how many files to delete
            files_to_delete = files[:len(files) - self.max_cache_files]

            # Delete oldest files
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    self.logger.debug(f"Removed old cache file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove cache file {file_path}: {e}")

        except Exception as e:
            self.logger.error(f"Error cleaning cache: {e}")

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

            # Get file info
            file_info = self.mega_client.get_public_url_info(url)

            if not file_info:
                error_msg = "Failed to get file info"
                self.logger.error(error_msg)
                return False, None, error_msg

            self.logger.info(f"File info retrieved successfully")
            self.logger.debug(f"File info: {file_info}")

            return True, file_info, None

        except Exception as e:
            error_msg = f"Failed to get file info: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
