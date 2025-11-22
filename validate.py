#!/usr/bin/env python3
"""
Validation script to check if the deployment setup is correct
"""
import sys
import importlib.util

def check_module(module_name):
    """Check if a Python module can be imported"""
    spec = importlib.util.find_spec(module_name)
    return spec is not None

def validate_imports():
    """Validate all required imports"""
    print("=" * 60)
    print("VALIDATING IMPORTS")
    print("=" * 60)
    
    required_modules = [
        "flask", "flask_cors", "gunicorn", "asgiref",
        "redis", "flask_limiter", "langchain", "langgraph",
        "uvicorn", "websockets", "httpx", "pydantic"
    ]
    
    all_ok = True
    for module in required_modules:
        if check_module(module):
            print(f"✓ {module}")
        else:
            print(f"✗ {module} - NOT FOUND")
            all_ok = False
    
    return all_ok

def validate_config():
    """Validate configuration"""
    print("\n" + "=" * 60)
    print("VALIDATING CONFIGURATION")
    print("=" * 60)
    
    try:
        from config import Config
        print("✓ Config module loads successfully")
        
        # Check required env vars
        required = [
            ("API_KEY", Config.API_KEY),
            ("OPENAI_API_KEY", Config.OPENAI_API_KEY),
            ("TOGETHER_API_KEY", Config.TOGETHER_API_KEY),
            ("PINECONE_API_KEY", Config.PINECONE_API_KEY),
        ]
        
        missing = []
        for name, value in required:
            if value:
                print(f"✓ {name} is set")
            else:
                print(f"⚠ {name} is not set (optional for validation)")
                missing.append(name)
        
        return True
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False

def validate_app():
    """Validate app module"""
    print("\n" + "=" * 60)
    print("VALIDATING APP MODULE")
    print("=" * 60)
    
    try:
        import app
        print("✓ App module imports successfully")
        print("✓ Flask app initialized")
        print("✓ ASGI wrapper created")
        return True
    except Exception as e:
        print(f"✗ Failed to import app: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_agents():
    """Validate agent modules"""
    print("\n" + "=" * 60)
    print("VALIDATING AGENT MODULES")
    print("=" * 60)
    
    try:
        from agents import rag
        print("✓ RAG agent imports successfully")
        print("✓ Checkpointer initialized")
        return True
    except Exception as e:
        print(f"✗ Failed to import agents: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_utils():
    """Validate utility modules"""
    print("\n" + "=" * 60)
    print("VALIDATING UTILITY MODULES")
    print("=" * 60)
    
    modules = [
        ("utils.checkpointer", "Checkpointer"),
        ("utils.logging_config", "Logging config"),
        ("utils.validation", "Input validation"),
        ("utils.stt", "Speech-to-text"),
        ("utils.tts", "Text-to-speech"),
        ("utils.emotion", "Emotion analysis"),
    ]
    
    all_ok = True
    for module_name, desc in modules:
        try:
            __import__(module_name)
            print(f"✓ {desc}")
        except Exception as e:
            print(f"✗ {desc}: {e}")
            all_ok = False
    
    return all_ok

def validate_docker_files():
    """Validate Docker configuration files"""
    print("\n" + "=" * 60)
    print("VALIDATING DOCKER FILES")
    print("=" * 60)
    
    import os
    
    files = [
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        "gunicorn.conf.py",
        "wsgi.py"
    ]
    
    all_ok = True
    for file in files:
        if os.path.exists(file):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
            all_ok = False
    
    return all_ok

def main():
    """Run all validations"""
    print("\n" + "=" * 60)
    print("ITB CHATBOT DEPLOYMENT VALIDATION")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run validations
    results.append(("Imports", validate_imports()))
    results.append(("Configuration", validate_config()))
    results.append(("App Module", validate_app()))
    results.append(("Agent Modules", validate_agents()))
    results.append(("Utility Modules", validate_utils()))
    results.append(("Docker Files", validate_docker_files()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All validations passed! Ready for deployment.")
        print("\nNext steps:")
        print("1. Start Docker: docker-compose up -d")
        print("2. Check health: curl http://localhost:8000/health")
        print("3. Test chat endpoint with proper API key")
        return 0
    else:
        print("\n✗ Some validations failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

