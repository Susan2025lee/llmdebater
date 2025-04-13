import pytest
from unittest.mock import patch
import tiktoken

# Ensure imports work correctly based on project structure
from src.utils.token_utils import estimate_token_count, DEFAULT_ENCODING, MODEL_TO_ENCODING

# --- Test Cases --- #

def test_estimate_token_count_simple():
    """Tests token counting for a basic string."""
    text = "Hello world! This is a test."
    # Using cl100k_base encoding (default), this should be 8 tokens
    expected_tokens = 8
    assert estimate_token_count(text) == expected_tokens

def test_estimate_token_count_empty_string():
    """Tests handling of an empty string input."""
    assert estimate_token_count("") == 0

def test_estimate_token_count_none_input():
    """Tests handling of None input."""
    assert estimate_token_count(None) == 0

def test_estimate_token_count_different_model():
    """Tests specifying a model (assuming it maps to the default encoding)."""
    text = "Another test string."
    # Assuming o3-mini maps to cl100k_base, count should be 4
    expected_tokens = 4
    # Explicitly pass model_name, even if it uses the default encoding
    assert estimate_token_count(text, model_name="o3-mini") == expected_tokens 

def test_estimate_token_count_encoding_fallback(caplog):
    """Tests the fallback mechanism if a model's specific encoding isn't found."""
    text = "Test fallback."
    # cl100k_base should give 3 tokens
    expected_tokens = 3
    
    # Mock tiktoken.get_encoding to simulate failure for the specific model
    # but success for the default encoding.
    original_get_encoding = tiktoken.get_encoding # Store the original function
    def mock_get_encoding(encoding_name):
        if encoding_name == "specific_unknown_encoding":
            raise ValueError("Encoding not found")
        elif encoding_name == DEFAULT_ENCODING:
            # Return the actual default encoding function using the stored original
            return original_get_encoding(DEFAULT_ENCODING)
        else:
            # Unexpected encoding request in this test
            raise ValueError(f"Unexpected encoding requested: {encoding_name}")

    # Temporarily add a non-existent model mapping to trigger the logic
    temp_model_name = "temp_unknown_model"
    MODEL_TO_ENCODING[temp_model_name] = "specific_unknown_encoding" 

    with patch('src.utils.token_utils.tiktoken.get_encoding', side_effect=mock_get_encoding):
        count = estimate_token_count(text, model_name=temp_model_name)
        assert count == expected_tokens
        # Check log messages for the warning
        assert "Encoding 'specific_unknown_encoding' not found" in caplog.text
        assert f"Falling back to default '{DEFAULT_ENCODING}'" in caplog.text
    
    # Clean up the temporary mapping
    del MODEL_TO_ENCODING[temp_model_name]

def test_estimate_token_count_encoding_critical_error(caplog):
    """Tests error handling if even the default encoding fails."""
    text = "Critical failure test."
    
    # Mock tiktoken.get_encoding to always fail
    with patch('src.utils.token_utils.tiktoken.get_encoding', side_effect=ValueError("All encodings failed")):
        count = estimate_token_count(text)
        assert count == -1 # Function should return -1 on critical error
        # Check log messages for the error
        assert f"Default encoding '{DEFAULT_ENCODING}' not found." in caplog.text

def test_estimate_token_count_encode_error(caplog):
    """Tests error handling if encoding.encode() itself fails."""
    text = "Test encoding failure."
    
    # Mock the encode method of the encoding object to raise an error
    with patch('src.utils.token_utils.tiktoken.Encoding.encode') as mock_encode:
        mock_encode.side_effect = Exception("Encoding process failed")
        count = estimate_token_count(text)
        assert count == -1 # Function should return -1 on encoding error
        assert "Error encoding text" in caplog.text 