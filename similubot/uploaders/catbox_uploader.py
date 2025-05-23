"""CatBox uploader module for SimiluBot."""
import logging
import os
import requests
from typing import Optional, Tuple

from similubot.progress.base import ProgressCallback

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

    def upload(self, file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a file to CatBox.

        Args:
            file_path: Path to the file to upload

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

            # Prepare request data
            data = {
                'reqtype': 'fileupload',
            }

            # Add user hash if available
            if self.user_hash:
                data['userhash'] = self.user_hash

            # Prepare file data
            files = {
                'fileToUpload': (
                    os.path.basename(file_path),
                    open(file_path, 'rb'),
                    'application/octet-stream'
                )
            }

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

            self.logger.info(f"Upload successful: {url}")

            return True, url, None

        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
        finally:
            # Close file if it was opened
            if 'files' in locals() and 'fileToUpload' in files:
                files['fileToUpload'][1].close()

    def upload_with_progress(
        self,
        file_path: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a file to Catbox with progress tracking.

        Args:
            file_path: Path to the file to upload
            progress_callback: Optional callback function for progress updates

        Returns:
            Tuple containing:
                - Success status (True/False)
                - File URL if successful, None otherwise
                - Error message if failed, None otherwise
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            return False, None, error_msg

        # Import here to avoid circular imports
        from similubot.progress.upload_tracker import UploadProgressTracker

        # Get file size for progress tracking
        file_size = os.path.getsize(file_path)

        # Create progress tracker
        progress_tracker = UploadProgressTracker("Catbox", file_size)
        if progress_callback:
            progress_tracker.add_callback(progress_callback)

        # Start progress tracking
        progress_tracker.start_upload(file_size)

        try:
            self.logger.info(f"Uploading file to Catbox: {file_path}")
            self.logger.debug(f"File size: {file_size} bytes")

            # Prepare the file for upload
            filename = os.path.basename(file_path)

            # Create a custom file-like object that tracks progress
            class ProgressFile:
                def __init__(self, file_obj, tracker):
                    self.file_obj = file_obj
                    self.tracker = tracker
                    self.bytes_read = 0

                def read(self, size=-1):
                    data = self.file_obj.read(size)
                    if data:
                        self.bytes_read += len(data)
                        # Update progress every 64KB to avoid too frequent updates
                        if self.bytes_read % (64 * 1024) == 0 or len(data) < size:
                            percentage = (self.bytes_read / file_size) * 100 if file_size > 0 else 0
                            self.tracker.update_progress(
                                bytes_uploaded=self.bytes_read,
                                percentage=percentage
                            )
                    return data

                def __getattr__(self, name):
                    return getattr(self.file_obj, name)

            with open(file_path, 'rb') as f:
                progress_file = ProgressFile(f, progress_tracker)

                files = {
                    'fileToUpload': (filename, progress_file, 'application/octet-stream')
                }

                data = {
                    'reqtype': 'fileupload'
                }

                # Make the upload request
                response = requests.post(
                    self.upload_url,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )

                # Ensure we've reported 100% progress
                progress_tracker.update_progress(
                    bytes_uploaded=file_size,
                    percentage=100.0
                )

                if response.status_code == 200:
                    file_url = response.text.strip()
                    if file_url.startswith('http'):
                        self.logger.info(f"Upload successful: {file_url}")
                        progress_tracker.complete_upload(file_url)
                        return True, file_url, None
                    else:
                        error_msg = f"Upload failed: {file_url}"
                        self.logger.error(error_msg)
                        progress_tracker.fail_upload(error_msg)
                        return False, None, error_msg
                else:
                    error_msg = f"Upload failed with status {response.status_code}: {response.text}"
                    self.logger.error(error_msg)
                    progress_tracker.fail_upload(error_msg)
                    return False, None, error_msg

        except requests.exceptions.Timeout:
            error_msg = f"Upload timed out after {self.timeout} seconds"
            self.logger.error(error_msg)
            progress_tracker.fail_upload(error_msg)
            return False, None, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(error_msg)
            progress_tracker.fail_upload(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            progress_tracker.fail_upload(error_msg)
            return False, None, error_msg

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
