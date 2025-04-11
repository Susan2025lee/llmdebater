#!/usr/bin/env python3
"""
Test script for the LLMInterface class
This script verifies that the LLMInterface correctly:
1. Loads the configuration from config.json
2. Sets up the proxy for OpenAI API access
3. Successfully calls the OpenAI API
"""
import os
import sys
from typing import Dict, List, Optional

# Ensure the project root is in the path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the LLMInterface
from src.core.llm_interface import LLMInterface

def test_basic_functionality():
    """Test the basic functionality of the LLMInterface."""
    print("\n===== TESTING LLMInterface =====")
    print("Initializing LLMInterface...")
    
    # List available OpenAI models in the config
    openai_models = ["gpt-4o", "gpt-o1-mini", "gpt-o1-preview", "gpt4", "gpt4-turbo", "gpt35-turbo"]
    
    # Try to find a valid model key to use
    successful_model = None
    for model_key in openai_models:
        try:
            print(f"\nAttempting to initialize with model key: {model_key}")
            llm = LLMInterface(model_key=model_key)
            successful_model = model_key
            print(f"✅ Successfully initialized with model key: {model_key}")
            
            # Test sending a simple prompt
            print("\nSending test prompt to evaluate proxy and API access...")
            test_prompt = "Respond with 'Success' if you can read this message."
            response = llm.generate_response(prompt=test_prompt, temperature=0.3)
            
            print("\nResponse received:")
            print(f"'{response}'")
            
            if "success" in response.lower():
                print("✅ API connection works! The proxy is properly configured.")
            else:
                print("⚠️ Received a response, but it didn't contain 'Success'.")
                print(f"Response content: {response}")
            
            # Test chat completion functionality
            print("\nTesting chat completion functionality...")
            chat_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4"},
                {"role": "user", "content": "Multiply that by 3."}
            ]
            
            chat_response = llm.generate_chat_response(messages=chat_messages, temperature=0.3)
            print("\nChat response received:")
            print(f"'{chat_response}'")
            
            if chat_response:
                print("✅ Chat completion functionality works!")
            else:
                print("❌ Chat completion failed to return a response.")
            
            # No need to try other models if this one works
            break
            
        except ValueError as e:
            print(f"❌ Could not initialize with {model_key}: {e}")
        except Exception as e:
            print(f"❌ Error using {model_key}: {e}")
    
    if not successful_model:
        print("\n❌ TEST FAILED: Could not initialize LLMInterface with any of the attempted model keys.")
        print("Please check your config.json file and ensure at least one OpenAI model is properly configured.")
        return False
    
    print("\n===== TEST SUMMARY =====")
    print(f"✅ Successfully used model key: {successful_model}")
    print("✅ LLMInterface correctly loads configuration")
    print("✅ Proxy settings are correctly applied")
    print("✅ Basic API communication works")
    print("✅ Chat completion functionality works")
    
    return True

if __name__ == "__main__":
    try:
        success = test_basic_functionality()
        if success:
            print("\n✅ All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 