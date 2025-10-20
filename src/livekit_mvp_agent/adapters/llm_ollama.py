"""
Ollama LLM Adapter for local language model inference
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
import json

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class OllamaLLM:
    """
    Large Language Model adapter using Ollama
    
    Supports:
    - Local model inference
    - Streaming responses
    - Model fallback
    - Conversation history
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b-instruct-q4_K_M",
        fallback_model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        timeout: float = 30.0,
    ):
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is not installed. "
                "Install with: pip install httpx"
            )
        
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None
        self.initialized = False
        
        # Model availability cache
        self._available_models: List[str] = []
        self._model_checked = False
    
    async def initialize(self) -> None:
        """Initialize the Ollama client and check model availability"""
        if self.initialized:
            return
        
        try:
            self.logger.info("Initializing Ollama client...")
            
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=10)
            )
            
            # Check Ollama server availability
            await self._check_server()
            
            # Check model availability
            await self._check_models()
            
            self.initialized = True
            self.logger.info("Ollama client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama: {e}", exc_info=True)
            raise
    
    async def _check_server(self) -> None:
        """Check if Ollama server is running"""
        try:
            response = await self.client.get(f"{self.base_url}/api/version")
            response.raise_for_status()
            
            version_info = response.json()
            self.logger.info(f"Ollama server version: {version_info.get('version', 'unknown')}")
            
        except Exception as e:
            raise ConnectionError(f"Ollama server not available at {self.base_url}: {e}")
    
    async def _check_models(self) -> None:
        """Check which models are available"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            self._available_models = [model["name"] for model in data.get("models", [])]
            
            self.logger.info(f"Available models: {self._available_models}")
            
            # Check if primary model is available
            if self.model not in self._available_models:
                self.logger.warning(f"Primary model '{self.model}' not found")
                
                # Try to pull the model
                await self._pull_model(self.model)
            
            # Check fallback model
            if self.fallback_model and self.fallback_model not in self._available_models:
                self.logger.warning(f"Fallback model '{self.fallback_model}' not found")
            
            self._model_checked = True
            
        except Exception as e:
            self.logger.error(f"Failed to check models: {e}")
            # Continue without model check
    
    async def _pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Pulling model: {model_name}")
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=300.0  # 5 minutes for model download
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            status = json.loads(line)
                            if "status" in status:
                                self.logger.debug(f"Pull status: {status['status']}")
                        except json.JSONDecodeError:
                            continue
            
            self.logger.info(f"Successfully pulled model: {model_name}")
            
            # Update available models list
            if model_name not in self._available_models:
                self._available_models.append(model_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        stream: bool = False
    ) -> Optional[str]:
        """
        Send chat messages and get response
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (optional, uses default)
            stream: Whether to use streaming response
            
        Returns:
            Response text or None if failed
        """
        if not self.initialized:
            await self.initialize()
        
        # Choose model
        chosen_model = model or self.model
        
        # Try primary model first, then fallback
        for attempt_model in [chosen_model, self.fallback_model]:
            if not attempt_model:
                continue
            
            try:
                if stream:
                    return await self._chat_streaming(messages, attempt_model)
                else:
                    return await self._chat_single(messages, attempt_model)
                    
            except Exception as e:
                self.logger.warning(f"Chat failed with model {attempt_model}: {e}")
                continue
        
        self.logger.error("All chat attempts failed")
        return None
    
    async def _chat_single(self, messages: List[Dict[str, str]], model: str) -> Optional[str]:
        """Send single chat request"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
                "stream": False
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Single chat error: {e}")
            raise
    
    async def _chat_streaming(self, messages: List[Dict[str, str]], model: str) -> Optional[str]:
        """Send streaming chat request and collect response"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
                "stream": True
            }
            
            response_parts = []
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                response_parts.append(data["message"]["content"])
                                
                            if data.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
            return "".join(response_parts).strip() if response_parts else None
            
        except Exception as e:
            self.logger.error(f"Streaming chat error: {e}")
            raise
    
    async def chat_stream(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response token by token
        
        Args:
            messages: List of message dictionaries
            model: Model to use (optional)
            
        Yields:
            Response tokens as they arrive
        """
        if not self.initialized:
            await self.initialize()
        
        chosen_model = model or self.model
        
        try:
            payload = {
                "model": chosen_model,
                "messages": messages,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
                "stream": True
            }
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                if content:
                                    yield content
                                    
                            if data.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            self.logger.error(f"Chat stream error: {e}")
            # Try fallback model
            if self.fallback_model and chosen_model != self.fallback_model:
                async for token in self.chat_stream(messages, self.fallback_model):
                    yield token
    
    async def generate(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            model: Model to use (optional)
            system_prompt: System prompt (optional)
            
        Returns:
            Generated text or None if failed
        """
        # Convert to chat format
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat(messages, model)
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return self._available_models.copy()
    
    async def close(self) -> None:
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            self.initialized = False


class MockOllamaLLM:
    """Mock LLM for testing when httpx is not available"""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.initialized = False
    
    async def initialize(self) -> None:
        """Mock initialization"""
        self.logger.info("Mock Ollama LLM initialized")
        self.initialized = True
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        stream: bool = False
    ) -> Optional[str]:
        """Mock chat response"""
        last_message = messages[-1].get("content", "") if messages else ""
        response = f"Mock response to: {last_message[:50]}..."
        self.logger.debug(f"Mock LLM response: {response}")
        return response
    
    async def generate(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Mock generation"""
        return f"Mock response to prompt: {prompt[:50]}..."
    
    def get_available_models(self) -> List[str]:
        return ["mock-model"]
    
    async def close(self) -> None:
        pass


# Use mock if httpx is not available
if not HTTPX_AVAILABLE:
    OllamaLLM = MockOllamaLLM