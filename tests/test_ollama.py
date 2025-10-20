"""
Test Ollama LLM functionality
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from livekit_mvp_agent.adapters.llm_ollama import OllamaLLM


class TestOllamaLLM:
    """Test Ollama LLM functionality"""
    
    @pytest.fixture
    def llm(self):
        """Create LLM instance for testing"""
        return OllamaLLM(
            base_url="http://localhost:11434",
            model="test-model",
            fallback_model="test-fallback",
            timeout=10.0
        )
    
    def test_llm_initialization(self, llm):
        """Test LLM initialization"""
        assert llm.base_url == "http://localhost:11434"
        assert llm.model == "test-model" 
        assert llm.fallback_model == "test-fallback"
        assert llm.timeout == 10.0
        assert not llm.initialized
    
    @pytest.mark.asyncio
    async def test_mock_initialization(self, llm):
        """Test mock LLM initialization when httpx not available"""
        # This test assumes we're using the mock implementation
        # when httpx is not available
        
        try:
            await llm.initialize()
            # If using mock, this should succeed
            assert llm.initialized
        except ImportError:
            # If using real implementation but httpx not available
            pytest.skip("httpx not available for real Ollama testing")
    
    @pytest.mark.asyncio
    async def test_chat_functionality(self, llm):
        """Test chat functionality"""
        await llm.initialize()
        
        messages = [
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        response = await llm.chat(messages)
        
        # Should get some response (even if mock)
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_generate_functionality(self, llm):
        """Test text generation"""
        await llm.initialize()
        
        prompt = "Explain what a voice agent is."
        
        response = await llm.generate(prompt)
        
        # Should get a response
        assert response is not None
        assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_system_prompt(self, llm):
        """Test generation with system prompt"""
        await llm.initialize()
        
        system_prompt = "You are a helpful assistant."
        user_prompt = "What is AI?"
        
        response = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        assert response is not None
        assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_conversation_history(self, llm):
        """Test maintaining conversation history"""
        await llm.initialize()
        
        # First message
        messages1 = [
            {"role": "user", "content": "My name is John."}
        ]
        
        response1 = await llm.chat(messages1)
        assert response1 is not None
        
        # Follow-up message
        messages2 = [
            {"role": "user", "content": "My name is John."},
            {"role": "assistant", "content": response1},
            {"role": "user", "content": "What is my name?"}
        ]
        
        response2 = await llm.chat(messages2)
        assert response2 is not None
    
    @pytest.mark.asyncio
    async def test_empty_messages(self, llm):
        """Test handling of empty messages"""
        await llm.initialize()
        
        # Empty messages list
        response = await llm.chat([])
        
        # Should handle gracefully (may return None or empty string)
        assert response is None or isinstance(response, str)
    
    def test_available_models(self, llm):
        """Test getting available models list"""
        models = llm.get_available_models()
        
        # Should return a list (even if empty or mock)
        assert isinstance(models, list)
    
    @pytest.mark.asyncio
    async def test_client_cleanup(self, llm):
        """Test proper client cleanup"""
        await llm.initialize()
        
        # Should be able to close without errors
        await llm.close()
        
        # After closing, should not be initialized
        assert not llm.initialized


class TestOllamaLLMEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors"""
        # Use non-existent URL
        llm = OllamaLLM(base_url="http://nonexistent:9999")
        
        # Should handle connection errors gracefully
        try:
            await llm.initialize()
            # Mock implementation should still work
            assert llm.initialized
        except ConnectionError:
            # Real implementation should raise ConnectionError
            pass
    
    @pytest.mark.asyncio
    async def test_invalid_model_handling(self):
        """Test handling of invalid model names"""
        llm = OllamaLLM(model="nonexistent-model")
        
        await llm.initialize()
        
        messages = [{"role": "user", "content": "Test"}]
        response = await llm.chat(messages)
        
        # Should handle gracefully (mock will work, real might fail)
        assert response is None or isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_large_message_handling(self):
        """Test handling of large messages"""
        llm = OllamaLLM()
        await llm.initialize()
        
        # Create a very long message
        long_content = "This is a test. " * 1000  # ~15k characters
        
        messages = [{"role": "user", "content": long_content}]
        
        response = await llm.chat(messages)
        
        # Should handle large messages
        assert response is None or isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_special_characters_handling(self):
        """Test handling of special characters in messages"""
        llm = OllamaLLM()
        await llm.initialize()
        
        # Message with special characters
        special_content = "Hello! 🚀 This has émojis and àccénts. ¿Cómo estás? 中文 日本語"
        
        messages = [{"role": "user", "content": special_content}]
        
        response = await llm.chat(messages)
        
        # Should handle special characters
        assert response is None or isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        llm = OllamaLLM()
        await llm.initialize()
        
        # Create multiple concurrent requests
        messages_list = [
            [{"role": "user", "content": f"Request {i}"}]
            for i in range(3)
        ]
        
        # Send requests concurrently
        tasks = [llm.chat(messages) for messages in messages_list]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle concurrent requests
        assert len(responses) == 3
        
        for response in responses:
            assert (response is None or 
                   isinstance(response, str) or 
                   isinstance(response, Exception))


class TestOllamaLLMConfiguration:
    """Test configuration and parameter handling"""
    
    def test_temperature_setting(self):
        """Test temperature parameter"""
        llm = OllamaLLM(temperature=0.9)
        assert llm.temperature == 0.9
    
    def test_max_tokens_setting(self):
        """Test max_tokens parameter"""
        llm = OllamaLLM(max_tokens=256)
        assert llm.max_tokens == 256
    
    def test_fallback_model_configuration(self):
        """Test fallback model configuration"""
        llm = OllamaLLM(
            model="primary-model",
            fallback_model="backup-model"
        )
        
        assert llm.model == "primary-model"
        assert llm.fallback_model == "backup-model"
    
    def test_base_url_normalization(self):
        """Test base URL normalization"""
        # URL with trailing slash
        llm1 = OllamaLLM(base_url="http://localhost:11434/")
        assert llm1.base_url == "http://localhost:11434"
        
        # URL without trailing slash
        llm2 = OllamaLLM(base_url="http://localhost:11434")
        assert llm2.base_url == "http://localhost:11434"


@pytest.mark.integration
class TestOllamaLLMIntegration:
    """Integration tests (require actual Ollama server)"""
    
    @pytest.mark.asyncio
    async def test_real_ollama_connection(self):
        """Test real connection to Ollama server"""
        llm = OllamaLLM()
        
        try:
            await llm.initialize()
            
            # If we get here, Ollama is available
            messages = [{"role": "user", "content": "Hello"}]
            response = await llm.chat(messages)
            
            assert response is not None
            assert isinstance(response, str)
            
        except (ConnectionError, ImportError):
            pytest.skip("Ollama server not available or httpx not installed")
        finally:
            await llm.close()
    
    @pytest.mark.asyncio
    async def test_model_pulling(self):
        """Test model pulling functionality"""
        llm = OllamaLLM()
        
        try:
            await llm.initialize()
            
            # Try to pull a small test model
            success = await llm._pull_model("tiny-test-model")
            
            # May succeed or fail depending on model availability
            assert isinstance(success, bool)
            
        except (ConnectionError, ImportError):
            pytest.skip("Ollama server not available")
        finally:
            await llm.close()