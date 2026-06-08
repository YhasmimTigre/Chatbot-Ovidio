from typing import TypedDict, Annotated, List, Union
#from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
#from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator
import os
import time
import re
import math
from IPython.display import Image, display
import chainlit as cl
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from langchain_ollama import ChatOllama

from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver