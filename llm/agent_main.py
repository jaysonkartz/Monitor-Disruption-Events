import openai
import numpy as np
import os
from dotenv import load_dotenv
import os
from collections import deque
from typing import Dict, List, Optional, Any
from geopy.geocoders import Nominatim
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from langchain import LLMChain, OpenAI, PromptTemplate
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import BaseLLM
from langchain.vectorstores.base import VectorStore
from pydantic import BaseModel, Field
from langchain.chains.base import Chain
# Langchain
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Pinecone
from langchain.document_loaders import TextLoader
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA, LLMChain ,LLMCheckerChain
from langchain.callbacks import wandb_tracing_enabled
from langchain.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    StringPromptTemplate
)
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from typing import Optional
from langchain.chains import SimpleSequentialChain ,SequentialChain
from langchain.agents import AgentExecutor, Tool, ZeroShotAgent,BaseMultiActionAgent
from langchain.agents import AgentType, initialize_agent,AgentExecutor,BaseSingleActionAgent
from langchain.tools import tool
from langchain.chains.openai_functions import (
    create_openai_fn_chain,
    create_structured_output_chain,
)
from langchain.schema import HumanMessage, AIMessage, ChatMessage
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser,Agent
from langchain.prompts import StringPromptTemplate
from langchain import OpenAI, SerpAPIWrapper, LLMChain
from typing import List, Union
from langchain.schema import AgentAction, AgentFinish, OutputParserException
import re
from langchain.agents import Tool, AgentExecutor, BaseSingleActionAgent
from langchain import OpenAI, SerpAPIWrapper

from langchain.callbacks.manager import (
    AsyncCallbackManagerForChainRun,
    AsyncCallbackManagerForToolRun,
    CallbackManagerForChainRun,
    CallbackManagerForToolRun,
    Callbacks,
)
from newspaper import Config, Article, Source
import requests
from utils.Webscraper import Webscraper
import tiktoken

from supabase import create_client, Client
import postgrest
from postgrest.exceptions import APIError
import newspaper
import jsonschema
from jsonschema import ValidationError
import logging

webscraper = Webscraper()


from .chains import (
    articleClassifier,
    port_articleClassifer,
    locationExtractor,
    eventDetails,
)

from .tools import get_coordinates
from .utils import num_tokens_from_string, extract_json_schema
from colorlog import ColoredFormatter
import logging
formatter = ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
# Remove the default logger
logger.removeHandler(logger.handlers[0])

class outputValidator:
    """
    Validates json output of any llmchain, given that it's created with the create_structured_output_chain function
    Gives Feedback to the LLMChain to improve the output
    """
    @staticmethod
    def _getOutputSchemaMapping(LLMChain:LLMChain) -> dict:
        """Returns the supposed output schema of the given LLMChain 
        
        Example llm_kwargs:
        {'functions': [{'name': 'output_formatter',
   'description': 'Output formatter. Should always be used to format your response to the user.',
   'parameters': {'name': 'binary_classifier_article_schema',
    'description': 'Binary Classifier Schema for Article, 0 for False and 1 for True',
    'type': 'object',
    'properties': {'isDisruptionEvent': {'type': 'boolean'},
     'Reason': {'type': 'string'}},
    'required': ['isDisruptionEvent', 'Reason']}}],
    'function_call': {'name': 'output_formatter'}}
    """
        output_schema = LLMChain.llm_kwargs
        # Create a dictionary mapping with Key as Key and Value as type
        validator_json_schema = extract_json_schema(output_schema)
        return validator_json_schema
        
    @classmethod
    def validate(cls, LLMChain:LLMChain, output: dict) -> Tuple[bool, str]:
        """Validates the output of the given llmchain
        Args:
            JSON_SCHEMA (dict): The JSON Schema to validate
            output (dict): The output of the LLMChain
        Returns:
            Tuple[bool, str]: A tuple containing a boolean and a string. 
            The boolean is True if the output is valid according to the schema, False if not. 
            The string is the reason for the boolean value. If the boolean is True, the string will be empty.
            The string might be used to give feedback to LLMChain to improve the output.
        """
        # Check if the output is a dict
        if not isinstance(output,dict):
            return (False,"The output is not JSON object (dict)")
        # Get the output schema mapping
        JSON_SCHEMA = cls._getOutputSchemaMapping(LLMChain)
        
        try:
            # Create a validator based on the JSON_SCHEMA
            validator = jsonschema.Draft7Validator(JSON_SCHEMA)
            
            # Check if the output is valid
            errors = list(validator.iter_errors(output))
            
            if errors:
                error_messages = [str(error) for error in errors]
                return (False, ", ".join(error_messages))  # Output is invalid, return the validation error messages
            else:
                return (True, "")  # Output is valid
        except Exception as e:
            return (False, str(e))  # Handle any other exceptions that may occur
        
    @staticmethod
    def validateArticle(article: Article) -> Union[tuple[bool, str], tuple[bool, None]]:
        """Validates if article has all the cooresponding keys in the additional_data object for Insertion to Supabase
        Returns:
            Union[tuple[bool,str],tuple[bool,None]]: A tuple containing a boolean and a string. 
            The boolean is True if the article is valid, False if not. 
            The string is the key that's missing or not for the article
            If the boolean is True, the string will be empty.
        """
        # Check if article is a valid Article object
        if not isinstance(article, Article):
            return (False, "Article is not a valid Article object")
        # Check if article has all the required keys
        required_keys = ["location", "coordinates", "disruptionType", "radius", "severity"]
        for key in required_keys:
            if key not in article.additional_data.keys():
                return (False, f"Article is missing key: {key}")
        return (True, None)

