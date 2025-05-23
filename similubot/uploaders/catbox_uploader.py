"""CatBox uploader module for SimiluBot."""
import asyncio
import logging
import os
import requests
import threading
import time
from typing import Optional, Tuple, Callable

class CatboxUploader:
    """
    Uploader for CatBox file hosting service.

    Handles uploading files to CatBox and retrieving the public URL.
    """

    # CatBox API endpoint
    CATBOX_API_URL = "https://catbox.moe/user/api.php"

    def __init__(self, user_hash: Optional[str] = None):
        """
        Initialize the CatBox uploader.

        Args:
            user_hash: CatBox user hash for file management (optional)
        """
        self.logger = logging.getLogger("similubot.uploader.catbox")
        self.user_hash = user_hash

    def upload(self, file_path: str, progress_callback: Optional[Callable] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a file to CatBox.

        Args:
            file_path: Path to the file to upload
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple containing:
                - Success status (True/False)
                - Public URL if successful, None otherwise
                - Error message if failed, None otherwise
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            return False, None, error_msg

        try:
            self.logger.info(f"Uploading file to CatBox: {file_path}")

            # Get file size for progress tracking
            file_size = os.path.getsize(file_path)

            # Prepare request data
            data = {
                'reqtype': 'fileupload',
            }

            # Add user hash if available
            if self.user_hash:
                data['userhash'] = self.user_hash

            # Upload with or without progress tracking
            if progress_callback:
                url = self._upload_with_progress(file_path, data, file_size, progress_callback)
            else:
                # Prepare file data
                files = {
                    'fileToUpload': (
                        os.path.basename(file_path),
                        open(file_path, 'rb'),
                        'application/octet-stream'
                    )
                }

                try:
                    # Send request
                    self.logger.debug(f"Sending request to {self.CATBOX_API_URL}")
                    response = requests.post(
                        self.CATBOX_API_URL,
                        data=data,
                        files=files
                    )

                    # Check response
                    if response.status_code != 200:
                        error_msg = f"Upload failed: HTTP {response.status_code} - {response.text}"
                        self.logger.error(error_msg)
                        return False, None, error_msg

                    # Get URL from response
                    url = response.text.strip()

                    if not url.startswith('http'):
                        error_msg = f"Upload failed: Invalid response - {url}"
                        self.logger.error(error_msg)
                        return False, None, error_msg
                finally:
                    # Close file
                    files['fileToUpload'][1].close()

            if not url:
                return False, None, "Upload failed: No URL returned"

            self.logger.info(f"Upload successful: {url}")
            return True, url, None

        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def _upload_with_progress(self, file_path: str, data: dict, file_size: int, progress_callback: Callable) -> Optional[str]:
        """
        Upload file with progress tracking.

        Args:
            file_path: Path to the file to upload
            data: Request data
            file_size: Size of the file in bytes
            progress_callback: Progress callback function

        Returns:
            Upload URL if successful, None otherwise
        """
        # Since requests doesn't support upload progress directly,
        # we'll simulate progress by monitoring the upload
        upload_result = {'url': None, 'error': None}

        def upload_worker():
            try:
                files = {
                    'fileToUpload': (
                        os.path.basename(file_path),
                        open(file_path, 'rb'),
                        'application/octet-stream'
                    )
                }

                try:
                    response = requests.post(
                        self.CATBOX_API_URL,
                        data=data,
                        files=files
                    )

                    if response.status_code == 200:
                        url = response.text.strip()
                        if url.startswith('http'):
                            upload_result['url'] = url
                        else:
                            upload_result['error'] = f"Invalid response: {url}"
                    else:
                        upload_result['error'] = f"HTTP {response.status_code} - {response.text}"
                finally:
                    files['fileToUpload'][1].close()

            except Exception as e:
                upload_result['error'] = str(e)

        # Start upload in a separate thread
        upload_thread = threading.Thread(target=upload_worker)
        upload_thread.start()

        # Simulate progress (since we can't track actual upload progress with requests)
        start_time = time.time()
        estimated_duration = max(file_size / (1024 * 1024), 5)  # Estimate based on file size, minimum 5 seconds

        while upload_thread.is_alive():
            elapsed = time.time() - start_time
            progress = min((elapsed / estimated_duration) * 100, 95)  # Cap at 95% until upload completes

            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    # Run async callback in a thread-safe way
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(progress_callback(int(progress * file_size / 100), file_size, file_size / estimated_duration))
                    loop.close()
                else:
                    progress_callback(int(progress * file_size / 100), file_size, file_size / estimated_duration)
            except Exception as e:
                self.logger.warning(f"Progress callback error: {e}")

            time.sleep(0.5)

        # Wait for upload to complete
        upload_thread.join()

        # Final progress update
        if upload_result['url']:
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(progress_callback(file_size, file_size, 0))
                    loop.close()
                else:
                    progress_callback(file_size, file_size, 0)
            except Exception as e:
                self.logger.warning(f"Final progress callback error: {e}")

        if upload_result['error']:
            self.logger.error(f"Upload error: {upload_result['error']}")

        return upload_result['url']

    def delete(self, file_url: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a file from CatBox.

        Note: This requires a user hash to be set.

        Args:
            file_url: URL of the file to delete

        Returns:
            Tuple containing:
                - Success status (True/False)
                - Error message if failed, None otherwise
        """
        if not self.user_hash:
            error_msg = "Cannot delete file: No user hash provided"
            self.logger.error(error_msg)
            return False, error_msg

        try:
            self.logger.info(f"Deleting file from CatBox: {file_url}")

            # Extract filename from URL
            filename = os.path.basename(file_url)

            # Prepare request data
            data = {
                'reqtype': 'deletefiles',
                'userhash': self.user_hash,
                'files': filename
            }

            # Send request
            self.logger.debug(f"Sending request to {self.CATBOX_API_URL}")
            response = requests.post(
                self.CATBOX_API_URL,
                data=data
            )

            # Check response
            if response.status_code != 200:
                error_msg = f"Delete failed: HTTP {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False, error_msg

            self.logger.info(f"Delete successful: {filename}")

            return True, None

        except Exception as e:
            error_msg = f"Delete failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
