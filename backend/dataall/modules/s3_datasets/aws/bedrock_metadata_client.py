import logging
import os

from dataall.base.db import exceptions
from dataall.base.aws.sts import SessionHelper
from typing import List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel
from langchain_aws import ChatBedrock as BedrockChat
from langchain_core.output_parsers import JsonOutputParser

log = logging.getLogger(__name__)

METADATA_GENERATION_DATASET_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), 'bedrock_prompts', 'metadata_generation_dataset_template.txt'
)
METADATA_GENERATION_TABLE_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), 'bedrock_prompts', 'metadata_generation_table_template.txt'
)
METADATA_GENERATION_FOLDER_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), 'bedrock_prompts', 'metadata_generation_folder_template.txt'
)


class MetadataOutput(BaseModel):
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    label: Optional[str] = None
    topics: Optional[List[str]] = None
    columns_metadata: Optional[List[dict]] = None


class BedrockClient:
    def __init__(self):
        session = SessionHelper.get_session()
        self._client = session.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'eu-west-1'))
        model_id = 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0'
        model_kwargs = {
            'max_tokens': 4096,
            'temperature': 0.5,
            'top_k': 250,
            'top_p': 0.5,
            'stop_sequences': ['\n\nHuman'],
        }
        self._model = BedrockChat(client=self._client, model_id=model_id, model_kwargs=model_kwargs)

    def invoke_model_dataset_metadata(self, metadata_types, dataset, tables, folders):
        try:
            prompt_template = PromptTemplate.from_file(METADATA_GENERATION_DATASET_TEMPLATE_PATH)
            parser = JsonOutputParser(pydantic_object=MetadataOutput)
            chain = prompt_template | self._model | parser
            context = {
                'metadata_types': metadata_types,
                'dataset_label': dataset.label,
                'description': dataset.description,
                'tags': dataset.tags,
                'topics': dataset.topics,
                'table_names': [t.label for t in tables],
                'table_descriptions': [t.description for t in tables],
                'folder_names': [f.label for f in folders],
            }
            return chain.invoke(context)
        except Exception as e:
            raise e

    def invoke_model_table_metadata(self, metadata_types, table, columns, sample_data, generate_columns_metadata=False):
        try:
            prompt_template = PromptTemplate.from_file(METADATA_GENERATION_TABLE_TEMPLATE_PATH)
            parser = JsonOutputParser(pydantic_object=MetadataOutput)
            chain = prompt_template | self._model | parser
            context = {
                'metadata_types': metadata_types,
                'generate_columns_metadata': generate_columns_metadata,
                'label': table.label,
                'description': table.description,
                'tags': table.tags,
                'topics': table.topics,
                'column_labels': [c.label for c in columns],
                'column_descriptions': [c.description for c in columns],
                'sample_data': sample_data,
            }
            return chain.invoke(context)
        except Exception as e:
            raise e

    def invoke_model_folder_metadata(self, metadata_types, folder, files):
        try:
            prompt_template = PromptTemplate.from_file(METADATA_GENERATION_FOLDER_TEMPLATE_PATH)
            parser = JsonOutputParser(pydantic_object=MetadataOutput)
            chain = prompt_template | self._model | parser
            context = {
                'metadata_types': metadata_types,
                'label': folder.label,
                'description': folder.description,
                'tags': folder.tags,
                'topics': folder.topics,
                'file_names': files,
            }
            return chain.invoke(context)
        except Exception as e:
            raise e