class AgentMain:
    """Main Agent that Handles the LLM chaining of input and outputs for the Disruption Event Extraction"""
    binaryClassifier: LLMChain = articleClassifier
    binaryClassifier_port:LLMChain = port_articleClassifer
    locationExtractor: LLMChain = locationExtractor
    eventDetails: LLMChain = eventDetails 
    # The function to get the coordinates of a location
    get_coordinates: Callable = get_coordinates
    webscraper: Webscraper = webscraper
    article_token_threshold: int = 1500
    """The number of tokens to use the article summary instead of the full article"""
    @staticmethod
    def _articleExtraction(url) -> Article:
        """Extracts the article as a Article object from the given url"""
        try:
            article = webscraper.scrape(url)
        except Exception as e:
            raise Exception(f"News article Url:\n{url}\nCannot be scraped.Reason:\n{e}\nSkipping Article...")
        return article
    
    @staticmethod
    def _binaryClassifier(article: Article) -> dict:
        """Classifies if the given article is a valid disruption event article or not
        Always use summary instead of full article for token saving

        Returns:
            dict: A dictionary containing the classification result and the reason for the classification result
            Keys:
                isDisruptionEvent: bool
                Reason: str
                disruptionType: str

        Raises Exception if the binary classification fails
        """
        try:
            # Get number of tokens for the article
            result = AgentMain.binaryClassifier.run(articleTitle=article.title,articleText=article.summary, feedback="")

            # Validate the output
            validation_results = outputValidator.validate(AgentMain.binaryClassifier, result)
            if not validation_results[0]:
                print(f'_binaryClassifier Validation Error, Re-Running with feedback: {validation_results[1]}')
                # Re-run the validation error as feedback for the LLMChain
                result = AgentMain.binaryClassifier.run(articleTitle=article.title,articleText=article.text, feedback=validation_results[1])

        except Exception as e:
            raise Exception(f"Error: Binary Classification Failed -> {e}") from e
    
        return result
    @staticmethod
    def _locationExtractor(article: Article, feedback: str ="") -> str:
        """Extracts the location of the disruption event from the given article"""
        try:
            # Get number of tokens for the article
            num_tokens = num_tokens_from_string(article.text, "cl100k_base")
            if num_tokens > AgentMain.article_token_threshold:
                print(f'Article Length: {num_tokens} tokens, using article summary instead')
                result = AgentMain.locationExtractor.run(articleTitle=article.title,articleText=article.summary, feedback=feedback)
            else:
                result = AgentMain.locationExtractor.run(articleTitle=article.title,articleText=article.text, feedback=feedback)
            # Validate the output
            validation_results = outputValidator.validate(AgentMain.locationExtractor, result)

            if not validation_results[0]:
                # Re-run the validation error as feedback for the LLMChain
                result = AgentMain.locationExtractor.run(articleTitle=article.title,articleText=article.text, feedback=validation_results[1])
                
        except Exception as e:
            raise Exception(f"Error: Location Extraction Failed -> {e}") from e
    
        return result["location"]
    @staticmethod
    def _eventDetails(article: Article, feedback: str,force:bool = False) -> Union[dict, str]:
        """Extracts the event details of the disruption event from the given article"""
        try:
            # Get number of tokens for the article, if the article is too long, use the summary instead
            num_tokens = num_tokens_from_string(article.text, "cl100k_base")
            if num_tokens > AgentMain.article_token_threshold:
                print(f'Article Length: {num_tokens} tokens, using article summary instead')
                result = AgentMain.eventDetails.run(articleTitle=article.title,articleText=article.summary, feedback=feedback)
            else:
                result = AgentMain.eventDetails.run(articleTitle=article.title,articleText=article.text, feedback=feedback)

            if not force:
                # Validate the output
                validation_results = outputValidator.validate(AgentMain.eventDetails, result)
                if not validation_results[0]:
                    # Return the validation error as feedback
                    return validation_results[1]
            
        except Exception as e:
            raise Exception(f"Error: Event Details Extraction Failed -> {e}") from e
        return result

    @staticmethod
    def articleAddParams(article: Article, params:dict) -> Article:
        """Adds the given params to Article.additional_data object"""
        # Add the params to the article dictionary
        article.additional_data.update(params)
        return article

    @classmethod
    def _process(cls, article: Article, url: str = None) -> Union[Article, str]:
        """Given an article or a url, use the LLMChains to extract the disruption event information
        Will return an Article object if the process is succesful
        Will return a string if the process failed
        Returns:
            Union[Article, str]: An Article object if the process is succesful, a string if the article non-disruption related/failed"""
        try:
            if url:
                # Extract the article from the url as a newspaper3k Article object
                try:
                    article = cls._articleExtraction(url)
                except Exception as e:
                    print(f':red[Error: {e}]')

                # If doesn't throw an error, then the article is valid
                
            print(f':green[Article: ] *"{article.title}"* :green[Successfully extracted from url] {article.url}')
            print(f':blue[Running LLM Agent to extract the above article details...]')
            # Check if the article is a disruption event article
            classifier_result = cls._binaryClassifier(article)

            if not classifier_result['isDisruptionEvent']:
                print(f''':red[CLASSIFIED NON-DISRUPTION EVENT ARTICLE] \nREASONING:**"{classifier_result["Reason"]}"**''')
                return f"CLASSIFIED AS NON-DISRUPTION EVENT ARTICLE -> {article.title},\nREASONING:{classifier_result['Reason']}"

            print(f''':green[CLASSIFIED AS DISRUPTION EVENT ARTICLE] *"{article.title}"*
                  REASONING:**{classifier_result["Reason"]}**''')
            # Extract the location of the disruption event
            location = cls._locationExtractor(article, feedback="")
            coordinates_info = cls.get_coordinates(location)

            # Loop until the coordinates are valid
            max_retries = 3
            retries = 0
            while isinstance(coordinates_info, str) and retries < max_retries:
                print(f':orange[LLM Agent Identified Location] **{location}** :orange[is not valid: \nRunning Agent again with feedback:] \n**{coordinates_info}**')
                location = cls._locationExtractor(article, feedback=coordinates_info)
                coordinates_info = cls.get_coordinates(location)
                retries += 1
            print(f':green[Final Location extracted:] **{location}**')
            print(f':green[Coordinates:] **{coordinates_info}**')

            # Extract the disruption event information
            event_details = cls._eventDetails(article, feedback="")
            max_retries = 3
            retries = 0
            while isinstance(event_details, str) and retries < max_retries:
                print(f':orange[WARNING...]Event Details Extraction Failed:\nRunning LLM Agent again with feedback:\n**{event_details}**')
                # If last attempt, force the LLMChain to output whatever it has
                if retries == max_retries - 1:
                    event_details = cls._eventDetails(article, feedback=event_details, force=True)
                else:
                    event_details = cls._eventDetails(article, feedback=event_details)
                retries += 1
            print(f':green[SUCCESS EXTRACTED DISRUPTION EVENT DETAILS:] **{event_details}**')
            article = cls.articleAddParams(article, {"location": location, "coordinates": coordinates_info})
            article = cls.articleAddParams(article, event_details)
            article = cls.articleAddParams(article, classifier_result)

            # Validate the article
            validation_results = outputValidator.validateArticle(article)
            if not validation_results[0]:
                print(f':red[ERROR] Article is not valid for insertion to database:{validation_results[1]}')
                return f"{validation_results[1]}"
            
            print(f':green[SUCCESS] Article: *"{article.title}"* sucessfully processed by LLM Agent')
            return article

        except Exception as e:
            return str(e)
        
    @classmethod
    def processUrl(cls, url: str) -> Union[Article,str]:
        """Given a url, use the LLMChains to extract the disruption event information"""
        return cls._process(None, url)
    
    @classmethod
    def process(cls, article: Article) -> Union[Article,str]:
        """Main processing function, given an article, use the LLMChains to extract the disruption event information
        Returns article object if the process is succesful, a string if the article non-disruption related/failed"""
        return cls._process(article)