"""Tests for the NovelAI progress tracker module."""
import time
import pytest
from unittest.mock import MagicMock

from similubot.progress.novelai_tracker import NovelAIProgressTracker

class TestNovelAIProgressTracker:
    """Test cases for the NovelAI progress tracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = NovelAIProgressTracker()

    def test_init(self):
        """Test tracker initialization."""
        assert self.tracker.prompt is None
        assert self.tracker.model is None
        assert self.tracker.parameters == {}
        assert self.tracker.generation_start_time is None
        assert self.tracker.estimated_duration == 30.0
        assert not self.tracker.is_active

    def test_start_generation(self):
        """Test starting generation tracking."""
        prompt = "test prompt"
        model = "nai-diffusion-3"
        parameters = {"steps": 20, "n_samples": 2}

        # Mock callback
        callback = MagicMock()
        self.tracker.add_callback(callback)

        self.tracker.start_generation(prompt, model, parameters)

        assert self.tracker.prompt == prompt
        assert self.tracker.model == model
        assert self.tracker.parameters == parameters
        assert self.tracker.generation_start_time is not None

        # Check estimated duration calculation
        # 20 steps * 2 samples * 0.8 + 10 = 42 seconds
        assert self.tracker.estimated_duration == 42.0

        # Verify callback was called
        callback.assert_called()
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'preparing'
        assert progress_info.percentage == 0.0
        assert 'Preparing image generation' in progress_info.message

    def test_start_generation_default_duration(self):
        """Test starting generation with default duration estimation."""
        self.tracker.start_generation("test", "model", {})

        # Should use minimum duration of 15 seconds (28 default steps * 1 sample * 0.8 + 10 = 32.4)
        assert self.tracker.estimated_duration > 15.0

    def test_update_api_request(self):
        """Test API request update."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        self.tracker.update_api_request()

        callback.assert_called()
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'generating'
        assert progress_info.percentage == 10.0
        assert 'Generating image with AI' in progress_info.message

    def test_update_generation_progress(self):
        """Test generation progress updates."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        # Start generation to set start time
        self.tracker.start_generation("test", "model", {"steps": 28})
        callback.reset_mock()

        # Test progress at different stages
        self.tracker.update_generation_progress(5.0)  # Early stage
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'generating'
        assert 10.0 < progress_info.percentage < 30.0
        assert 'analyzing your prompt' in progress_info.message

        callback.reset_mock()
        self.tracker.update_generation_progress(15.0)  # Mid stage
        progress_info = callback.call_args[0][0]
        assert 30.0 <= progress_info.percentage < 60.0
        assert 'Generating image details' in progress_info.message

        callback.reset_mock()
        self.tracker.update_generation_progress(25.0)  # Late stage
        progress_info = callback.call_args[0][0]
        assert 60.0 <= progress_info.percentage < 80.0
        assert 'Adding final touches' in progress_info.message

        callback.reset_mock()
        self.tracker.update_generation_progress(35.0)  # Very late stage
        progress_info = callback.call_args[0][0]
        assert progress_info.percentage >= 80.0
        assert 'Almost ready' in progress_info.message

    def test_update_generation_progress_no_start_time(self):
        """Test generation progress update without start time."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        # Should not crash or call callback
        self.tracker.update_generation_progress(10.0)
        callback.assert_not_called()

    def test_complete_generation(self):
        """Test generation completion."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        # Start generation to set start time
        self.tracker.start_generation("test", "model", {})
        callback.reset_mock()

        self.tracker.complete_generation(2)

        callback.assert_called()
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'complete'
        assert progress_info.percentage == 100.0
        assert 'Generated 2 images' in progress_info.message

    def test_complete_generation_single_image(self):
        """Test generation completion with single image."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        self.tracker.start_generation("test", "model", {})
        callback.reset_mock()

        self.tracker.complete_generation(1)

        progress_info = callback.call_args[0][0]
        assert 'Generated 1 image!' in progress_info.message  # No 's' for single

    def test_fail_generation(self):
        """Test generation failure."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        self.tracker.start_generation("test", "model", {})
        callback.reset_mock()

        error_msg = "API error occurred"
        self.tracker.fail_generation(error_msg)

        callback.assert_called()
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'failed'
        assert progress_info.percentage == 0.0
        assert error_msg in progress_info.message

    def test_start_upload(self):
        """Test upload start tracking."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        service = "catbox"
        self.tracker.start_upload(service)

        callback.assert_called()
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'uploading'
        assert progress_info.percentage == 95.0
        assert service in progress_info.message

    def test_complete_upload(self):
        """Test upload completion."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        url = "https://example.com/image.png"
        self.tracker.complete_upload(url)

        callback.assert_called()
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'complete'
        assert progress_info.percentage == 100.0
        assert 'Upload complete' in progress_info.message

    def test_fail_upload(self):
        """Test upload failure."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        error_msg = "Upload failed"
        self.tracker.fail_upload(error_msg)

        callback.assert_called()
        progress_info = callback.call_args[0][0]
        assert progress_info.details['stage'] == 'failed'
        assert progress_info.percentage == 95.0
        assert error_msg in progress_info.message

    def test_update_progress_with_timing(self):
        """Test progress update includes timing information."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        # Start generation and wait a bit
        self.tracker.start_generation("test", "model", {"steps": 20})
        time.sleep(0.1)  # Small delay
        callback.reset_mock()

        self.tracker.update_generation_progress(2.0)

        progress_info = callback.call_args[0][0]
        assert 'elapsed_time' in progress_info.details
        assert 'estimated_remaining' in progress_info.details
        assert progress_info.details['elapsed_time'] > 0
        assert progress_info.details['estimated_remaining'] >= 0

    def test_get_current_status(self):
        """Test getting current status."""
        # Test initial status
        status = self.tracker.get_current_status()
        assert status['prompt'] is None
        assert status['model'] is None
        assert status['parameters'] == {}
        assert not status['is_active']
        assert 'elapsed_time' not in status

        # Test status after starting generation
        self.tracker.start_generation("test prompt", "test-model", {"steps": 20})
        status = self.tracker.get_current_status()

        assert status['prompt'] == "test prompt"
        assert status['model'] == "test-model"
        assert status['parameters'] == {"steps": 20}
        assert 'elapsed_time' in status
        assert 'estimated_duration' in status

    def test_callback_exception_handling(self):
        """Test that callback exceptions don't crash the tracker."""
        # Create a callback that raises an exception
        bad_callback = MagicMock(side_effect=Exception("Callback error"))
        good_callback = MagicMock()

        self.tracker.add_callback(bad_callback)
        self.tracker.add_callback(good_callback)

        # Should not raise exception
        self.tracker.start_generation("test", "model", {})

        # Good callback should still be called
        good_callback.assert_called()
        bad_callback.assert_called()

    def test_progress_data_structure(self):
        """Test that progress data contains all expected fields."""
        callback = MagicMock()
        self.tracker.add_callback(callback)

        self.tracker.start_generation("test prompt", "test-model", {"steps": 20})

        progress_info = callback.call_args[0][0]

        # Check required fields in details
        required_fields = ['stage', 'prompt', 'model', 'parameters']
        for field in required_fields:
            assert field in progress_info.details

        # Check main progress info fields
        assert hasattr(progress_info, 'message')
        assert hasattr(progress_info, 'percentage')

        assert progress_info.details['prompt'] == "test prompt"
        assert progress_info.details['model'] == "test-model"
        assert progress_info.details['parameters'] == {"steps": 20}
