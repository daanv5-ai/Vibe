try:
    from google import genai
    print("google-genai (new SDK) is available")
except ImportError:
    print("google-genai (new SDK) is NOT available")

try:
    import google.generativeai as old_genai
    print("google-generativeai (old SDK) is available")
except ImportError:
    print("google-generativeai (old SDK) is NOT available")
