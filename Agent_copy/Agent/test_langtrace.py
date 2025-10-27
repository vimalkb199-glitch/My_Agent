import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
LANGTRACE_AVAILABLE=True
# Test Langtrace connection
try:
    from langtrace_python_sdk import langtrace
    
    # Initialize with your API key
    api_key = os.getenv('LANGTRACE_API_KEY')
    print(f"API Key loaded: {'Yes' if api_key else 'No'}")
    print(f"API Key (first 10 chars): {api_key[:10] if api_key else 'None'}")
    
    # Initialize Langtrace
    langtrace.init(api_key=api_key)
    print("Langtrace initialized successfully")
    
    # Test a simple trace
    from langtrace_python_sdk.utils.with_root_span import with_langtrace_root_span
    
    @with_langtrace_root_span("test_trace")
    def test_function():
        print("Test function executed")
        return {"status": "success", "message": "Test completed"}
    
    result = test_function()
    print(f"Test result: {result}")
    
    print("SUCCESS: Langtrace test completed successfully!")
    print("Check your Langtrace dashboard at https://langtrace.ai for the 'test_trace' entry")
    
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
except Exception as e:
    print(f"ERROR: {e}")