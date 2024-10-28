from dataall.base.aws.sts import SessionHelper
from langchain_aws import ChatBedrock as BedrockChat
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from dataall.base.db import exceptions
import os

TEXT_TO_SQL_EXAMPLES_PATH = os.path.join(os.path.dirname(__file__), 'bedrock_prompts', 'text_to_sql_examples.txt')
TEXT_TO_SQL_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'bedrock_prompts', 'test_to_sql_template.txt')
PROCESS_TEXT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'bedrock_prompts', 'process_text_template.txt')


class BedrockClient:
    def __init__(self):
        self._session = SessionHelper.get_session()
        self._client = self._session.client('bedrock-runtime')
        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        model_kwargs = {
            'max_tokens': 2048,
            'temperature': 0,
            'top_k': 250,
            'top_p': 1,
            'stop_sequences': ['\n\nHuman'],
        }
        self._model = BedrockChat(
            client=self._client,
            model_id=model_id,
            model_kwargs=model_kwargs,
        )

    def invoke_model_text_to_sql(self, prompt: str, metadata: str):
        prompt_template = PromptTemplate.from_file(TEXT_TO_SQL_TEMPLATE_PATH)
        chain = prompt_template | self._model | StrOutputParser()

        with open(TEXT_TO_SQL_EXAMPLES_PATH, 'r') as f:
            examples = f.read()

        response = chain.invoke({'prompt': prompt, 'context': metadata, 'examples': examples})
        if response.startswith('Error:'):
            raise exceptions.ModelGuardrailException(response)
        return response

    def invoke_model_process_text(self, prompt: str, content: str):
        prompt_template = PromptTemplate.from_file(PROCESS_TEXT_TEMPLATE_PATH)

        chain = prompt_template | self._model | StrOutputParser()
        response = chain.invoke({'prompt': prompt, 'content': content})

        if response.startswith('Error:'):
            raise exceptions.ModelGuardrailException(response)
        return response
