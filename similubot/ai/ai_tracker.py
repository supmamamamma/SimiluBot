"""Progress tracking for AI operations."""

import logging
import time
from typing import Optional, Dict, Any
from similubot.progress.base import ProgressTracker, ProgressInfo, ProgressStatus


class AITracker(ProgressTracker):
    """
    Progress tracker for AI conversation operations.
    
    Tracks AI request processing, response generation, and provides
    real-time progress updates for Discord users.
    """

    def __init__(self, operation_name: str = "AI Generation"):
        """
        Initialize the AI progress tracker.

        Args:
            operation_name: Name of the AI operation being tracked
        """
        super().__init__(operation_name)
        self.logger = logging.getLogger("similubot.ai.tracker")
        
        # AI-specific tracking
        self.request_start_time: Optional[float] = None
        self.response_start_time: Optional[float] = None
        self.tokens_generated: int = 0
        self.estimated_total_tokens: int = 0

    def start_request(self, prompt_length: int, estimated_response_tokens: int = 500) -> None:
        """
        Start tracking an AI request.

        Args:
            prompt_length: Length of the input prompt in characters
            estimated_response_tokens: Estimated response length in tokens
        """
        self.request_start_time = time.time()
        self.estimated_total_tokens = estimated_response_tokens
        self.tokens_generated = 0
        
        self.start()
        
        # Update with initial request info
        self.update(
            percentage=5.0,
            message="Sending request to AI provider...",
            details={
                "prompt_length": prompt_length,
                "estimated_tokens": estimated_response_tokens,
                "stage": "request"
            }
        )
        
        self.logger.debug(f"Started AI request tracking - Prompt: {prompt_length} chars, Estimated: {estimated_response_tokens} tokens")

    def start_response_generation(self) -> None:
        """Mark the start of response generation."""
        self.response_start_time = time.time()
        
        self.update(
            percentage=15.0,
            message="AI is generating response...",
            details={
                "stage": "generation",
                "tokens_generated": 0
            }
        )
        
        self.logger.debug("Started response generation tracking")

    def update_token_progress(self, tokens_generated: int, partial_response: Optional[str] = None) -> None:
        """
        Update progress based on tokens generated.

        Args:
            tokens_generated: Number of tokens generated so far
            partial_response: Partial response text (optional)
        """
        self.tokens_generated = tokens_generated
        
        # Calculate progress percentage (15% for request + up to 80% for generation)
        if self.estimated_total_tokens > 0:
            generation_progress = min(tokens_generated / self.estimated_total_tokens, 1.0)
            total_percentage = 15.0 + (generation_progress * 80.0)
        else:
            # Fallback if we don't have token estimates
            total_percentage = min(15.0 + (tokens_generated / 10), 90.0)
        
        # Calculate generation speed
        speed = None
        if self.response_start_time:
            elapsed = time.time() - self.response_start_time
            if elapsed > 0:
                speed = tokens_generated / elapsed  # tokens per second
        
        # Calculate ETA
        eta = None
        if speed and speed > 0 and self.estimated_total_tokens > tokens_generated:
            remaining_tokens = self.estimated_total_tokens - tokens_generated
            eta = remaining_tokens / speed
        
        details = {
            "stage": "generation",
            "tokens_generated": tokens_generated,
            "estimated_total": self.estimated_total_tokens,
            "generation_speed": speed
        }
        
        if partial_response:
            details["partial_response_length"] = len(partial_response)
        
        self.update(
            percentage=total_percentage,
            message=f"Generating response... ({tokens_generated} tokens)",
            details=details,
            speed=speed,
            eta=eta
        )

    def complete_generation(self, final_response: str, total_tokens: int) -> None:
        """
        Mark the completion of AI generation.

        Args:
            final_response: Final generated response
            total_tokens: Total tokens in the response
        """
        total_time = None
        if self.request_start_time:
            total_time = time.time() - self.request_start_time
        
        generation_time = None
        if self.response_start_time:
            generation_time = time.time() - self.response_start_time
        
        details = {
            "stage": "completed",
            "final_tokens": total_tokens,
            "response_length": len(final_response),
            "total_time": total_time,
            "generation_time": generation_time
        }
        
        if generation_time and generation_time > 0:
            details["average_speed"] = total_tokens / generation_time
        
        self.complete(f"AI response generated successfully ({total_tokens} tokens)")
        
        self.logger.info(f"AI generation completed - Tokens: {total_tokens}, Time: {total_time:.2f}s")

    def fail_generation(self, error_message: str) -> None:
        """
        Mark the AI generation as failed.

        Args:
            error_message: Error message describing the failure
        """
        total_time = None
        if self.request_start_time:
            total_time = time.time() - self.request_start_time
        
        details = {
            "stage": "failed",
            "tokens_generated": self.tokens_generated,
            "total_time": total_time,
            "error": error_message
        }
        
        self.fail(f"AI generation failed: {error_message}")
        
        self.logger.error(f"AI generation failed after {total_time:.2f}s: {error_message}")

    def parse_output(self, output_line: str) -> bool:
        """
        Parse output line for progress information.
        
        Note: This is primarily used for subprocess-based operations.
        For AI operations, we use the specific tracking methods above.

        Args:
            output_line: Line of output to parse

        Returns:
            False (AI operations don't use line-based parsing)
        """
        # AI operations don't typically use line-based output parsing
        # Progress is tracked through the API response mechanisms
        return False

    def get_generation_stats(self) -> Dict[str, Any]:
        """
        Get detailed generation statistics.

        Returns:
            Dictionary with generation statistics
        """
        stats = {
            "tokens_generated": self.tokens_generated,
            "estimated_total_tokens": self.estimated_total_tokens,
            "request_start_time": self.request_start_time,
            "response_start_time": self.response_start_time
        }
        
        if self.request_start_time:
            stats["total_elapsed"] = time.time() - self.request_start_time
        
        if self.response_start_time:
            stats["generation_elapsed"] = time.time() - self.response_start_time
            if stats["generation_elapsed"] > 0:
                stats["generation_speed"] = self.tokens_generated / stats["generation_elapsed"]
        
        if self.current_progress:
            stats["current_percentage"] = self.current_progress.percentage
            stats["current_status"] = self.current_progress.status.value
        
        return stats
