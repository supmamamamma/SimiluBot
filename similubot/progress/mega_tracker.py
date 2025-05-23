"""MEGA download progress tracker."""

import re
import logging
from typing import Optional, Dict, Any

from .base import ProgressTracker


class MegaProgressTracker(ProgressTracker):
    """
    Progress tracker for MEGA downloads using MegaCMD.

    Parses MegaCMD output to extract download progress information.
    Expected format: TRANSFERRING ||################||(1714/1714 MB: 100.00 %)
    """

    # Regex patterns for parsing MegaCMD output
    TRANSFER_PATTERN = re.compile(
        r'TRANSFERRING\s+\|\|[#\s]*\|\|\s*\((\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\s*(\w+):\s*(\d+(?:\.\d+)?)\s*%\s*\)'
    )

    SPEED_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(KB|MB|GB)/s'
    )

    def __init__(self):
        """Initialize the MEGA progress tracker."""
        super().__init__("MEGA Download")
        self.logger = logging.getLogger("similubot.progress.mega")

    def parse_output(self, output_line: str) -> bool:
        """
        Parse a line of MegaCMD output for progress information.

        Args:
            output_line: Line of output from MegaCMD

        Returns:
            True if progress information was found and parsed, False otherwise
        """
        line = output_line.strip()

        # Skip empty lines
        if not line:
            return False

        # Log all output for debugging (but only in debug mode)
        self.logger.debug(f"Parsing MegaCMD output: {line}")

        # Look for transfer progress
        transfer_match = self.TRANSFER_PATTERN.search(line)
        if transfer_match:
            try:
                current_str, total_str, unit, percentage_str = transfer_match.groups()

                # Parse values
                current_value = float(current_str)
                total_value = float(total_str)
                percentage = float(percentage_str)

                # Convert to bytes based on unit
                unit_multipliers = {
                    'B': 1,
                    'KB': 1024,
                    'MB': 1024 * 1024,
                    'GB': 1024 * 1024 * 1024,
                    'TB': 1024 * 1024 * 1024 * 1024
                }

                multiplier = unit_multipliers.get(unit.upper(), 1024 * 1024)  # Default to MB
                current_size = int(current_value * multiplier)
                total_size = int(total_value * multiplier)

                # Look for speed information in the same line or nearby
                speed = None
                speed_match = self.SPEED_PATTERN.search(line)
                if speed_match:
                    speed_value, speed_unit = speed_match.groups()
                    speed_multiplier = unit_multipliers.get(speed_unit.upper(), 1024 * 1024)
                    speed = float(speed_value) * speed_multiplier

                # Create progress message
                if unit.upper() == 'B':
                    size_msg = f"{current_value:.0f}/{total_value:.0f} bytes"
                else:
                    size_msg = f"{current_value:.1f}/{total_value:.1f} {unit}"

                message = f"Downloading: {size_msg} ({percentage:.1f}%)"
                if speed:
                    if speed >= 1024 * 1024:
                        speed_msg = f"{speed / (1024 * 1024):.1f} MB/s"
                    elif speed >= 1024:
                        speed_msg = f"{speed / 1024:.1f} KB/s"
                    else:
                        speed_msg = f"{speed:.0f} B/s"
                    message += f" - {speed_msg}"

                # Update progress
                self.update(
                    percentage=percentage,
                    current_size=current_size,
                    total_size=total_size,
                    speed=speed,
                    message=message,
                    details={
                        'unit': unit,
                        'raw_current': current_value,
                        'raw_total': total_value
                    }
                )

                self.logger.info(f"MEGA download progress: {percentage:.1f}% ({size_msg})")
                return True

            except (ValueError, IndexError) as e:
                self.logger.warning(f"Failed to parse MEGA progress line: {line} - {e}")
                return False

        # Check for other status messages
        if "TRANSFERRING" in line:
            self.update(message="Transferring file...")
            self.logger.info("MEGA transfer started")
            return True
        elif "Starting download" in line or "Downloading" in line:
            self.update(message="Starting download...")
            self.logger.info("MEGA download starting")
            return True
        elif "Download completed" in line or "completed" in line.lower():
            self.complete("Download completed successfully")
            self.logger.info("MEGA download completed")
            return True
        elif "error" in line.lower() or "failed" in line.lower():
            self.fail(f"Download error: {line}")
            self.logger.error(f"MEGA download error: {line}")
            return True
        elif "login" in line.lower() or "authentication" in line.lower():
            self.update(message="Authenticating with MEGA...")
            self.logger.info("MEGA authentication in progress")
            return True
        elif "connecting" in line.lower() or "connection" in line.lower():
            self.update(message="Connecting to MEGA...")
            self.logger.info("MEGA connection in progress")
            return True
        elif line.startswith("mega-get"):
            # Command echo - ignore but log
            self.logger.debug(f"Command echo: {line}")
            return False
        elif "%" in line and any(unit in line.upper() for unit in ['B', 'KB', 'MB', 'GB']):
            # Fallback: try to extract percentage and size info from any line containing % and size units
            self.logger.debug(f"Attempting fallback parsing for: {line}")
            try:
                # Simple regex to find percentage
                import re
                percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                if percent_match:
                    percentage = float(percent_match.group(1))
                    self.update(
                        percentage=percentage,
                        message=f"Download progress: {percentage:.1f}%"
                    )
                    self.logger.info(f"MEGA download progress (fallback): {percentage:.1f}%")
                    return True
            except Exception as e:
                self.logger.debug(f"Fallback parsing failed: {e}")

        return False

    def _format_size(self, size_bytes: int) -> str:
        """
        Format size in bytes to human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes} B"

    def get_file_info_from_output(self, output: str) -> Optional[Dict[str, Any]]:
        """
        Extract file information from MegaCMD output.

        Args:
            output: Complete output from MegaCMD

        Returns:
            Dictionary with file information or None if not found
        """
        lines = output.split('\n')
        file_info = {}

        for line in lines:
            # Look for file size information
            if 'MB' in line or 'GB' in line or 'KB' in line:
                # Try to extract filename and size
                parts = line.split()
                for i, part in enumerate(parts):
                    if any(unit in part for unit in ['MB', 'GB', 'KB', 'B']):
                        if i > 0:
                            # Previous part might be filename
                            file_info['filename'] = parts[i-1]
                        file_info['size_str'] = part
                        break

        return file_info if file_info else None
