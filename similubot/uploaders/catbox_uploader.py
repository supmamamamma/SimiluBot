"""CatBox uploader module for SimiluBot."""
import logging
import os
import requests
from typing import Optional, Tuple

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
