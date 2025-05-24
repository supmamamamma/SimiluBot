# NovelAI Image Generation Integration

This document describes the NovelAI image generation functionality integrated into SimiluBot.

## Overview

The NovelAI integration allows Discord users to generate AI images using NovelAI's diffusion models through a simple `!nai` command. The system provides real-time progress tracking, error handling, and automatic file upload to the configured service.

## Features

- **Text-to-Image Generation**: Generate images from text prompts using NovelAI's API
- **Real-time Progress Tracking**: Live updates in Discord showing generation progress
- **Multiple Upload Options**: Support for CatBox and Discord direct upload
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Configurable Parameters**: Customizable generation settings via configuration
- **Rate Limiting Awareness**: Proper handling of API rate limits
- **Secure API Key Management**: API keys stored securely in configuration

## Configuration

### Required Configuration

Add the following to your `config/config.yaml`:

```yaml
novelai:
  api_key: "YOUR_NOVELAI_API_KEY_HERE"  # Your NovelAI API key
  base_url: "https://image.novelai.net"  # NovelAI Image Generation API base URL
  default_model: "nai-diffusion-3"  # Default image generation model
  default_parameters:
    width: 832  # Default image width
    height: 1216  # Default image height
    steps: 28  # Number of generation steps
    scale: 5.0  # CFG scale
    sampler: "k_euler"  # Sampling method
    n_samples: 1  # Number of images to generate
    seed: -1  # Random seed (-1 for random)
  timeout: 120  # API request timeout in seconds
```

### Getting a NovelAI API Key

1. Sign up for a NovelAI account at https://novelai.net/
2. Subscribe to a plan that includes API access
3. Go to your account settings and generate an API key
4. Add the API key to your configuration file

### Optional Configuration

The bot will work with default settings, but you can customize:

- **Model**: Choose different diffusion models (e.g., `nai-diffusion-3`, `nai-diffusion-2`)
- **Dimensions**: Adjust default image size (must be multiples of 64)
- **Generation Steps**: Higher steps = better quality but slower generation
- **CFG Scale**: Controls how closely the AI follows the prompt
- **Sampler**: Different sampling methods for varied results

## Usage

### Basic Command

```
!nai <prompt>
```

Generate an image from a text prompt:

```
!nai a beautiful sunset over mountains
!nai anime girl with blue hair, detailed artwork
!nai cyberpunk cityscape at night, neon lights
```

### Command Features

- **Prompt Length**: Supports prompts up to several hundred characters
- **Progress Updates**: Real-time progress shown in Discord embed
- **Multiple Images**: Can generate multiple images if configured
- **Automatic Upload**: Images automatically uploaded to configured service

### Example Usage

```
User: !nai a majestic dragon flying over a medieval castle

Bot: 🎨 AI Image Generation
     Generating image from prompt: `a majestic dragon flying over a medieval castle`
     
     [Progress updates every few seconds]
     🔄 Generating image with AI...
     🖼️ Generating image details...
     ✨ Adding final touches...
     📤 Uploading to catbox...
     
     ✅ Image Generation Complete
     Your AI-generated image is ready!
     
     🎨 Prompt: `a majestic dragon flying over a medieval castle`
     🤖 Model: nai-diffusion-3
     📊 Images: 1
     🔗 Download Link: https://files.catbox.moe/abc123.png
```

## Architecture

### Module Structure

```
similubot/
├── generators/
│   ├── __init__.py
│   ├── novelai_client.py      # NovelAI API client
│   └── image_generator.py     # High-level image generation
├── progress/
│   └── novelai_tracker.py     # Progress tracking for generation
└── bot.py                     # Main bot with !nai command
```

### Key Components

1. **NovelAIClient**: Low-level API client for NovelAI
   - Handles authentication and HTTP requests
   - Validates parameters and processes responses
   - Extracts images from ZIP responses

2. **ImageGenerator**: High-level generation coordinator
   - Manages progress tracking
   - Handles file operations
   - Coordinates with uploaders

3. **NovelAIProgressTracker**: Progress tracking system
   - Real-time progress updates
   - Estimated completion times
   - Stage-based progress reporting

4. **Bot Integration**: Discord command handling
   - `!nai` command implementation
   - Error handling and user feedback
   - Integration with existing upload systems

### Data Flow

