"""OpenAI-compatible AI client with multi-provider support."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
import aiohttp
from openai import AsyncOpenAI
from similubot.utils.config_manager import ConfigManager


class AIClient:
    """
    OpenAI-compatible AI client supporting multiple providers.

    Supports OpenRouter, SiliconFlow, DeepSeek, and other OpenAI-compatible APIs.
    Provides conversation management and streaming capabilities.
    """

    def __init__(self, config: ConfigManager, provider: Optional[str] = None):
        """
        Initialize the AI client.

        Args:
            config: Configuration manager instance
            provider: AI provider to use (defaults to configured default)

        Raises:
            ValueError: If the specified provider is not configured
        """
        self.logger = logging.getLogger("similubot.ai.client")
        self.config = config
        self.provider = provider or config.get_default_ai_provider()

        # Get provider configuration
        try:
            self.provider_config = config.get_ai_provider_config(self.provider)
            self.logger.info(f"Initialized AI client with provider: {self.provider}")
        except ValueError as e:
            self.logger.error(f"Failed to initialize AI client: {e}")
            raise

        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.provider_config['api_key'],
            base_url=self.provider_config['base_url']
        )

        # AI generation parameters
        self.max_tokens = config.get_ai_max_tokens()
        self.temperature = config.get_ai_temperature()
        self.model = self.provider_config['model']

        self.logger.debug(f"AI client configured - Model: {self.model}, Max tokens: {self.max_tokens}")

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """
        Generate an AI response for the given messages.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt to override default
            stream: Whether to stream the response

        Returns:
            Generated response text

        Raises:
            Exception: If the API request fails
        """
        try:
            # Prepare messages with system prompt
            formatted_messages = []

            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})

            formatted_messages.extend(messages)

            self.logger.debug(f"Generating AI response with {len(formatted_messages)} messages")

            if stream:
                return await self._generate_streaming_response(formatted_messages)
            else:
                return await self._generate_standard_response(formatted_messages)

        except Exception as e:
            self.logger.error(f"AI generation failed: {e}", exc_info=True)
            raise

    async def _generate_standard_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a standard (non-streaming) response."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("AI response was empty")

        self.logger.debug(f"Generated response: {len(content)} characters")
        return content.strip()

    async def _generate_streaming_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a streaming response and return the complete text."""
        response_chunks = []

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                response_chunks.append(chunk.choices[0].delta.content)

        complete_response = ''.join(response_chunks)
        self.logger.debug(f"Generated streaming response: {len(complete_response)} characters")
        return complete_response.strip()

    async def generate_streaming_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming AI response.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt to override default

        Yields:
            Response chunks as they are generated

        Raises:
            Exception: If the API request fails
        """
        try:
            # Prepare messages with system prompt
            formatted_messages = []

            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})

            formatted_messages.extend(messages)

            self.logger.debug(f"Starting streaming AI response with {len(formatted_messages)} messages")

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"Streaming AI generation failed: {e}", exc_info=True)
            raise

    def get_provider_info(self) -> Dict[str, str]:
        """
        Get information about the current provider.

        Returns:
            Dictionary with provider information
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.provider_config['base_url'],
            "max_tokens": str(self.max_tokens),
            "temperature": str(self.temperature)
        }

    async def test_connection(self) -> bool:
        """
        Test the connection to the AI provider.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_messages = [{"role": "user", "content": "Hello"}]
            await self._generate_standard_response(test_messages)
            self.logger.info(f"AI provider {self.provider} connection test successful")
            return True
        except Exception as e:
            self.logger.error(f"AI provider {self.provider} connection test failed: {e}")
            return False

    async def close(self) -> None:
        """Close the AI client and clean up resources."""
        try:
            await self.client.close()
            self.logger.debug("AI client closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing AI client: {e}")

    def is_available(self) -> bool:
        """
        Check if the AI client is available and properly configured.

        Returns:
            True if the client is available, False otherwise
        """
        try:
            # Check if provider config is valid
            return all(self.provider_config.values())
        except Exception:
            return False
