"""MEGA downloader module for SimiluBot."""
import asyncio
import hashlib
import logging
import os
import re
import time
import threading
from typing import List, Optional, Tuple, Callable, Any
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

    def download(self, url: str, progress_callback: Optional[Callable] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download a file from a MEGA link.

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
                                # Run async callback in a thread-safe way
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(progress_callback(file_size, file_size, 0))
                                loop.close()
                            else:
                                progress_callback(file_size, file_size, 0)
                        except Exception as e:
                            self.logger.warning(f"Progress callback error: {e}")

                    return True, existing_file_path, None

            # Download the file with progress tracking
            if progress_callback and file_size > 0 and original_filename:
                file_path = self._download_with_progress(url, original_filename, file_size, progress_callback)
            else:
                file_path = self.mega_client.download_url(url, dest_path=self.temp_dir)

            if not file_path or not os.path.exists(file_path):
                error_msg = "Download failed: File not found after download"
                self.logger.error(error_msg)
                return False, None, error_msg

            # Convert Path object to string if necessary
            if not isinstance(file_path, str):
                file_path = str(file_path)

            actual_file_size = os.path.getsize(file_path)
            self.logger.info(f"Download successful: {os.path.basename(file_path)} ({actual_file_size} bytes)")

            # Rename file using hash to avoid long filenames
            hashed_file_path = self._rename_with_hash(file_path)

            return True, hashed_file_path, None

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

    def _download_with_progress(self, url: str, filename: str, total_size: int, progress_callback: Callable) -> Optional[str]:
        """
        Download file with progress tracking.

        Args:
            url: MEGA URL to download
            filename: Original filename
            total_size: Total file size in bytes
            progress_callback: Progress callback function

        Returns:
            Path to downloaded file
        """
        # Since mega.py doesn't support progress callbacks directly,
        # we'll simulate progress by monitoring the file size during download
        download_thread = None
        file_path = None

        def download_worker():
            nonlocal file_path
            file_path = self.mega_client.download_url(url, dest_path=self.temp_dir)

        # Start download in a separate thread
        download_thread = threading.Thread(target=download_worker)
        download_thread.start()

        # Monitor progress
        start_time = time.time()
        last_size = 0
        last_time = start_time

        # Try to find the downloading file
        temp_file_path = None
        if filename:
            # Look for temporary files that might be the download
            for i in range(30):  # Wait up to 30 seconds for download to start
                time.sleep(1)
                for temp_file in os.listdir(self.temp_dir):
                    temp_path = os.path.join(self.temp_dir, temp_file)
                    if os.path.isfile(temp_path) and temp_file.startswith('megapy_'):
                        temp_file_path = temp_path
                        break
                if temp_file_path:
                    break

        # Monitor file size growth
        while download_thread.is_alive():
            try:
                current_time = time.time()
                current_size = 0

                if temp_file_path and os.path.exists(temp_file_path):
                    current_size = os.path.getsize(temp_file_path)

                # Calculate speed
                time_diff = current_time - last_time
                if time_diff >= 1.0:  # Update every second
                    size_diff = current_size - last_size
                    speed = size_diff / time_diff if time_diff > 0 else 0

                    # Call progress callback
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            # Run async callback in a thread-safe way
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(progress_callback(current_size, total_size, speed))
                            loop.close()
                        else:
                            progress_callback(current_size, total_size, speed)
                    except Exception as e:
                        self.logger.warning(f"Progress callback error: {e}")

                    last_size = current_size
                    last_time = current_time

                time.sleep(0.5)  # Check every 0.5 seconds

            except Exception as e:
                self.logger.warning(f"Error monitoring download progress: {e}")
                time.sleep(1)

        # Wait for download to complete
        download_thread.join()

        # Final progress update
        if progress_callback and file_path and os.path.exists(file_path):
            final_size = os.path.getsize(file_path)
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(progress_callback(final_size, final_size, 0))
                    loop.close()
                else:
                    progress_callback(final_size, final_size, 0)
            except Exception as e:
                self.logger.warning(f"Final progress callback error: {e}")

        return file_path

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
