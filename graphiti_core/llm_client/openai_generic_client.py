"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import logging
import typing
from typing import ClassVar

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from ..prompts.models import Message
from .client import LLMClient, get_extraction_language_instruction
from .config import DEFAULT_MAX_TOKENS, LLMConfig, ModelSize
from .errors import RateLimitError, RefusalError

# Import trace context utility
try:
    from graphiti_core.utils.trace_context import TraceContext
    TRACE_AVAILABLE = True
except ImportError:
    TRACE_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'gpt-4.1-mini'


def _get_trace_logger():
    """Get a trace-aware logger if available, otherwise return the regular logger."""
    if TRACE_AVAILABLE:
        return TraceContext.get_logger_with_trace(__name__)
    return logger


class OpenAIGenericClient(LLMClient):
    """
    OpenAIClient is a client class for interacting with OpenAI's language models.

    This class extends the LLMClient and provides methods to initialize the client,
    get an embedder, and generate responses from the language model.

    Attributes:
        client (AsyncOpenAI): The OpenAI client used to interact with the API.
        model (str): The model name to use for generating responses.
        temperature (float): The temperature to use for generating responses.
        max_tokens (int): The maximum number of tokens to generate in a response.

    Methods:
        __init__(config: LLMConfig | None = None, cache: bool = False, client: typing.Any = None):
            Initializes the OpenAIClient with the provided configuration, cache setting, and client.

        _generate_response(messages: list[Message]) -> dict[str, typing.Any]:
            Generates a response from the language model based on the provided messages.
    """

    # Class-level constants
    MAX_RETRIES: ClassVar[int] = 2

    def __init__(
        self, config: LLMConfig | None = None, cache: bool = False, client: typing.Any = None
    ):
        """
        Initialize the OpenAIClient with the provided configuration, cache setting, and client.

        Args:
            config (LLMConfig | None): The configuration for the LLM client, including API key, model, base URL, temperature, and max tokens.
            cache (bool): Whether to use caching for responses. Defaults to False.
            client (Any | None): An optional async client instance to use. If not provided, a new AsyncOpenAI client is created.

        """
        # removed caching to simplify the `generate_response` override
        if cache:
            raise NotImplementedError('Caching is not implemented for OpenAI')

        if config is None:
            config = LLMConfig()

        super().__init__(config, cache)

        if client is None:
            self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
        else:
            self.client = client

    def _is_schema_structure(self, obj: dict) -> bool:
        """Check if a dictionary represents a JSON schema structure."""
        schema_indicators = {
            'type', 'anyOf', 'oneOf', 'allOf', 'properties', 'items', 
            'description', 'title', 'default', '$schema', 'definitions'
        }
        return isinstance(obj, dict) and any(key in schema_indicators for key in obj.keys())

    def _extract_value_from_schema_structure(self, schema: dict) -> typing.Any:
        """Extract a usable value from a JSON schema structure."""
        # Try to get the default value first
        if 'default' in schema:
            logger.info(f"Extracting default value: {schema['default']}")
            return schema['default']
        
        # Special case: if this looks like a summary field and description contains the actual content
        # (not just a field description), use the description as the value
        if ('title' in schema and schema.get('title', '').lower() == 'summary' and 
            'description' in schema and 'type' in schema and schema['type'] == 'string'):
            description = schema['description']
            # Check if description looks like actual content rather than a field description
            if (len(description) > 50 and not description.lower().startswith('summary') and 
                not description.lower().startswith('description')):
                logger.info(f"Extracting summary content from description: {description[:100]}...")
                return description
        
        # If no default, try to infer from type
        if 'type' in schema:
            schema_type = schema['type']
            if schema_type == 'string':
                return ""
            elif schema_type == 'integer':
                return 0
            elif schema_type == 'number':
                return 0.0
            elif schema_type == 'boolean':
                return False
            elif schema_type == 'array':
                return []
            elif schema_type == 'object':
                return {}
        
        # Handle anyOf, oneOf patterns
        if 'anyOf' in schema and isinstance(schema['anyOf'], list):
            for option in schema['anyOf']:
                if isinstance(option, dict) and 'default' in option:
                    logger.info(f"Extracting anyOf default value: {option['default']}")
                    return option['default']
                if isinstance(option, dict) and 'type' in option:
                    if option['type'] != 'null':  # Prefer non-null types
                        return self._extract_value_from_schema_structure(option)
        
        if 'oneOf' in schema and isinstance(schema['oneOf'], list):
            for option in schema['oneOf']:
                if isinstance(option, dict) and 'default' in option:
                    logger.info(f"Extracting oneOf default value: {option['default']}")
                    return option['default']
                if isinstance(option, dict) and 'type' in option:
                    if option['type'] != 'null':  # Prefer non-null types
                        return self._extract_value_from_schema_structure(option)
        
        # If all else fails, return None
        logger.warning(f"Could not extract value from schema, returning None: {schema}")
        return None

    def _clean_schema_response(self, response: dict) -> dict:
        """Recursively clean schema structures from the response."""
        cleaned_response = {}
        
        for key, value in response.items():
            if isinstance(value, dict):
                # Check if this dict is a schema structure
                if self._is_schema_structure(value):
                    # Found a schema structure - extract the actual value
                    extracted_value = self._extract_value_from_schema_structure(value)
                    cleaned_response[key] = extracted_value
                    _get_trace_logger().info(f"Found schema structure for '{key}', extracted: {extracted_value}")
                else:
                    # Check for nested schema structures (like in 'properties' field)
                    if key == 'properties' and isinstance(value, dict):
                        # This is likely a schema properties object, extract the actual values
                        extracted_properties = {}
                        for prop_key, prop_value in value.items():
                            if isinstance(prop_value, dict) and self._is_schema_structure(prop_value):
                                extracted_val = self._extract_value_from_schema_structure(prop_value)
                                extracted_properties[prop_key] = extracted_val
                                _get_trace_logger().info(f"Found nested schema in properties for '{prop_key}', extracted: {extracted_val}")
                            else:
                                extracted_properties[prop_key] = prop_value
                        # Return the extracted properties directly instead of nesting under 'properties'
                        cleaned_response.update(extracted_properties)
                    else:
                        # Recursively clean nested dicts
                        cleaned_response[key] = self._clean_schema_response(value)
            elif isinstance(value, list):
                # Clean lists that might contain schema structures
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_list.append(self._clean_schema_response(item))
                    else:
                        cleaned_list.append(item)
                cleaned_response[key] = cleaned_list
            else:
                cleaned_response[key] = value
        
        return cleaned_response

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, typing.Any]:
        trace_logger = _get_trace_logger()
        trace_logger.info(f"OpenAI Generic Client _generate_response called with {len(messages)} messages")
        openai_messages: list[ChatCompletionMessageParam] = []
        for m in messages:
            m.content = self._clean_input(m.content)
            if m.role == 'user':
                openai_messages.append({'role': 'user', 'content': m.content})
            elif m.role == 'system':
                openai_messages.append({'role': 'system', 'content': m.content})
        try:
            # Prepare request parameters
            kwargs = {
                'model': self.model or DEFAULT_MODEL,
                'messages': openai_messages,
                'max_tokens': self.max_tokens,
                'response_format': {'type': 'json_object'},
            }
            
            # Only include temperature if the model supports it (GPT-5 models don't)
            if not (self.model or DEFAULT_MODEL).startswith('gpt-5'):
                kwargs['temperature'] = self.temperature
            else:
                # GPT-5 models use reasoning_effort instead of temperature
                kwargs['reasoning_effort'] = 'minimal'
            
            response = await self.client.chat.completions.create(**kwargs)
            result = response.choices[0].message.content or ''
            return json.loads(result)
        except openai.RateLimitError as e:
            raise RateLimitError from e
        except Exception as e:
            logger.error(f'Error in generating LLM response: {e}')
            raise

    async def generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int | None = None,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, typing.Any]:
        if max_tokens is None:
            max_tokens = self.max_tokens

        retry_count = 0
        last_error = None

        if response_model is not None:
            serialized_model = json.dumps(response_model.model_json_schema())
            messages[
                -1
            ].content += (
                f'\n\nRespond with a JSON object in the following format:\n\n{serialized_model}'
            )

        # Add multilingual extraction instructions
        messages[0].content += get_extraction_language_instruction()

        while retry_count <= self.MAX_RETRIES:
            try:
                response = await self._generate_response(
                    messages, response_model, max_tokens=max_tokens, model_size=model_size
                )
                # Clean any schema structures from the response
                trace_logger = _get_trace_logger()
                trace_logger.info(f"OpenAI Generic Client - Raw response: {response}")
                    
                if isinstance(response, dict):
                    cleaned_response = self._clean_schema_response(response)
                    trace_logger.info(f"OpenAI Generic Client - Cleaned response: {cleaned_response}")
                    return cleaned_response
                return response
            except (RateLimitError, RefusalError):
                # These errors should not trigger retries
                raise
            except (openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError):
                # Let OpenAI's client handle these retries
                raise
            except Exception as e:
                last_error = e

                # Don't retry if we've hit the max retries
                if retry_count >= self.MAX_RETRIES:
                    logger.error(f'Max retries ({self.MAX_RETRIES}) exceeded. Last error: {e}')
                    raise

                retry_count += 1

                # Construct a detailed error message for the LLM
                error_context = (
                    f'The previous response attempt was invalid. '
                    f'Error type: {e.__class__.__name__}. '
                    f'Error details: {str(e)}. '
                    f'Please try again with a valid response, ensuring the output matches '
                    f'the expected format and constraints.'
                )

                error_message = Message(role='user', content=error_context)
                messages.append(error_message)
                logger.warning(
                    f'Retrying after application error (attempt {retry_count}/{self.MAX_RETRIES}): {e}'
                )

        # If we somehow get here, raise the last error
        raise last_error or Exception('Max retries exceeded with no specific error')
