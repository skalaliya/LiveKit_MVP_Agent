#!/usr/bin/env python3
"""
🔧 ElevenLabs API Key Permission Test
Test what your API key can actually do
"""

import asyncio
import os
from pathlib import Path


async def test_api_permissions():
    """Test what the API key can access."""
    
    print("🔧 ElevenLabs API Key Permission Test")
    print("=" * 45)
    
    # Get the new API key
    api_key = "sk_3117257089bbb45601ba47b20e10e41774b8d8625510536e"
    print(f"✅ Testing API Key: {api_key[:15]}...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"xi-api-key": api_key}
            
            # Test each endpoint to see what works
            tests = [
                ("User Info", "GET", "https://api.elevenlabs.io/v1/user"),
                ("Voices List", "GET", "https://api.elevenlabs.io/v1/voices"),
                ("Models List", "GET", "https://api.elevenlabs.io/v1/models"),
                ("STT Models", "GET", "https://api.elevenlabs.io/v1/speech-to-text/models"),
            ]
            
            results = {}
            
            for name, method, url in tests:
                try:
                    if method == "GET":
                        async with session.get(url, headers=headers) as response:
                            status = response.status
                            if status == 200:
                                data = await response.json()
                                results[name] = f"✅ SUCCESS ({len(str(data))} chars)"
                            else:
                                error = await response.text()
                                results[name] = f"❌ FAILED ({status})"
                                
                except Exception as e:
                    results[name] = f"❌ ERROR: {e}"
                    
                await asyncio.sleep(0.5)  # Rate limiting
            
            print("\n📊 Permission Test Results:")
            print("-" * 30)
            for test_name, result in results.items():
                print(f"{test_name:15}: {result}")
            
            # Test basic TTS (this usually works even with limited keys)
            print(f"\n🗣️ Testing Basic TTS...")
            
            # Use a known public voice ID for Rachel
            voice_id = "21m00Tcm4TlvDq8ikWAM"
            
            tts_data = {
                "text": "Hello! Testing new API key permissions.",
                "model_id": "eleven_flash_v2_5",
            }
            
            async with session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=tts_data
            ) as response:
                
                if response.status == 200:
                    audio_data = await response.read()
                    
                    with open("new_key_test.mp3", "wb") as f:
                        f.write(audio_data)
                    
                    print(f"✅ TTS SUCCESS: Generated {len(audio_data):,} bytes")
                    print(f"🎵 Audio saved: new_key_test.mp3")
                    
                else:
                    error = await response.text()
                    print(f"❌ TTS FAILED: {response.status} - {error}")
            
    except ImportError:
        print("❌ aiohttp not available")
    except Exception as e:
        print(f"❌ Test failed: {e}")


async def test_simple_endpoints():
    """Test simpler endpoints that might work."""
    
    print("\n🎯 Testing Simple Endpoints")
    print("=" * 30)
    
    api_key = "sk_3117257089bbb45601ba47b20e10e41774b8d8625510536e"
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"xi-api-key": api_key}
            
            # Test the most basic endpoint
            print("Testing basic API connectivity...")
            
            async with session.get(
                "https://api.elevenlabs.io/v1/models",
                headers=headers
            ) as response:
                
                print(f"Models endpoint: {response.status}")
                
                if response.status == 200:
                    models = await response.json()
                    print(f"✅ Available models: {len(models)}")
                    
                    for model in models[:3]:  # Show first 3
                        name = model.get("name", "Unknown")
                        model_id = model.get("model_id", "")
                        print(f"   - {name} ({model_id})")
                        
                else:
                    error = await response.text()
                    print(f"❌ Models failed: {error}")
                    
    except Exception as e:
        print(f"❌ Simple test failed: {e}")


def check_env_update():
    """Verify the .env file was updated."""
    
    print("\n📁 Checking .env File Update")
    print("=" * 32)
    
    env_file = Path(__file__).parent.parent / ".env"
    
    if env_file.exists():
        content = env_file.read_text()
        
        if "sk_3117257089bbb45601ba47b20e10e41774b8d8625510536e" in content:
            print("✅ New API key found in .env file")
            
            # Show the ElevenLabs section
            lines = content.splitlines()
            in_elevenlabs = False
            
            for line in lines:
                if "ElevenLabs" in line and "#" in line:
                    in_elevenlabs = True
                    print(f"📝 {line}")
                elif in_elevenlabs and line.strip() and not line.startswith("#"):
                    if "ELEVENLABS" in line:
                        print(f"📝 {line}")
                    else:
                        break
        else:
            print("❌ New API key not found in .env file")
    else:
        print("❌ .env file not found")


async def main():
    """Run all tests."""
    
    check_env_update()
    await test_api_permissions()
    await test_simple_endpoints()
    
    print("\n" + "="*50)
    print("🎯 Summary:")
    print("- Testing new API key permissions")
    print("- Some features may be restricted on free tier")
    print("- TTS should work even with limited permissions")
    print("- STT and voices may require paid subscription")
    print("\n💡 If TTS works, your voice agent is ready!")


if __name__ == "__main__":
    asyncio.run(main())