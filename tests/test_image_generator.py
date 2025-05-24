"""Tests for the image generator module."""
import asyncio
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from similubot.generators.image_generator import ImageGenerator

class TestImageGenerator:
    """Test cases for the image generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key"
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ImageGenerator(
            api_key=self.api_key,
            temp_dir=self.temp_dir
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test generator initialization."""
        assert self.generator.temp_dir == self.temp_dir
        assert self.generator.client.api_key == self.api_key
        assert os.path.exists(self.temp_dir)

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_generate_image_with_progress_success(self, mock_image_open, mock_generate):
        """Test successful image generation with progress."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_png_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        # Mock progress callback
        progress_callback = MagicMock()

        # Test generation
        success, file_paths, error = await self.generator.generate_image_with_progress(
            prompt="test prompt",
            progress_callback=progress_callback
        )

        # Verify results
        assert success is True
        assert file_paths is not None
        assert len(file_paths) == 1
        assert file_paths[0].endswith('.png')
        assert os.path.exists(file_paths[0])
        assert error is None

        # Verify file content
        with open(file_paths[0], 'rb') as f:
            assert f.read() == fake_image_data

        # Verify API call
        mock_generate.assert_called_once()
        args, _ = mock_generate.call_args
        assert args[0] == "test prompt"  # prompt
        assert args[1] is None  # negative_prompt
        assert args[2] == "nai-diffusion-3"  # model

        # Verify progress callback was called
        assert progress_callback.called

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @pytest.mark.asyncio
    async def test_generate_image_with_progress_api_failure(self, mock_generate):
        """Test image generation with API failure."""
        # Mock API failure
        mock_generate.return_value = (False, None, "API error")

        success, file_paths, error = await self.generator.generate_image_with_progress(
            prompt="test prompt"
        )

        assert success is False
        assert file_paths is None
        assert error == "API error"

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @patch('builtins.open')
    @pytest.mark.asyncio
    async def test_generate_image_with_progress_save_failure(self, mock_open, mock_image_open, mock_generate):
        """Test image generation with file save failure."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_png_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        # Mock file open to raise an exception
        mock_open.side_effect = PermissionError("Permission denied")

        success, file_paths, error = await self.generator.generate_image_with_progress(
            prompt="test prompt"
        )

        assert success is False
        assert file_paths is None
        assert error is not None
        assert "Failed to save generated images" in error

    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_save_image_to_temp(self, mock_image_open):
        """Test saving image data to temporary file."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'JPEG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        fake_image_data = b'fake_jpeg_data'

        file_path = await self.generator._save_image_to_temp(fake_image_data, 0)

        assert file_path.endswith('.jpg')
        assert os.path.exists(file_path)

        with open(file_path, 'rb') as f:
            assert f.read() == fake_image_data

    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_save_image_to_temp_unknown_format(self, mock_image_open):
        """Test saving image with unknown format defaults to PNG."""
        # Mock image format detection failure
        mock_image_open.side_effect = Exception("Cannot determine format")

        fake_image_data = b'fake_image_data'

        file_path = await self.generator._save_image_to_temp(fake_image_data, 0)

        assert file_path.endswith('.png')
        assert os.path.exists(file_path)

    def test_test_connection(self):
        """Test connection testing."""
        with patch.object(self.generator.client, 'test_connection') as mock_test:
            mock_test.return_value = (True, None)

            success, error = self.generator.test_connection()

            assert success is True
            assert error is None
            mock_test.assert_called_once()

    def test_get_client_info(self):
        """Test getting client information."""
        info = self.generator.get_client_info()

        assert 'base_url' in info
        assert 'timeout' in info
        assert 'temp_dir' in info
        assert info['temp_dir'] == self.temp_dir

    def test_cleanup_temp_files(self):
        """Test cleaning up temporary files."""
        # Create test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write("test content")
            test_files.append(file_path)

        # Verify files exist
        for file_path in test_files:
            assert os.path.exists(file_path)

        # Clean up files
        self.generator.cleanup_temp_files(test_files)

        # Verify files are deleted
        for file_path in test_files:
            assert not os.path.exists(file_path)

    def test_cleanup_temp_files_nonexistent(self):
        """Test cleaning up non-existent files doesn't raise errors."""
        nonexistent_files = [
            "/path/that/does/not/exist.txt",
            os.path.join(self.temp_dir, "nonexistent.txt")
        ]

        # Should not raise any exceptions
        self.generator.cleanup_temp_files(nonexistent_files)

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_generate_and_upload_success(self, mock_image_open, mock_generate):
        """Test successful generation and upload."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_png_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        # Mock uploader
        mock_uploader = MagicMock()
        mock_uploader.upload_with_progress = MagicMock(return_value=(True, "http://example.com/image.png", None))

        success, results, error = await self.generator.generate_and_upload(
            prompt="test prompt",
            uploader=mock_uploader
        )

        assert success is True
        assert results is not None
        assert len(results) == 1
        assert results[0] == "http://example.com/image.png"
        assert error is None

        # Verify uploader was called
        mock_uploader.upload_with_progress.assert_called_once()

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @pytest.mark.asyncio
    async def test_generate_and_upload_generation_failure(self, mock_generate):
        """Test generation and upload with generation failure."""
        # Mock generation failure
        mock_generate.return_value = (False, None, "Generation failed")

        mock_uploader = MagicMock()

        success, results, error = await self.generator.generate_and_upload(
            prompt="test prompt",
            uploader=mock_uploader
        )

        assert success is False
        assert results is None
        assert error == "Generation failed"

        # Verify uploader was not called
        assert not mock_uploader.upload_with_progress.called

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_generate_and_upload_upload_failure(self, mock_image_open, mock_generate):
        """Test generation and upload with upload failure."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_png_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        # Mock uploader failure
        mock_uploader = MagicMock()
        mock_uploader.upload_with_progress = MagicMock(return_value=(False, None, "Upload failed"))

        success, results, error = await self.generator.generate_and_upload(
            prompt="test prompt",
            uploader=mock_uploader
        )

        assert success is False
        assert results is None
        assert error == "Upload failed"

    # Multi-character functionality tests
    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_generate_image_with_progress_multicharacter_success(self, mock_image_open, mock_generate):
        """Test successful multi-character image generation with progress."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_multichar_png_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        # Mock progress callback
        progress_callback = MagicMock()

        # Test multi-character generation
        character_args = ["char1:[girl with blue hair]", "char2:[boy with red eyes]"]
        success, file_paths, error = await self.generator.generate_image_with_progress(
            prompt="fantasy scene",
            progress_callback=progress_callback,
            character_args=character_args
        )

        # Verify results
        assert success is True
        assert file_paths is not None
        assert len(file_paths) == 1
        assert file_paths[0].endswith('.png')
        assert os.path.exists(file_paths[0])
        assert error is None

        # Verify file content
        with open(file_paths[0], 'rb') as f:
            assert f.read() == fake_image_data

        # Verify API call with character arguments
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        assert args[0] == "fantasy scene"  # prompt
        assert args[1] is None  # negative_prompt
        assert args[2] == "nai-diffusion-3"  # model
        assert args[3] == character_args  # character_args

        # Verify progress callback was called
        assert progress_callback.called

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @pytest.mark.asyncio
    async def test_generate_image_with_progress_multicharacter_invalid_params(self, mock_generate):
        """Test multi-character generation with invalid character parameters."""
        # Mock API failure due to invalid character parameters
        mock_generate.return_value = (False, None, "Character parameter error: Invalid character syntax")

        character_args = ["char1:missing_brackets", "char2:[valid description]"]
        success, file_paths, error = await self.generator.generate_image_with_progress(
            prompt="fantasy scene",
            character_args=character_args
        )

        assert success is False
        assert file_paths is None
        assert error == "Character parameter error: Invalid character syntax"

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_generate_image_with_progress_character_args_none(self, mock_image_open, mock_generate):
        """Test generation with None character_args (backward compatibility)."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_single_char_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        success, file_paths, error = await self.generator.generate_image_with_progress(
            prompt="simple scene",
            character_args=None
        )

        # Verify results
        assert success is True
        assert file_paths is not None
        assert len(file_paths) == 1
        assert error is None

        # Verify API call with None character_args
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        assert args[3] is None  # character_args should be None

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_generate_image_with_progress_character_args_empty(self, mock_image_open, mock_generate):
        """Test generation with empty character_args list."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_single_char_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        success, file_paths, error = await self.generator.generate_image_with_progress(
            prompt="simple scene",
            character_args=[]
        )

        # Verify results
        assert success is True
        assert file_paths is not None
        assert len(file_paths) == 1
        assert error is None

        # Verify API call with empty character_args
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        assert args[3] == []  # character_args should be empty list

    @patch('similubot.generators.novelai_client.NovelAIClient.generate_image')
    @patch('PIL.Image.open')
    @pytest.mark.asyncio
    async def test_generate_and_upload_multicharacter_success(self, mock_image_open, mock_generate):
        """Test successful multi-character generation and upload."""
        # Mock image format detection
        mock_img = MagicMock()
        mock_img.format = 'PNG'
        mock_image_open.return_value.__enter__.return_value = mock_img

        # Mock successful generation
        fake_image_data = b'fake_multichar_png_data'
        mock_generate.return_value = (True, [fake_image_data], None)

        # Mock uploader
        mock_uploader = MagicMock()
        mock_uploader.upload_with_progress = MagicMock(return_value=(True, "http://example.com/multichar.png", None))

        character_args = ["char1:[girl with blue hair]", "char2:[boy with red eyes]"]
        success, results, error = await self.generator.generate_and_upload(
            prompt="fantasy scene",
            uploader=mock_uploader,
            character_args=character_args
        )

        assert success is True
        assert results is not None
        assert len(results) == 1
        assert results[0] == "http://example.com/multichar.png"
        assert error is None

        # Verify uploader was called
        mock_uploader.upload_with_progress.assert_called_once()

        # Verify generation was called with character args
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        assert args[3] == character_args  # character_args passed through
