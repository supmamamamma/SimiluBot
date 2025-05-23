"""MEGA downloader module for SimiluBot."""
import logging
import os
import re
from typing import Optional, Tuple
from mega import Mega

class MegaDownloader:
    """
    Downloader for MEGA links.
    
    Handles downloading files from MEGA links to a local directory.
    """
    
    # Regular expression to match MEGA links
    MEGA_LINK_PATTERN = r'https?://mega\.nz/(?:file|/#!?)[^/\s]+'
    
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
        return bool(re.match(self.MEGA_LINK_PATTERN, url))
    
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
        Download a file from a MEGA link.
        
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
            
            # Download the file
            file_path = self.mega_client.download_url(url, dest_path=self.temp_dir)
            
            if not file_path or not os.path.exists(file_path):
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
