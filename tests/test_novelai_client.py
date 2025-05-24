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

    def test_validate_parameters_invalid_sampler(self):
        """Test parameter validation with invalid sampler."""
        params = {'prompt': 'test', 'sampler': 'invalid_sampler'}

        with pytest.raises(ValueError, match="Sampler must be one of"):
            self.client._validate_parameters(params)

    def test_validate_parameters_invalid_noise_schedule(self):
        """Test parameter validation with invalid noise schedule."""
        params = {'prompt': 'test', 'noise_schedule': 'invalid_schedule'}

        with pytest.raises(ValueError, match="noise_schedule must be one of"):
            self.client._validate_parameters(params)

    def test_validate_parameters_invalid_uc_preset(self):
        """Test parameter validation with invalid ucPreset."""
        params = {'prompt': 'test', 'ucPreset': 5}  # Out of range

        with pytest.raises(ValueError, match="ucPreset must be an integer between 0 and 3"):
            self.client._validate_parameters(params)

    @patch('requests.Session.post')
    def test_generate_image_success(self, mock_post):
        """Test successful image generation."""
        # Create mock ZIP response
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('image_0.png', b'fake_image_data')
        zip_data = zip_buffer.getvalue()

        # Mock successful HTTP response (NovelAI returns 200 for successful generation)
        mock_response = MagicMock()
        mock_response.status_code = 200
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
        assert payload['model'] == "nai-diffusion-4-5-curated"
        assert payload['action'] == "generate"
        assert 'parameters' in payload

        # Check v4 format parameters
        params = payload['parameters']
        assert params['params_version'] == 3
        assert 'v4_prompt' in params
        assert 'v4_negative_prompt' in params
        assert params['v4_prompt']['caption']['base_caption'] == "test prompt"
        assert params['sampler'] == "k_euler_ancestral"
        assert params['noise_schedule'] == "karras"
        assert params['qualityToggle'] is True
        assert params['prefer_brownian'] is True

    def test_build_v4_payload(self):
        """Test v4 payload generation matches expected structure."""
        validated_params = {
            'prompt': '1girl, scenery, air bubble, thorns, very aesthetic, location, masterpiece, no text, -0.8::feet::, rating:general',
            'negative_prompt': 'blurry, lowres, upscaled, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, halftone, multiple views, logo, too many watermarks, negative space, blank page',
            'width': 832,
            'height': 1216,
            'scale': 5,
            'sampler': 'k_euler_ancestral',
            'steps': 23,
            'n_samples': 1,
            'ucPreset': 0,
            'noise_schedule': 'karras',
            'seed': 1605800212
        }

        payload = self.client._build_v4_payload(validated_params, "nai-diffusion-4-5-curated")

        # Check top-level structure
        assert payload['input'] == validated_params['prompt']
        assert payload['model'] == "nai-diffusion-4-5-curated"
        assert payload['action'] == "generate"

        # Check parameters structure
        params = payload['parameters']
        assert params['params_version'] == 3
        assert params['width'] == 832
        assert params['height'] == 1216
        assert params['scale'] == 5
        assert params['sampler'] == 'k_euler_ancestral'
        assert params['steps'] == 23
        assert params['n_samples'] == 1
        assert params['ucPreset'] == 0
        assert params['qualityToggle'] is True
        assert params['autoSmea'] is False
        assert params['dynamic_thresholding'] is False
        assert params['controlnet_strength'] == 1
        assert params['legacy'] is False
        assert params['add_original_image'] is True
        assert params['cfg_rescale'] == 0
        assert params['noise_schedule'] == 'karras'
        assert params['legacy_v3_extend'] is False
        assert params['skip_cfg_above_sigma'] is None
        assert params['use_coords'] is False
        assert params['legacy_uc'] is False
        assert params['normalize_reference_strength_multiple'] is True
        assert params['seed'] == 1605800212
        assert params['characterPrompts'] == []
        assert params['deliberate_euler_ancestral_bug'] is False
        assert params['prefer_brownian'] is True

        # Check v4_prompt structure
        v4_prompt = params['v4_prompt']
        assert v4_prompt['caption']['base_caption'] == validated_params['prompt']
        assert v4_prompt['caption']['char_captions'] == []
        assert v4_prompt['use_coords'] is False
        assert v4_prompt['use_order'] is True

        # Check v4_negative_prompt structure
        v4_negative = params['v4_negative_prompt']
        assert v4_negative['caption']['base_caption'] == validated_params['negative_prompt']
        assert v4_negative['caption']['char_captions'] == []
        assert v4_negative['legacy_uc'] is False

    @patch('requests.Session.post')
    def test_generate_image_success_http_201(self, mock_post):
        """Test successful image generation with HTTP 201 response."""
        # Create mock ZIP response
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('image_0.png', b'fake_image_data')
        zip_data = zip_buffer.getvalue()

        # Mock successful HTTP response with 201 status
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = zip_data
        mock_post.return_value = mock_response

        # Test generation
        success, images, error = self.client.generate_image("test prompt")

        # Verify results
        assert success is True
        assert images is not None
        assert len(images) == 1
        assert images[0] == b'fake_image_data'
        assert error is None

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

    # Multi-character functionality tests
    def test_parse_character_parameters_valid_single(self):
        """Test parsing valid single character parameter."""
        char_args = ["char1:[girl with blue hair]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is None
        assert len(characters) == 1
        assert characters[0]['number'] == 1
        assert characters[0]['description'] == "girl with blue hair"

    def test_parse_character_parameters_valid_multiple(self):
        """Test parsing valid multiple character parameters."""
        char_args = ["char1:[girl with blue hair]", "char2:[boy with red eyes]", "char3:[elderly wizard]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is None
        assert len(characters) == 3
        assert characters[0]['number'] == 1
        assert characters[0]['description'] == "girl with blue hair"
        assert characters[1]['number'] == 2
        assert characters[1]['description'] == "boy with red eyes"
        assert characters[2]['number'] == 3
        assert characters[2]['description'] == "elderly wizard"

    def test_parse_character_parameters_complex_descriptions(self):
        """Test parsing character parameters with complex descriptions."""
        char_args = [
            "char1:[anime girl, long blue hair, white dress, holding book, sitting]",
            "char2:[muscular warrior, armor, sword, battle stance, serious expression]"
        ]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is None
        assert len(characters) == 2
        assert "anime girl, long blue hair, white dress, holding book, sitting" in characters[0]['description']
        assert "muscular warrior, armor, sword, battle stance, serious expression" in characters[1]['description']

    def test_parse_character_parameters_unordered(self):
        """Test parsing character parameters in non-sequential order."""
        char_args = ["char3:[third character]", "char1:[first character]", "char2:[second character]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is None
        assert len(characters) == 3
        # Should be sorted by character number
        assert characters[0]['number'] == 1
        assert characters[1]['number'] == 2
        assert characters[2]['number'] == 3

    def test_parse_character_parameters_invalid_syntax_missing_brackets(self):
        """Test parsing character parameters with missing brackets."""
        char_args = ["char1:missing_brackets"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is not None
        assert "Invalid character syntax" in error
        assert "Expected format: 'char1:[description]'" in error
        assert len(characters) == 0

    def test_parse_character_parameters_invalid_syntax_missing_colon(self):
        """Test parsing character parameters with missing colon."""
        char_args = ["char1[missing colon]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is not None
        assert "Invalid character syntax" in error
        assert len(characters) == 0

    def test_parse_character_parameters_empty_description(self):
        """Test parsing character parameters with empty description."""
        char_args = ["char1:[ ]"]  # Space inside brackets to match regex but still be empty when stripped

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is not None
        assert "Empty character description" in error
        assert len(characters) == 0

    def test_parse_character_parameters_invalid_number_zero(self):
        """Test parsing character parameters with invalid number (zero)."""
        char_args = ["char0:[invalid number]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is not None
        assert "Character number must be between 1 and 8" in error
        assert len(characters) == 0

    def test_parse_character_parameters_invalid_number_too_high(self):
        """Test parsing character parameters with invalid number (too high)."""
        char_args = ["char9:[too high number]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is not None
        assert "Character number must be between 1 and 8" in error
        assert len(characters) == 0

    def test_parse_character_parameters_duplicate_numbers(self):
        """Test parsing character parameters with duplicate numbers."""
        char_args = ["char1:[first description]", "char1:[duplicate number]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is not None
        assert "Duplicate character numbers found" in error
        assert len(characters) == 0

    def test_parse_character_parameters_case_insensitive(self):
        """Test parsing character parameters is case insensitive."""
        char_args = ["CHAR1:[uppercase char]", "Char2:[mixed case]"]

        characters, error = self.client._parse_character_parameters(char_args)

        assert error is None
        assert len(characters) == 2
        assert characters[0]['number'] == 1
        assert characters[1]['number'] == 2

    def test_generate_character_coordinates_single(self):
        """Test coordinate generation for single character."""
        coords = self.client._generate_character_coordinates(1)

        assert len(coords) == 1
        assert coords[0] == (0.0, 0.0)

    def test_generate_character_coordinates_two(self):
        """Test coordinate generation for two characters."""
        coords = self.client._generate_character_coordinates(2)

        assert len(coords) == 2
        assert coords[0] == (0.0, 0.0)
        assert coords[1] == (0.5, 0.5)

    def test_generate_character_coordinates_three(self):
        """Test coordinate generation for three characters."""
        coords = self.client._generate_character_coordinates(3)

        assert len(coords) == 3
        assert coords[0] == (0.0, 0.0)
        assert coords[1] == (0.5, 0.0)
        assert coords[2] == (0.25, 0.5)

    def test_generate_character_coordinates_four(self):
        """Test coordinate generation for four characters."""
        coords = self.client._generate_character_coordinates(4)

        assert len(coords) == 4
        assert coords[0] == (0.0, 0.0)
        assert coords[1] == (0.5, 0.0)
        assert coords[2] == (0.0, 0.5)
        assert coords[3] == (0.5, 0.5)

    def test_generate_character_coordinates_eight(self):
        """Test coordinate generation for maximum characters."""
        coords = self.client._generate_character_coordinates(8)

        assert len(coords) == 8
        # Verify all coordinates are within valid range [0, 1]
        for x, y in coords:
            assert 0.0 <= x <= 1.0
            assert 0.0 <= y <= 1.0

    def test_build_character_prompts_empty(self):
        """Test building character prompts with empty character list."""
        character_prompts, char_captions, negative_char_captions = self.client._build_character_prompts([], "negative prompt")

        assert len(character_prompts) == 0
        assert len(char_captions) == 0
        assert len(negative_char_captions) == 0

    def test_build_character_prompts_single(self):
        """Test building character prompts for single character."""
        characters = [{'number': 1, 'description': 'girl with blue hair'}]

        character_prompts, char_captions, negative_char_captions = self.client._build_character_prompts(characters, "base negative")

        assert len(character_prompts) == 1
        assert len(char_captions) == 1
        assert len(negative_char_captions) == 1

        # Check characterPrompts structure
        char_prompt = character_prompts[0]
        assert char_prompt['prompt'] == 'girl with blue hair'
        assert char_prompt['uc'] == 'lowres, aliasing, '
        assert char_prompt['center']['x'] == 0.0
        assert char_prompt['center']['y'] == 0.0
        assert char_prompt['enabled'] is True

        # Check char_captions structure
        char_caption = char_captions[0]
        assert char_caption['char_caption'] == 'girl with blue hair'
        assert len(char_caption['centers']) == 1
        assert char_caption['centers'][0]['x'] == 0.0
        assert char_caption['centers'][0]['y'] == 0.0

        # Check negative_char_captions structure
        neg_caption = negative_char_captions[0]
        assert neg_caption['char_caption'] == 'lowres, aliasing, '
        assert len(neg_caption['centers']) == 1
        assert neg_caption['centers'][0]['x'] == 0.0
        assert neg_caption['centers'][0]['y'] == 0.0

    def test_build_character_prompts_multiple(self):
        """Test building character prompts for multiple characters."""
        characters = [
            {'number': 1, 'description': 'girl with blue hair'},
            {'number': 2, 'description': 'boy with red eyes'}
        ]

        character_prompts, char_captions, negative_char_captions = self.client._build_character_prompts(characters, "base negative")

        assert len(character_prompts) == 2
        assert len(char_captions) == 2
        assert len(negative_char_captions) == 2

        # Verify first character
        assert character_prompts[0]['prompt'] == 'girl with blue hair'
        assert character_prompts[0]['center']['x'] == 0.0
        assert character_prompts[0]['center']['y'] == 0.0

        # Verify second character
        assert character_prompts[1]['prompt'] == 'boy with red eyes'
        assert character_prompts[1]['center']['x'] == 0.5
        assert character_prompts[1]['center']['y'] == 0.5

    def test_build_v4_payload_multicharacter(self):
        """Test v4 payload generation with multi-character data."""
        characters = [
            {'number': 1, 'description': 'girl with blue hair, dress'},
            {'number': 2, 'description': 'boy with red eyes, armor'}
        ]

        validated_params = {
            'prompt': 'fantasy scene',
            'negative_prompt': 'blurry, low quality',
            'width': 832,
            'height': 1216,
            'scale': 5,
            'sampler': 'k_euler_ancestral',
            'steps': 23,
            'n_samples': 1,
            'ucPreset': 0,
            'noise_schedule': 'karras',
            'seed': 12345,
            'characters': characters
        }

        payload = self.client._build_v4_payload(validated_params, "nai-diffusion-4-5-curated")

        # Check multi-character specific parameters
        params = payload['parameters']
        assert params['use_coords'] is True
        assert len(params['characterPrompts']) == 2
        assert params['uc'] == ""  # Empty base UC for multi-character

        # Check characterPrompts structure
        char_prompts = params['characterPrompts']
        assert char_prompts[0]['prompt'] == 'girl with blue hair, dress'
        assert char_prompts[0]['center']['x'] == 0.0
        assert char_prompts[0]['center']['y'] == 0.0
        assert char_prompts[1]['prompt'] == 'boy with red eyes, armor'
        assert char_prompts[1]['center']['x'] == 0.5
        assert char_prompts[1]['center']['y'] == 0.5

        # Check v4_prompt structure
        v4_prompt = params['v4_prompt']
        assert v4_prompt['use_coords'] is True
        assert len(v4_prompt['caption']['char_captions']) == 2
        assert v4_prompt['caption']['char_captions'][0]['char_caption'] == 'girl with blue hair, dress'
        assert v4_prompt['caption']['char_captions'][1]['char_caption'] == 'boy with red eyes, armor'

        # Check v4_negative_prompt structure
        v4_negative = params['v4_negative_prompt']
        assert v4_negative['caption']['base_caption'] == ""  # Empty for multi-character
        assert len(v4_negative['caption']['char_captions']) == 2

    def test_build_v4_payload_single_character_fallback(self):
        """Test v4 payload generation without character data (single character fallback)."""
        validated_params = {
            'prompt': 'simple scene',
            'negative_prompt': 'blurry, low quality',
            'width': 832,
            'height': 1216,
            'scale': 5,
            'sampler': 'k_euler_ancestral',
            'steps': 23,
            'n_samples': 1,
            'ucPreset': 0,
            'noise_schedule': 'karras',
            'seed': 12345
        }

        payload = self.client._build_v4_payload(validated_params, "nai-diffusion-4-5-curated")

        # Check single-character parameters
        params = payload['parameters']
        assert params['use_coords'] is False
        assert len(params['characterPrompts']) == 0
        assert len(params['v4_prompt']['caption']['char_captions']) == 0
        assert params['v4_negative_prompt']['caption']['base_caption'] == 'blurry, low quality'

    @patch('requests.Session.post')
    def test_generate_image_multicharacter_success(self, mock_post):
        """Test successful multi-character image generation."""
        # Create mock ZIP response
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('image_0.png', b'fake_multichar_image_data')
        zip_data = zip_buffer.getvalue()

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = zip_data
        mock_post.return_value = mock_response

        # Test multi-character generation
        character_args = ["char1:[girl with blue hair]", "char2:[boy with red eyes]"]
        success, images, error = self.client.generate_image(
            prompt="fantasy scene",
            character_args=character_args
        )

        # Verify results
        assert success is True
        assert len(images) == 1
        assert images[0] == b'fake_multichar_image_data'
        assert error is None

        # Verify API call payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        payload = kwargs['json']

        # Check multi-character payload structure
        params = payload['parameters']
        assert params['use_coords'] is True
        assert len(params['characterPrompts']) == 2
        assert params['characterPrompts'][0]['prompt'] == 'girl with blue hair'
        assert params['characterPrompts'][1]['prompt'] == 'boy with red eyes'

    @patch('requests.Session.post')
    def test_generate_image_multicharacter_invalid_params(self, mock_post):
        """Test multi-character generation with invalid character parameters."""
        # Test with invalid character syntax
        character_args = ["char1:missing_brackets", "char2:[valid description]"]

        success, images, error = self.client.generate_image(
            prompt="fantasy scene",
            character_args=character_args
        )

        # Should fail due to invalid character parameters
        assert success is False
        assert images is None
        assert error is not None
        assert "Character parameter error" in error

        # API should not be called
        mock_post.assert_not_called()

    def test_generate_image_character_args_none(self):
        """Test generate_image with None character_args (backward compatibility)."""
        with patch.object(self.client, '_validate_parameters') as mock_validate, \
             patch.object(self.client, '_build_v4_payload') as mock_build, \
             patch('requests.Session.post') as mock_post:

            # Mock successful validation and payload building
            mock_validate.return_value = {'prompt': 'test', 'negative_prompt': 'neg'}
            mock_build.return_value = {'test': 'payload'}

            # Mock successful HTTP response
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                zip_file.writestr('image_0.png', b'test_data')

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = zip_buffer.getvalue()
            mock_post.return_value = mock_response

            # Test with None character_args
            success, images, error = self.client.generate_image(
                prompt="test prompt",
                character_args=None
            )

            # Should succeed and not include character data
            assert success is True
            mock_validate.assert_called_once()
            validated_params = mock_validate.call_args[0][0]
            assert 'characters' not in validated_params

    def test_generate_image_character_args_empty_list(self):
        """Test generate_image with empty character_args list."""
        with patch.object(self.client, '_validate_parameters') as mock_validate, \
             patch.object(self.client, '_build_v4_payload') as mock_build, \
             patch('requests.Session.post') as mock_post:

            # Mock successful validation and payload building
            mock_validate.return_value = {'prompt': 'test', 'negative_prompt': 'neg'}
            mock_build.return_value = {'test': 'payload'}

            # Mock successful HTTP response
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                zip_file.writestr('image_0.png', b'test_data')

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = zip_buffer.getvalue()
            mock_post.return_value = mock_response

            # Test with empty character_args
            success, images, error = self.client.generate_image(
                prompt="test prompt",
                character_args=[]
            )

            # Should succeed and not include character data
            assert success is True
            mock_validate.assert_called_once()
            validated_params = mock_validate.call_args[0][0]
            assert 'characters' not in validated_params
