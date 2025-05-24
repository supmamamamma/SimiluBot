"""Image generator module for SimiluBot."""
import asyncio
import io
import logging
import os
import tempfile
import time
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image

from similubot.generators.novelai_client import NovelAIClient
from similubot.progress.base import ProgressCallback
from similubot.progress.novelai_tracker import NovelAIProgressTracker

class ImageGenerator:
    """
    High-level image generator that coordinates NovelAI API calls
    with progress tracking and file management.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://image.novelai.net",
        timeout: int = 120,
        temp_dir: str = "./temp"
    ):
        """
        Initialize the image generator.
        
        Args:
            api_key: NovelAI API key
            base_url: NovelAI API base URL
            timeout: Request timeout in seconds
            temp_dir: Temporary directory for file operations
        """
        self.logger = logging.getLogger("similubot.generators.image_generator")
        self.temp_dir = temp_dir
        
        # Initialize NovelAI client
        self.client = NovelAIClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.logger.debug(f"Initialized image generator with temp dir: {self.temp_dir}")
    
    async def generate_image_with_progress(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        model: str = "nai-diffusion-3",
        progress_callback: Optional[ProgressCallback] = None,
        **parameters
    ) -> Tuple[bool, Optional[List[str]], Optional[str]]:
        """
        Generate images with progress tracking.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Optional negative prompt
            model: Model to use for generation
            progress_callback: Optional progress callback function
            **parameters: Additional generation parameters
            
        Returns:
            Tuple containing:
                - Success status (True/False)
                - List of file paths if successful, None otherwise
                - Error message if failed, None otherwise
        """
        # Create progress tracker
        progress_tracker = NovelAIProgressTracker()
        if progress_callback:
            progress_tracker.add_callback(progress_callback)
        
        # Start progress tracking
        progress_tracker.start()
        progress_tracker.start_generation(prompt, model, parameters)
        
        try:
            self.logger.info(f"Starting image generation: '{prompt[:100]}...'")
            
            # Update progress for API request
            progress_tracker.update_api_request()
            
            # Start generation in thread to avoid blocking
            generation_task = asyncio.create_task(
                self._generate_with_progress_updates(
                    prompt, negative_prompt, model, progress_tracker, **parameters
                )
            )
            
            # Wait for generation to complete
            success, image_data_list, error = await generation_task
            
            if not success:
                progress_tracker.fail_generation(error or "Unknown error")
                return False, None, error
            
            # Save images to temporary files
            file_paths = []
            for i, image_data in enumerate(image_data_list):
                try:
                    file_path = await self._save_image_to_temp(image_data, i)
                    file_paths.append(file_path)
                    self.logger.debug(f"Saved image {i+1} to: {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to save image {i+1}: {e}")
                    # Clean up any files we've already saved
                    for path in file_paths:
                        try:
                            os.remove(path)
                        except:
                            pass
                    error_msg = f"Failed to save generated images: {str(e)}"
                    progress_tracker.fail_generation(error_msg)
                    return False, None, error_msg
            
            progress_tracker.complete_generation(len(file_paths))
            self.logger.info(f"Successfully generated and saved {len(file_paths)} image(s)")
            
            return True, file_paths, None
            
        except Exception as e:
            error_msg = f"Image generation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            progress_tracker.fail_generation(error_msg)
            return False, None, error_msg
        finally:
            progress_tracker.stop()
    
    async def _generate_with_progress_updates(
        self,
        prompt: str,
        negative_prompt: Optional[str],
        model: str,
        progress_tracker: NovelAIProgressTracker,
        **parameters
    ) -> Tuple[bool, Optional[List[bytes]], Optional[str]]:
        """
        Generate images with periodic progress updates.
        
        Args:
            prompt: Text prompt
            negative_prompt: Optional negative prompt
            model: Model name
            progress_tracker: Progress tracker instance
            **parameters: Generation parameters
            
        Returns:
            Tuple of (success, image_data_list, error)
        """
        # Start progress update task
        progress_task = asyncio.create_task(
            self._update_progress_periodically(progress_tracker)
        )
        
        try:
            # Run generation in thread pool
            success, image_data_list, error = await asyncio.to_thread(
                self.client.generate_image,
                prompt,
                negative_prompt,
                model,
                **parameters
            )
            
            return success, image_data_list, error
            
        finally:
            # Cancel progress updates
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
    
    async def _update_progress_periodically(
        self,
        progress_tracker: NovelAIProgressTracker,
        interval: float = 2.0
    ) -> None:
        """
        Update progress periodically during generation.
        
        Args:
            progress_tracker: Progress tracker instance
            interval: Update interval in seconds
        """
        start_time = time.time()
        
        try:
            while True:
                await asyncio.sleep(interval)
                elapsed = time.time() - start_time
                progress_tracker.update_generation_progress(elapsed)
        except asyncio.CancelledError:
            pass
    
    async def _save_image_to_temp(self, image_data: bytes, index: int = 0) -> str:
        """
        Save image data to a temporary file.
        
        Args:
            image_data: Image data as bytes
            index: Image index for filename
            
        Returns:
            Path to saved file
            
        Raises:
            Exception: If saving fails
        """
        # Determine file extension based on image format
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                format_ext = img.format.lower() if img.format else 'png'
                if format_ext == 'jpeg':
                    format_ext = 'jpg'
        except Exception:
            # Default to PNG if we can't determine format
            format_ext = 'png'
        
        # Generate unique filename
        timestamp = int(time.time() * 1000)  # Millisecond timestamp
        filename = f"novelai_generated_{timestamp}_{index}.{format_ext}"
        file_path = os.path.join(self.temp_dir, filename)
        
        # Save image data
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Verify file was saved correctly
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            raise Exception(f"Failed to save image to {file_path}")
        
        return file_path
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test connection to NovelAI API.
        
        Returns:
            Tuple of (success, error_message)
        """
        return self.client.test_connection()
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get information about the configured client.
        
        Returns:
            Dictionary with client information
        """
        return {
            'base_url': self.client.base_url,
            'timeout': self.client.timeout,
            'temp_dir': self.temp_dir
        }
    
    def cleanup_temp_files(self, file_paths: List[str]) -> None:
        """
        Clean up temporary files.
        
        Args:
            file_paths: List of file paths to clean up
        """
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.logger.debug(f"Removed temporary file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove temporary file {file_path}: {e}")
    
    async def generate_and_upload(
        self,
        prompt: str,
        uploader,
        negative_prompt: Optional[str] = None,
        model: str = "nai-diffusion-3",
        progress_callback: Optional[ProgressCallback] = None,
        **parameters
    ) -> Tuple[bool, Optional[List[str]], Optional[str]]:
        """
        Generate images and upload them using the provided uploader.
        
        Args:
            prompt: Text prompt for image generation
            uploader: Uploader instance (CatboxUploader or DiscordUploader)
            negative_prompt: Optional negative prompt
            model: Model to use for generation
            progress_callback: Optional progress callback function
            **parameters: Additional generation parameters
            
        Returns:
            Tuple containing:
                - Success status (True/False)
                - List of upload URLs/results if successful, None otherwise
                - Error message if failed, None otherwise
        """
        # Generate images
        success, file_paths, error = await self.generate_image_with_progress(
            prompt, negative_prompt, model, progress_callback, **parameters
        )
        
        if not success or not file_paths:
            return False, None, error
        
        # Create progress tracker for upload
        progress_tracker = NovelAIProgressTracker()
        if progress_callback:
            progress_tracker.add_callback(progress_callback)
        
        try:
            # Upload images
            upload_results = []
            
            for i, file_path in enumerate(file_paths):
                progress_tracker.start_upload(f"service ({i+1}/{len(file_paths)})")
                
                # Upload using the provided uploader
                if hasattr(uploader, 'upload_with_progress'):
                    upload_success, result, upload_error = await asyncio.to_thread(
                        uploader.upload_with_progress, file_path, progress_callback
                    )
                else:
                    upload_success, result, upload_error = await asyncio.to_thread(
                        uploader.upload, file_path
                    )
                
                if not upload_success:
                    progress_tracker.fail_upload(upload_error or "Upload failed")
                    return False, None, upload_error
                
                upload_results.append(result)
            
            progress_tracker.complete_upload("All files uploaded")
            return True, upload_results, None
            
        finally:
            # Clean up temporary files
            self.cleanup_temp_files(file_paths)
