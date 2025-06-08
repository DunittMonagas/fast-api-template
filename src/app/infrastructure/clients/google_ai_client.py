"""Google AI client wrapper using Google Generative AI SDK."""
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import Settings

logger = logging.getLogger(__name__)


class GoogleAIClient:
    """Client for interacting with Google Generative AI."""

    def __init__(self, settings: Settings, model_name: str = "gemini-pro"):
        self.settings = settings
        self.model_name = model_name

        # Configure the API key
        genai.configure(api_key=settings.google_api_key)

        # Initialize the model
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Initialized Google AI client with model: {model_name}")

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """Generate text based on a prompt."""
        logger.info("Generating text with Google AI")

        try:
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                top_p=top_p,
                top_k=top_k,
                stop_sequences=stop_sequences,
            )

            # Generate response
            response = self.model.generate_content(prompt, generation_config=generation_config)

            # Extract text from response
            if response.parts:
                generated_text = response.parts[0].text
                logger.info("Text generated successfully")
                return generated_text
            else:
                raise Exception("No text generated")

        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """Generate a chat response based on conversation history."""
        logger.info("Generating chat response with Google AI")

        try:
            # Start a chat session
            chat = self.model.start_chat(history=[])

            # Process messages
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")

                if role == "user":
                    response = chat.send_message(content)
                # For assistant messages, we just add them to history context

            # Get the last response
            if response.parts:
                generated_text = response.parts[0].text
                logger.info("Chat response generated successfully")
                return generated_text
            else:
                raise Exception("No response generated")

        except Exception as e:
            logger.error(f"Failed to generate chat response: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text."""
        try:
            return self.model.count_tokens(text).total_tokens
        except Exception as e:
            logger.error(f"Failed to count tokens: {e}")
            raise

    def embed_text(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """Generate embeddings for text."""
        try:
            # Use the embedding model
            embedding_model = genai.GenerativeModel("models/embedding-001")
            result = genai.embed_content(
                model="models/embedding-001", content=text, task_type=task_type
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def check_health(self) -> bool:
        """Check if Google AI API is accessible."""
        try:
            # Try to count tokens as a health check
            self.count_tokens("test")
            return True
        except Exception as e:
            logger.error(f"Google AI health check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """List available models."""
        try:
            models = []
            for model in genai.list_models():
                if "generateContent" in model.supported_generation_methods:
                    models.append(model.name)
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise
