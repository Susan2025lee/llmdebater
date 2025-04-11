import os
import sys
import json
from typing import Dict, List, Optional, Any, Union
from openai import OpenAI

# Add the project root to the Python path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import ModelManager from project root
from model_manager import ModelManager

class LLMInterface:
    """
    Interface for interacting with LLMs, specifically configured for OpenAI models
    with proxy settings behind a firewall.
    
    This class handles ONLY the communication with LLM APIs, providing a consistent
    interface regardless of the underlying model being used.
    
    Key features:
    - Automatically detects and adapts to model-specific limitations
    - Converts system messages to user messages for models that don't support system roles
    - Handles temperature restrictions for models with fixed temperature requirements
    - Provides a consistent API across different OpenAI models
    """
    
    # OpenAI proxy configuration from InteractiveChat
    OPENAI_PROXY = {
        "http": "http://testai:testai@192.168.1.7:6666",
        "https": "http://testai:testai@192.168.1.7:6666"
    }
    
    # Models with specific limitations
    MODELS_WITHOUT_SYSTEM_ROLE = ["o1-mini", "gpt-o1-mini"]
    MODELS_WITH_FIXED_TEMPERATURE = ["o1-mini", "gpt-o1-mini", "o3-mini", "gpt-o3-mini"]
    
    def __init__(self, config_path: Optional[str] = None, model_key: str = "gpt-o1-mini"):
        """
        Initialize the LLM interface with specified configuration.
        
        Args:
            config_path: Path to the config.json file, if None will use default location
            model_key: The model key to use from config.json (default: "gpt-o1-mini")
        """
        # Initialize ModelManager to access configuration
        self.model_manager = ModelManager(config_path)
        
        # Select the model to use
        self.current_model = model_key  # Default to gpt-o1-mini as used in the config
        self.current_model_config = self.model_manager.get_model_config(self.current_model)
        
        if not self.current_model_config:
            available_models = list(self.model_manager.available_models.keys())
            raise ValueError(f"Model '{model_key}' not found in configuration. Available models: {available_models}")
            
        # Verify this is an OpenAI model
        if self.current_model_config.get("provider") != "openai":
            raise ValueError(f"Model '{model_key}' is not an OpenAI model. Provider: {self.current_model_config.get('provider')}")
        
        # Set up proxy for OpenAI
        os.environ["HTTP_PROXY"] = self.OPENAI_PROXY["http"]
        os.environ["HTTPS_PROXY"] = self.OPENAI_PROXY["https"]
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.current_model_config["api_key"])
        
        # Get actual model name to use with the API
        self.model_name = self.current_model_config["config"]["name"]
        print(f"LLMInterface initialized with model: {self.model_name}")
        
        # Check for model-specific limitations
        self.supports_system_role = self.model_name not in self.MODELS_WITHOUT_SYSTEM_ROLE
        self.has_fixed_temperature = self.model_name in self.MODELS_WITH_FIXED_TEMPERATURE

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, 
                         temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        """
        Generate a response from the LLM using a simple prompt.
        
        For models that don't support system roles (like gpt-o1-mini), the system_prompt
        will be automatically converted and prepended to the user prompt.
        
        Args:
            prompt: The user's prompt to send to the model
            system_prompt: Optional system message to guide the model's behavior
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
                         Note: Some models only support the default temperature of 1.0
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            The model's response as a string
        """
        messages = []
        
        if system_prompt:
            if self.supports_system_role:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # For models that don't support system roles, prepend to user message
                prompt = f"[System instruction: {system_prompt}]\n\n{prompt}"
        
        messages.append({"role": "user", "content": prompt})
        
        return self.generate_chat_response(messages, temperature, max_tokens)
    
    def generate_chat_response(self, messages: List[Dict[str, str]], 
                              temperature: float = 0.7, 
                              max_tokens: Optional[int] = None) -> str:
        """
        Generate a response from the LLM using a conversation history.
        
        This method automatically adapts messages and parameters based on model limitations:
        - For models without system role support, system messages are converted to user messages
        - For models with fixed temperature, the temperature parameter is omitted
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
                         Note: Some models only support the default temperature of 1.0
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            The model's response as a string
        """
        try:
            # For models without system role support, convert system messages to user messages
            if not self.supports_system_role:
                converted_messages = []
                system_instructions = []
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_instructions.append(msg["content"])
                    else:
                        converted_messages.append(msg)
                
                # If there were system messages, prepend them to the first user message
                if system_instructions and converted_messages:
                    for i, msg in enumerate(converted_messages):
                        if msg["role"] == "user":
                            system_text = "\n\n".join(system_instructions)
                            converted_messages[i]["content"] = f"[System instructions: {system_text}]\n\n{msg['content']}"
                            break
                
                messages = converted_messages
            
            # Prepare the request parameters
            params: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages
            }
            
            # Add temperature only for models that support it
            if not self.has_fixed_temperature:
                params["temperature"] = temperature
            
            # Add max_tokens if specified
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            print(f"Sending request to {self.model_name}...")
            response = self.client.chat.completions.create(**params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating response: {e}")
            raise

    def close(self):
        """
        Clean up resources when done with the interface.
        """
        # Current OpenAI client doesn't require explicit cleanup,
        # but including this method for future-proofing and consistency
        # with the resource management pattern
        pass


# Example usage
if __name__ == "__main__":
    try:
        # Initialize the interface
        llm = LLMInterface()
        
        # Test a simple prompt
        response = llm.generate_response(
            prompt="Hello, can you hear me?",
            temperature=0.7
        )
        print("\nResponse to test prompt:")
        print(response)
        
    except Exception as e:
        print(f"Error in example usage: {e}")
        import traceback
        traceback.print_exc() 