import asyncio
from collections import defaultdict
import copy
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from flaml.autogen import oai
from .agent import Agent
from langchain.chains.base import Chain

from flaml.autogen.code_utils import (
    DEFAULT_MODEL,
    UNKNOWN,
    execute_code,
    extract_code,
    infer_lang,
)
try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x

class TaskChain:
    """Class to represent a Task Chain"""

    def __init__(self,task:str,chain:Chain):
        """
        Args:
            task (str): name of the task.
            chain (Chain): Initialized Chain with JSON Output Parser,Prompt and LLM
        """
        self.task = task
        self.chain = chain

class TaskChainAgent(Agent):
    """Class for Generic Task Chain Agent

    Overall Ochestrator with Memory that sends and receives messages from
    the Task Chain Agents
    """
    
