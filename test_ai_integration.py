#!/usr/bin/env python3
"""
Simple integration test script for AI functionality.
This script tests the AI components without requiring a full Discord bot setup.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from similubot.utils.config_manager import ConfigManager
from similubot.ai.conversation_memory import ConversationMemory
from similubot.ai.ai_tracker import AITracker


async def test_conversation_memory():
    """Test conversation memory functionality."""
    print("Testing Conversation Memory...")
    
    # Mock config
    mock_config = MagicMock(spec=ConfigManager)
    mock_config.get_ai_conversation_timeout.return_value = 1800
    mock_config.get_ai_max_conversation_history.return_value = 10
    mock_config.get_ai_default_system_prompt.return_value = "You are a helpful assistant."
    mock_config.get_ai_danbooru_system_prompt.return_value = "Generate Danbooru tags."
    
    # Create conversation memory
    memory = ConversationMemory(mock_config)
    
    # Test adding messages
    user_id = 12345
    memory.add_user_message(user_id, "Hello, how are you?", "default")
    memory.add_assistant_message(user_id, "I'm doing well, thank you!")
    
    # Get conversation messages
    messages = memory.get_conversation_messages(user_id, "default")
    print(f"✅ Conversation has {len(messages)} messages")
    
    # Test mode switching
    memory.add_user_message(user_id, "anime girl with blue hair", "danbooru")
    danbooru_messages = memory.get_conversation_messages(user_id, "danbooru")
    print(f"✅ Danbooru mode has {len(danbooru_messages)} messages")
    
    # Test statistics
    stats = memory.get_conversation_stats()
    print(f"✅ Active conversations: {stats['active_conversations']}")
    print(f"✅ Total messages: {stats['total_messages']}")
    
    # Cleanup
    await memory.shutdown()
    print("✅ Conversation memory test completed")


def test_ai_tracker():
    """Test AI progress tracking."""
    print("\nTesting AI Tracker...")
    
    # Create tracker
    tracker = AITracker("Test AI Generation")
    
    # Test request tracking
    tracker.start_request(100, 500)
    print("✅ Started request tracking")
    
    # Test response generation
    tracker.start_response_generation()
    print("✅ Started response generation tracking")
    
    # Test token progress updates
    tracker.update_token_progress(250, "Partial response text...")
    progress = tracker.get_current_progress()
    print(f"✅ Progress: {progress.percentage:.1f}%")
    
    # Test completion
    tracker.complete_generation("Final complete response", 500)
    final_progress = tracker.get_current_progress()
    print(f"✅ Final progress: {final_progress.percentage:.1f}%")
    
    # Test statistics
    stats = tracker.get_generation_stats()
    print(f"✅ Generated {stats['tokens_generated']} tokens")
    
    print("✅ AI tracker test completed")


def test_config_manager():
    """Test configuration manager AI methods."""
    print("\nTesting Configuration Manager...")
    
    # Test environment variable access
    os.environ['TEST_AI_PROVIDER'] = 'openrouter'
    os.environ['TEST_AI_TOKENS'] = '2048'
    os.environ['TEST_AI_TEMP'] = '0.7'
    
    try:
        config = ConfigManager("config/config.yaml")
        
        # Test environment variable methods
        provider = config.get_env('TEST_AI_PROVIDER', 'default')
        print(f"✅ Environment variable access: {provider}")
        
        # Test AI configuration methods
        max_tokens = config.get_ai_max_tokens()
        temperature = config.get_ai_temperature()
        timeout = config.get_ai_conversation_timeout()
        
        print(f"✅ Max tokens: {max_tokens}")
        print(f"✅ Temperature: {temperature}")
        print(f"✅ Conversation timeout: {timeout}")
        
        # Test system prompts
        default_prompt = config.get_ai_default_system_prompt()
        danbooru_prompt = config.get_ai_danbooru_system_prompt()
        
        print(f"✅ Default prompt length: {len(default_prompt)} characters")
        print(f"✅ Danbooru prompt length: {len(danbooru_prompt)} characters")
        
        print("✅ Configuration manager test completed")
        
    except FileNotFoundError:
        print("⚠️  Config file not found, skipping config manager test")
    except Exception as e:
        print(f"❌ Config manager test failed: {e}")
    
    finally:
        # Clean up environment variables
        for key in ['TEST_AI_PROVIDER', 'TEST_AI_TOKENS', 'TEST_AI_TEMP']:
            if key in os.environ:
                del os.environ[key]


async def main():
    """Run all integration tests."""
    print("🤖 AI Integration Test Suite")
    print("=" * 50)
    
    try:
        # Test individual components
        test_config_manager()
        await test_conversation_memory()
        test_ai_tracker()
        
        print("\n" + "=" * 50)
        print("✅ All AI integration tests completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Copy .env.example to .env and configure your AI provider")
        print("2. Run the bot and test with: !ai Hello, how are you?")
        print("3. Test Danbooru mode with: !ai mode:danbooru anime girl with blue hair")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
