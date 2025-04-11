import tiktoken
import logging

# TODO: Confirm the correct encoding for o3-mini. Using cl100k_base as a default.
# Other possibilities might include 'o200k_base' if it's based on newer models.
DEFAULT_ENCODING = "cl100k_base"
MODEL_TO_ENCODING = {
    "o3-mini": DEFAULT_ENCODING,
    # Add other model mappings if needed, e.g., "gpt-4": "cl100k_base"
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Basic logging setup

def estimate_token_count(text: str, model_name: str = "o3-mini") -> int:
    """
    Estimates the number of tokens in a given text string using tiktoken.

    Args:
        text: The text string to estimate tokens for.
        model_name: The name of the model (used to determine the correct encoding).
                    Defaults to "o3-mini".

    Returns:
        The estimated number of tokens. Returns -1 on error, 0 if text is empty.
    """
    if not text:
        return 0

    encoding_name = MODEL_TO_ENCODING.get(model_name, DEFAULT_ENCODING)
    try:
        # Attempt to get the encoding for the specified model or default
        encoding = tiktoken.get_encoding(encoding_name)
    except ValueError:
        logger.warning(
            f"Encoding '{encoding_name}' not found for model '{model_name}'. "
            f"Falling back to default '{DEFAULT_ENCODING}'."
        )
        try:
            encoding = tiktoken.get_encoding(DEFAULT_ENCODING)
        except ValueError:
            logger.error(f"Default encoding '{DEFAULT_ENCODING}' not found. "
                         "Tiktoken might be improperly installed or configured.")
            return -1 # Indicate critical setup error

    try:
        token_integers = encoding.encode(text)
        token_count = len(token_integers)
        return token_count
    except Exception as e:
        logger.error(f"Error encoding text with '{encoding_name}': {e}", exc_info=True)
        return -1 # Indicate encoding error

# Example usage (can be kept under __main__ guard)
if __name__ == "__main__":
    sample_text = "This is a sample financial report text."
    sample_model = "o3-mini"
    count = estimate_token_count(sample_text, model_name=sample_model)
    if count != -1:
        print(f"Estimated tokens for sample text using '{sample_model}' encoding: {count}")
    else:
        print(f"Could not estimate tokens for sample text using '{sample_model}'. Check logs.")

    # Example with a non-existent model to test fallback
    non_existent_model = "non_existent_model_xyz"
    count_fallback = estimate_token_count(sample_text, model_name=non_existent_model)
    if count_fallback != -1:
        print(f"Estimated tokens for sample text using fallback encoding for '{non_existent_model}': {count_fallback}")
    else:
        print(f"Could not estimate tokens for sample text using '{non_existent_model}'. Check logs.") 