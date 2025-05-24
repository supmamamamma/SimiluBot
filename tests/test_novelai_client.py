"""Tests for the NovelAI client module."""
import io
import json
import pytest
import zipfile
from unittest.mock import patch, MagicMock, Mock

from similubot.generators.novelai_client import NovelAIClient

class TestNovelAIClient:
    """Test cases for the NovelAI client."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key"
        self.client = NovelAIClient(self.api_key)

    def test_init(self):
        """Test client initialization."""
        assert self.client.api_key == self.api_key
        assert self.client.base_url == "https://image.novelai.net"
        assert self.client.timeout == 120
        assert "Authorization" in self.client.session.headers
        assert self.client.session.headers["Authorization"] == f"Bearer {self.api_key}"

    def test_init_custom_params(self):
        """Test client initialization with custom parameters."""
        custom_url = "https://custom.api.url"
        custom_timeout = 60

        client = NovelAIClient(
            api_key=self.api_key,
            base_url=custom_url,
            timeout=custom_timeout
        )

        assert client.base_url == custom_url
        assert client.timeout == custom_timeout

    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        correlation_id = self.client._generate_correlation_id()
        assert len(correlation_id) == 6
        assert correlation_id.isalnum()

    def test_validate_parameters_valid(self):
        """Test parameter validation with valid parameters."""
        params = {
            'prompt': 'test prompt',
            'width': 832,
            'height': 1216,
            'steps': 28,
            'scale': 5.0,
            'n_samples': 1,
            'seed': 12345
        }

        validated = self.client._validate_parameters(params)

        assert validated['prompt'] == 'test prompt'
        assert validated['width'] == 832
        assert validated['height'] == 1216
        assert validated['steps'] == 28
        assert validated['scale'] == 5.0
        assert validated['n_samples'] == 1
        assert validated['seed'] == 12345
        assert 'sampler' in validated

    def test_validate_parameters_empty_prompt(self):
        """Test parameter validation with empty prompt."""
        params = {'prompt': ''}

        with pytest.raises(ValueError, match="Prompt is required"):
            self.client._validate_parameters(params)

    def test_validate_parameters_invalid_dimensions(self):
        """Test parameter validation with invalid dimensions."""
        params = {'prompt': 'test', 'width': 50}  # Too small

        with pytest.raises(ValueError, match="Width must be an integer"):
            self.client._validate_parameters(params)

    def test_validate_parameters_dimension_rounding(self):
        """Test parameter validation rounds dimensions to multiples of 64."""
        params = {'prompt': 'test', 'width': 850, 'height': 1200}

        validated = self.client._validate_parameters(params)

        assert validated['width'] == 832  # 850 rounded down to nearest 64
        assert validated['height'] == 1152  # 1200 rounded down to nearest 64

    def test_validate_parameters_random_seed(self):
        """Test parameter validation with random seed."""
        params = {'prompt': 'test', 'seed': -1}

        validated = self.client._validate_parameters(params)

        assert validated['seed'] >= 0
        assert validated['seed'] < 2**32

    @patch('requests.Session.post')
    def test_generate_image_success(self, mock_post):
        """Test successful image generation."""
        # Create mock ZIP response
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('image_0.png', b'fake_image_data')
        zip_data = zip_buffer.getvalue()

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = zip_data
        mock_post.return_value = mock_response

        # Test generation
        success, images, error = self.client.generate_image("test prompt")

        # Verify results
        assert success is True
        assert len(images) == 1
        assert images[0] == b'fake_image_data'
        assert error is None

        # Verify API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == f"{self.client.base_url}/ai/generate-image"
        assert 'json' in kwargs

        payload = kwargs['json']
        assert payload['input'] == "test prompt"
        assert payload['model'] == "nai-diffusion-3"
        assert payload['action'] == "generate"
        assert 'parameters' in payload

    @patch('requests.Session.post')
    def test_generate_image_auth_failure(self, mock_post):
        """Test image generation with authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        success, images, error = self.client.generate_image("test prompt")

        assert success is False
        assert images is None
        assert "Authentication failed" in error

    @patch('requests.Session.post')
    def test_generate_image_rate_limit(self, mock_post):
        """Test image generation with rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        success, images, error = self.client.generate_image("test prompt")

        assert success is False
        assert images is None
        assert "Rate limited" in error

    @patch('requests.Session.post')
    def test_generate_image_server_error(self, mock_post):
        """Test image generation with server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'message': 'Internal server error'}
        mock_post.return_value = mock_response

        success, images, error = self.client.generate_image("test prompt")

        assert success is False
        assert images is None
        assert "HTTP 500" in error
        assert "Internal server error" in error

    @patch('requests.Session.post')
    def test_generate_image_timeout(self, mock_post):
        """Test image generation with timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        success, images, error = self.client.generate_image("test prompt")

        assert success is False
        assert images is None
        assert "timed out" in error

    @patch('requests.Session.post')
    def test_generate_image_network_error(self, mock_post):
        """Test image generation with network error."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        success, images, error = self.client.generate_image("test prompt")

        assert success is False
        assert images is None
        assert "Network error" in error

    def test_extract_images_from_zip(self):
        """Test extracting images from ZIP data."""
        # Create test ZIP with multiple images
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('image_0.png', b'image_data_1')
            zip_file.writestr('image_1.jpg', b'image_data_2')
            zip_file.writestr('metadata.txt', b'not_an_image')  # Should be ignored
        zip_data = zip_buffer.getvalue()

        images = self.client._extract_images_from_zip(zip_data)

        assert len(images) == 2
        assert b'image_data_1' in images
        assert b'image_data_2' in images

    def test_extract_images_from_zip_empty(self):
        """Test extracting images from ZIP with no images."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('metadata.txt', b'not_an_image')
        zip_data = zip_buffer.getvalue()

        images = self.client._extract_images_from_zip(zip_data)

        assert len(images) == 0

    @patch('requests.Session.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        success, error = self.client.test_connection()

        assert success is True
        assert error is None

    @patch('requests.Session.get')
    def test_test_connection_auth_failure(self, mock_get):
        """Test connection test with authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        success, error = self.client.test_connection()

        assert success is False
        assert "Authentication failed" in error

    @patch('requests.Session.get')
    def test_test_connection_timeout(self, mock_get):
        """Test connection test with timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        success, error = self.client.test_connection()

        assert success is False
        assert "timed out" in error
