"""Progress tracker for NovelAI image generation operations."""
import logging
import time
from typing import Optional, Dict, Any, List

from similubot.progress.base import ProgressCallback, ProgressInfo, ProgressStatus

class NovelAIProgressTracker:
    """
    Progress tracker for NovelAI image generation operations.

    Tracks the progress of image generation requests and provides
    real-time updates to Discord.
    """

    def __init__(self):
        """Initialize the NovelAI progress tracker."""
        self.logger = logging.getLogger("similubot.progress.novelai_tracker")

        # Callback management
        self.callbacks: List[ProgressCallback] = []
        self.is_active: bool = False

        # Generation state
        self.prompt: Optional[str] = None
        self.model: Optional[str] = None
        self.parameters: Dict[str, Any] = {}
        self.generation_start_time: Optional[float] = None
        self.estimated_duration: float = 30.0  # Default estimate in seconds

        self.logger.debug("Initialized NovelAI progress tracker")

    def add_callback(self, callback: ProgressCallback) -> None:
        """
        Add a progress callback.

        Args:
            callback: Function to call when progress updates
        """
        self.callbacks.append(callback)

    def start(self) -> None:
        """Start the progress tracker."""
        self.is_active = True

    def stop(self) -> None:
        """Stop the progress tracker."""
        self.is_active = False

    def start_generation(
        self,
        prompt: str,
        model: str = "nai-diffusion-3",
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Start tracking image generation progress.

        Args:
            prompt: The generation prompt
            model: The model being used
            parameters: Generation parameters
        """
        self.prompt = prompt
        self.model = model
        self.parameters = parameters or {}
        self.generation_start_time = time.time()

        # Estimate duration based on parameters
        steps = self.parameters.get('steps', 28)
        n_samples = self.parameters.get('n_samples', 1)

        # Rough estimation: ~1 second per step per sample, plus overhead
        self.estimated_duration = max(15.0, (steps * n_samples * 0.8) + 10)

        self.logger.info(f"Started generation tracking for prompt: '{prompt[:50]}...'")
        self.logger.debug(f"Model: {model}, Parameters: {parameters}")
        self.logger.debug(f"Estimated duration: {self.estimated_duration:.1f}s")

        # Send initial progress update
        self._update_progress(
            stage="preparing",
            message="🎨 Preparing image generation...",
            percentage=0.0
        )

    def update_api_request(self) -> None:
        """Update progress when API request is sent."""
        self.logger.debug("API request sent")
        self._update_progress(
            stage="generating",
            message="🔄 Generating image with AI...",
            percentage=10.0
        )

    def update_generation_progress(self, elapsed_time: float) -> None:
        """
        Update generation progress based on elapsed time.

        Args:
            elapsed_time: Time elapsed since generation started
        """
        if not self.generation_start_time:
            return

        # Calculate progress based on estimated duration
        progress_ratio = min(elapsed_time / self.estimated_duration, 0.9)  # Cap at 90%
        percentage = 10.0 + (progress_ratio * 80.0)  # 10% to 90%

        # Create dynamic message based on progress
        if percentage < 30:
            message = "🎨 AI is analyzing your prompt..."
        elif percentage < 60:
            message = "🖼️ Generating image details..."
        elif percentage < 80:
            message = "✨ Adding final touches..."
        else:
            message = "🔄 Almost ready..."

        self._update_progress(
            stage="generating",
            message=message,
            percentage=percentage
        )

    def complete_generation(self, image_count: int) -> None:
        """
        Mark generation as complete.

        Args:
            image_count: Number of images generated
        """
        elapsed_time = time.time() - self.generation_start_time if self.generation_start_time else 0

        self.logger.info(f"Generation completed in {elapsed_time:.1f}s, {image_count} image(s)")

        message = f"✅ Generated {image_count} image{'s' if image_count != 1 else ''}!"
        self._update_progress(
            stage="complete",
            message=message,
            percentage=100.0
        )

    def fail_generation(self, error: str) -> None:
        """
        Mark generation as failed.

        Args:
            error: Error message
        """
        elapsed_time = time.time() - self.generation_start_time if self.generation_start_time else 0

        self.logger.error(f"Generation failed after {elapsed_time:.1f}s: {error}")

        self._update_progress(
            stage="failed",
            message=f"❌ Generation failed: {error}",
            percentage=0.0
        )

    def start_upload(self, service: str) -> None:
        """
        Start tracking upload progress.

        Args:
            service: Upload service name
        """
        self.logger.debug(f"Starting upload to {service}")
        self._update_progress(
            stage="uploading",
            message=f"📤 Uploading to {service}...",
            percentage=95.0
        )

    def complete_upload(self, url: str) -> None:
        """
        Mark upload as complete.

        Args:
            url: URL of uploaded file
        """
        self.logger.info(f"Upload completed: {url}")
        self._update_progress(
            stage="complete",
            message="✅ Upload complete!",
            percentage=100.0
        )

    def fail_upload(self, error: str) -> None:
        """
        Mark upload as failed.

        Args:
            error: Error message
        """
        self.logger.error(f"Upload failed: {error}")
        self._update_progress(
            stage="failed",
            message=f"❌ Upload failed: {error}",
            percentage=95.0
        )

    def _update_progress(
        self,
        stage: str,
        message: str,
        percentage: float,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send progress update to all registered callbacks.

        Args:
            stage: Current operation stage
            message: Progress message
            percentage: Completion percentage (0-100)
            details: Additional details dictionary
        """
        # Map stage to ProgressStatus
        status_map = {
            'preparing': ProgressStatus.STARTING,
            'generating': ProgressStatus.IN_PROGRESS,
            'uploading': ProgressStatus.IN_PROGRESS,
            'complete': ProgressStatus.COMPLETED,
            'failed': ProgressStatus.FAILED
        }

        status = status_map.get(stage, ProgressStatus.IN_PROGRESS)

        # Calculate ETA if we have timing information
        eta = None
        if self.generation_start_time and stage == "generating":
            elapsed = time.time() - self.generation_start_time
            if elapsed > 0 and self.estimated_duration > elapsed:
                eta = self.estimated_duration - elapsed

        # Create additional details
        progress_details = {
            'stage': stage,
            'prompt': self.prompt,
            'model': self.model,
            'parameters': self.parameters
        }

        if details:
            progress_details.update(details)

        # Add timing information
        if self.generation_start_time:
            elapsed = time.time() - self.generation_start_time
            progress_details['elapsed_time'] = elapsed

            if stage == "generating" and elapsed > 0:
                remaining = max(0, self.estimated_duration - elapsed)
                progress_details['estimated_remaining'] = remaining

        # Create ProgressInfo object
        progress_info = ProgressInfo(
            operation="AI Image Generation",
            status=status,
            percentage=percentage,
            message=message,
            eta=eta,
            details=progress_details
        )

        self.logger.debug(f"Progress update: {stage} - {percentage:.1f}% - {message}")

        # Send to all callbacks
        for callback in self.callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")

    def get_current_status(self) -> Dict[str, Any]:
        """
        Get current status information.

        Returns:
            Dictionary containing current status
        """
        status = {
            'prompt': self.prompt,
            'model': self.model,
            'parameters': self.parameters,
            'is_active': self.is_active
        }

        if self.generation_start_time:
            elapsed = time.time() - self.generation_start_time
            status['elapsed_time'] = elapsed
            status['estimated_duration'] = self.estimated_duration

        return status
