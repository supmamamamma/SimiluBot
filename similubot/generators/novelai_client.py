"""NovelAI API client for SimiluBot."""
import base64
import io
import json
import logging
import random
import string
import zipfile
from typing import Dict, Any, Optional, Tuple, List
import requests

class NovelAIClient:
    """
    Client for interacting with the NovelAI Image Generation API.
    
    Handles authentication, request formatting, and response processing
    for NovelAI's image generation endpoints.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://image.novelai.net",
        timeout: int = 120
    ):
        """
        Initialize the NovelAI client.
        
        Args:
            api_key: NovelAI API key for authentication
            base_url: Base URL for the NovelAI API
            timeout: Request timeout in seconds
        """
        self.logger = logging.getLogger("similubot.generators.novelai_client")
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Set up session with default headers
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'SimiluBot/1.0'
        })
        
        self.logger.debug(f"Initialized NovelAI client with base URL: {self.base_url}")
    
    def _generate_correlation_id(self) -> str:
        """
        Generate a correlation ID for API requests.
        
        Returns:
            6-character alphanumeric correlation ID
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize generation parameters.
        
        Args:
            parameters: Raw parameters dictionary
            
        Returns:
            Validated parameters dictionary
            
        Raises:
            ValueError: If parameters are invalid
        """
        validated = parameters.copy()
        
        # Validate required parameters
        if 'prompt' not in validated or not validated['prompt'].strip():
            raise ValueError("Prompt is required and cannot be empty")
        
        # Validate dimensions
        width = validated.get('width', 832)
        height = validated.get('height', 1216)
        
        if not isinstance(width, int) or width < 64 or width > 2048:
            raise ValueError("Width must be an integer between 64 and 2048")
        if not isinstance(height, int) or height < 64 or height > 2048:
            raise ValueError("Height must be an integer between 64 and 2048")
        
        # Ensure dimensions are multiples of 64
        validated['width'] = (width // 64) * 64
        validated['height'] = (height // 64) * 64
        
        # Validate steps
        steps = validated.get('steps', 28)
        if not isinstance(steps, (int, float)) or steps < 1 or steps > 50:
            raise ValueError("Steps must be a number between 1 and 50")
        validated['steps'] = int(steps)
        
        # Validate scale (CFG scale)
        scale = validated.get('scale', 5.0)
        if not isinstance(scale, (int, float)) or scale < 1.0 or scale > 20.0:
            raise ValueError("Scale must be a number between 1.0 and 20.0")
        validated['scale'] = float(scale)
        
        # Validate n_samples
        n_samples = validated.get('n_samples', 1)
        if not isinstance(n_samples, int) or n_samples < 1 or n_samples > 4:
            raise ValueError("n_samples must be an integer between 1 and 4")
        validated['n_samples'] = n_samples
        
        # Handle seed
        seed = validated.get('seed', -1)
        if seed == -1:
            validated['seed'] = random.randint(0, 2**32 - 1)
        elif not isinstance(seed, int) or seed < 0:
            raise ValueError("Seed must be a non-negative integer or -1 for random")
        
        # Set default sampler if not provided
        if 'sampler' not in validated:
            validated['sampler'] = 'k_euler'
        
        self.logger.debug(f"Validated parameters: {validated}")
        return validated
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        model: str = "nai-diffusion-3",
        **parameters
    ) -> Tuple[bool, Optional[List[bytes]], Optional[str]]:
        """
        Generate images using NovelAI's diffusion models.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Optional negative prompt
            model: Model to use for generation
            **parameters: Additional generation parameters
            
        Returns:
            Tuple containing:
                - Success status (True/False)
                - List of image data as bytes if successful, None otherwise
                - Error message if failed, None otherwise
        """
        try:
            self.logger.info(f"Generating image with prompt: '{prompt[:100]}...'")
            
            # Prepare parameters
            gen_params = {
                'prompt': prompt.strip(),
                **parameters
            }
            
            if negative_prompt:
                gen_params['negative_prompt'] = negative_prompt.strip()
            
            # Validate parameters
            validated_params = self._validate_parameters(gen_params)
            
            # Prepare request payload
            payload = {
                'input': validated_params['prompt'],
                'model': model,
                'action': 'generate',
                'parameters': {
                    'width': validated_params['width'],
                    'height': validated_params['height'],
                    'scale': validated_params['scale'],
                    'sampler': validated_params['sampler'],
                    'steps': validated_params['steps'],
                    'n_samples': validated_params['n_samples'],
                    'seed': validated_params['seed']
                }
            }
            
            # Add negative prompt if provided
            if 'negative_prompt' in validated_params:
                payload['parameters']['negative_prompt'] = validated_params['negative_prompt']
            
            # Generate correlation ID
            correlation_id = self._generate_correlation_id()
            headers = {'x-correlation-id': correlation_id}
            
            self.logger.debug(f"Sending request to {self.base_url}/ai/generate-image")
            self.logger.debug(f"Correlation ID: {correlation_id}")
            self.logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Make API request
            response = self.session.post(
                f"{self.base_url}/ai/generate-image",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Check response status
            if response.status_code == 401:
                error_msg = "Authentication failed. Please check your NovelAI API key."
                self.logger.error(error_msg)
                return False, None, error_msg
            elif response.status_code == 429:
                error_msg = "Rate limited. Please wait before making another request."
                self.logger.error(error_msg)
                return False, None, error_msg
            elif response.status_code != 201:
                error_msg = f"API request failed: HTTP {response.status_code}"
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data.get('message', 'Unknown error')}"
                    except:
                        pass
                else:
                    error_msg += f" - {response.text[:200]}"
                self.logger.error(error_msg)
                return False, None, error_msg
            
            # Process ZIP response
            try:
                images = self._extract_images_from_zip(response.content)
                if not images:
                    error_msg = "No images found in response"
                    self.logger.error(error_msg)
                    return False, None, error_msg
                
                self.logger.info(f"Successfully generated {len(images)} image(s)")
                return True, images, None
                
            except Exception as e:
                error_msg = f"Failed to extract images from response: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                return False, None, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {self.timeout} seconds"
            self.logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
    
    def _extract_images_from_zip(self, zip_data: bytes) -> List[bytes]:
        """
        Extract image files from ZIP response.
        
        Args:
            zip_data: ZIP file data as bytes
            
        Returns:
            List of image data as bytes
            
        Raises:
            Exception: If ZIP extraction fails
        """
        images = []
        
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            for file_info in zip_file.filelist:
                if file_info.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    image_data = zip_file.read(file_info.filename)
                    images.append(image_data)
                    self.logger.debug(f"Extracted image: {file_info.filename} ({len(image_data)} bytes)")
        
        return images
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test the connection to NovelAI API.
        
        Returns:
            Tuple containing:
                - Success status (True/False)
                - Error message if failed, None otherwise
        """
        try:
            self.logger.info("Testing NovelAI API connection...")
            
            # Make a simple request to test authentication
            response = self.session.get(
                f"{self.base_url}/ai/generate-image/suggest-tags",
                params={'model': 'nai-diffusion-3', 'prompt': 'test'},
                timeout=10
            )
            
            if response.status_code == 401:
                error_msg = "Authentication failed. Please check your NovelAI API key."
                self.logger.error(error_msg)
                return False, error_msg
            elif response.status_code in [200, 404]:  # 404 is acceptable for this test
                self.logger.info("NovelAI API connection successful")
                return True, None
            else:
                error_msg = f"Unexpected response: HTTP {response.status_code}"
                self.logger.warning(error_msg)
                return False, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "Connection test timed out"
            self.logger.error(error_msg)
            return False, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during connection test: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during connection test: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
