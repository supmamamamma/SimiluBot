"""Tests for the audio converter module."""
import os
import pytest
from unittest.mock import patch, MagicMock

from similubot.converters.audio_converter import AudioConverter

class TestAudioConverter:
    """Test cases for the audio converter."""
    
    def test_is_supported_format(self):
        """Test the is_supported_format method."""
        converter = AudioConverter()
        
        # Supported formats
        assert converter.is_supported_format("test.mp4")
        assert converter.is_supported_format("test.mp3")
        assert converter.is_supported_format("test.mkv")
        assert converter.is_supported_format("test.wav")
        
        # Unsupported formats
        assert not converter.is_supported_format("test.txt")
        assert not converter.is_supported_format("test.pdf")
        assert not converter.is_supported_format("test.jpg")
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_convert_to_aac_success(self, mock_getsize, mock_exists, mock_run):
        """Test successful conversion to AAC."""
        # Set up mocks
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        
        # Mock successful FFmpeg execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        
        # Create converter and run test
        converter = AudioConverter()
        success, output_file, error = converter.convert_to_aac(
            "input.mp4",
            bitrate=128,
            output_file="output.m4a"
        )
        
        # Verify results
        assert success is True
        assert output_file == "output.m4a"
        assert error is None
        
        # Verify mock calls
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert "input.mp4" in cmd
        assert "-c:a" in cmd
        assert "aac" in cmd
        assert "-b:a" in cmd
        assert "128k" in cmd
        assert "output.m4a" in cmd
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_convert_to_aac_failure(self, mock_exists, mock_run):
        """Test failed conversion to AAC."""
        # Set up mocks
        mock_exists.side_effect = lambda path: path == "input.mp4"
        
        # Mock failed FFmpeg execution
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Error: conversion failed"
        mock_run.return_value = mock_process
        
        # Create converter and run test
        converter = AudioConverter()
        success, output_file, error = converter.convert_to_aac(
            "input.mp4",
            bitrate=128,
            output_file="output.m4a"
        )
        
        # Verify results
        assert success is False
        assert output_file is None
        assert "conversion failed" in error.lower()
    
    def test_convert_to_aac_input_not_found(self):
        """Test conversion with non-existent input file."""
        with patch('os.path.exists', return_value=False):
            converter = AudioConverter()
            success, output_file, error = converter.convert_to_aac("nonexistent.mp4")
            
            # Verify results
            assert success is False
            assert output_file is None
            assert "not found" in error.lower()
    
    def test_convert_to_aac_unsupported_format(self):
        """Test conversion with unsupported format."""
        with patch('os.path.exists', return_value=True):
            converter = AudioConverter()
            success, output_file, error = converter.convert_to_aac("input.txt")
            
            # Verify results
            assert success is False
            assert output_file is None
            assert "unsupported format" in error.lower()
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_get_media_info_success(self, mock_exists, mock_run):
        """Test successful media info retrieval."""
        # Set up mocks
        mock_exists.return_value = True
        
        # Mock successful FFprobe execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"format": {"duration": "60"}, "streams": [{"codec_type": "audio"}]}'
        mock_run.return_value = mock_process
        
        # Create converter and run test
        converter = AudioConverter()
        success, media_info, error = converter.get_media_info("input.mp4")
        
        # Verify results
        assert success is True
        assert media_info is not None
        assert "format" in media_info
        assert "streams" in media_info
        assert error is None
        
        # Verify mock calls
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "ffprobe" in cmd
        assert "input.mp4" in cmd
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_get_media_info_failure(self, mock_exists, mock_run):
        """Test failed media info retrieval."""
        # Set up mocks
        mock_exists.return_value = True
        
        # Mock failed FFprobe execution
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Error: could not open file"
        mock_run.return_value = mock_process
        
        # Create converter and run test
        converter = AudioConverter()
        success, media_info, error = converter.get_media_info("input.mp4")
        
        # Verify results
        assert success is False
        assert media_info is None
        assert "could not open file" in error.lower()