1. User sends `!nai <prompt>` command
2. Bot validates prompt and checks configuration
3. ImageGenerator creates progress tracker
4. NovelAIClient sends API request with parameters
5. Progress tracker provides real-time updates
6. Generated images saved to temporary files
7. Images uploaded using configured uploader
8. Success/error message sent to Discord
9. Temporary files cleaned up

## Error Handling

### Common Errors and Solutions

1. **"NovelAI image generation is not configured"**
   - Solution: Add NovelAI API key to configuration

2. **"Authentication failed"**
   - Solution: Check API key validity and subscription status

3. **"Rate limited"**
   - Solution: Wait before making another request

4. **"Generation failed"**
   - Solution: Check prompt content and try again

5. **"Upload failed"**
   - Solution: Check upload service configuration

### Error Recovery

- Automatic cleanup of temporary files on errors
- Graceful degradation when services are unavailable
- User-friendly error messages with actionable advice
- Detailed logging for debugging

## Performance Considerations

### Generation Times

- Typical generation: 15-45 seconds
- Factors affecting speed:
  - Number of steps (more steps = slower)
  - Number of samples (multiple images = slower)
  - Server load and queue times

### Resource Usage

- **Memory**: Minimal, images processed as streams
- **Storage**: Temporary files cleaned up automatically
- **Network**: Efficient ZIP-based image transfer

### Rate Limiting

- NovelAI enforces rate limits per subscription tier
- Bot respects rate limits and provides appropriate feedback
- No automatic retry to prevent API abuse

## Security

### API Key Protection

- API keys stored in configuration files (not in code)
- Keys transmitted securely via HTTPS
- No logging of API keys in debug output

### Input Validation

- Prompt content validated for safety
- Parameter ranges enforced
- Malicious input sanitized

### File Handling

- Temporary files use secure random names
- Files cleaned up after processing
- No persistent storage of generated content

## Testing

### Unit Tests

Run the test suite:

```bash
pytest tests/test_novelai_client.py
pytest tests/test_image_generator.py
pytest tests/test_novelai_tracker.py
pytest tests/test_bot_novelai_integration.py
```

### Mock Testing

All tests use mocked API calls to avoid:
- Using real API credits during testing
- Dependency on external services
- Network-related test failures

### Integration Testing

Test with real API (optional):

1. Set up test configuration with real API key
2. Run integration tests manually
3. Verify end-to-end functionality

## Troubleshooting

### Debug Logging

Enable debug logging in configuration:

```yaml
logging:
  level: "DEBUG"
```

### Common Issues

1. **Bot doesn't respond to !nai**
   - Check bot permissions in Discord
   - Verify configuration is loaded correctly
   - Check logs for initialization errors

2. **Generation takes too long**
   - Check NovelAI server status
   - Verify network connectivity
   - Consider reducing steps or samples

3. **Images not uploading**
   - Check upload service configuration
   - Verify file permissions in temp directory
   - Check uploader-specific settings

### Log Analysis

Key log messages to look for:

- `"NovelAI image generator initialized successfully"` - Successful setup
- `"Starting NovelAI image generation"` - Command received
- `"Generation completed"` - Successful generation
- `"Upload successful"` - File uploaded successfully

## API Reference

### Configuration Methods

- `get_novelai_api_key()` - Get API key
- `get_novelai_base_url()` - Get API base URL
- `get_novelai_default_model()` - Get default model
- `get_novelai_default_parameters()` - Get default parameters
- `get_novelai_timeout()` - Get request timeout

### Client Methods

- `generate_image(prompt, **params)` - Generate image
- `test_connection()` - Test API connectivity
- `_validate_parameters(params)` - Validate generation parameters

### Generator Methods

- `generate_image_with_progress(prompt, **params)` - Generate with progress
- `generate_and_upload(prompt, uploader, **params)` - Generate and upload
- `cleanup_temp_files(paths)` - Clean up temporary files

## Future Enhancements

### Planned Features

- **Advanced Parameters**: Support for more generation parameters
- **Batch Generation**: Generate multiple variations of a prompt
- **Image-to-Image**: Support for img2img generation
- **Style Presets**: Predefined style configurations
- **User Preferences**: Per-user default settings

### Potential Improvements

- **Caching**: Cache generated images for repeated prompts
- **Queue System**: Handle multiple concurrent requests
- **Usage Analytics**: Track generation statistics
- **Cost Tracking**: Monitor API usage and costs
