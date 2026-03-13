
from typing import Dict, Optional
from langchain_community.chat_models import ChatOpenAI
from zhipuai import ZhipuAI
from dashscope import Generation
from openai import OpenAI

class ModelManager:

    def __init__(self, provider: str = "openai", config: Dict = None):
        self.provider = provider
        self.config = config or {}
        self._init_model()

    def _init_model(self):
        if self.provider == "openai":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                openai_api_key=self.config.get("api_key"),
                model=self.config.get("model", "gpt-4"),
                temperature=self.config.get("temperature", 0.8),
                openai_api_base=self.config.get("base_url")
            )
        elif self.provider == "zhipuai":
            self.client = ZhipuAI(api_key=self.config.get("api_key"))
            self.llm = self._create_zhipu_llm()
        elif self.provider == "dashscope":
            self.api_key = self.config.get("api_key")
            self.model = self.config.get("model", "qwen-turbo")
        elif self.provider == "deepseek":
            self.client = OpenAI(
                api_key=self.config.get("api_key"),
                base_url="https://api.deepseek.com"
            )
        elif self.provider == "minimax":
            from minimax import Chat
            self.client = Chat(
                api_key=self.config.get("api_key"),
                group_id=self.config.get("group_id")
            )
        elif self.provider == "moonshot":
            self.client = OpenAI(
                api_key=self.config.get("api_key"),
                base_url="https://api.moonshot.cn/v1"
            )

    def _create_zhipu_llm(self):
        from langchain.chat_models.base import BaseChatModel
        from langchain.schema import BaseMessage, AIMessage, HumanMessage, SystemMessage, ChatResult, ChatGeneration
        from typing import List, Optional, Any, Dict
        
        class ZhipuChatLLM(BaseChatModel):
            client: Any = None
            model_name: str = "chatglm3-6b"
            temperature: float = 0.7
            
            def __init__(self, client, model_name, temperature):
                super().__init__()
                self.client = client
                self.model_name = model_name
                self.temperature = temperature
                
            @property
            def _llm_type(self) -> str:
                return "zhipuai"
            
            def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> ChatResult:
                zhipu_messages = []
                for msg in messages:
                    role = "user"
                    if isinstance(msg, SystemMessage):
                        role = "system"
                    elif isinstance(msg, AIMessage):
                        role = "assistant"
                    zhipu_messages.append({"role": role, "content": msg.content})
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=zhipu_messages,
                    temperature=self.temperature
                )
                
                content = response.choices[0].message.content
                generation = ChatGeneration(message=AIMessage(content=content))
                return ChatResult(generations=[generation])

        return ZhipuChatLLM(
            client=self.client, 
            model_name=self.config.get("model", "chatglm3-6b"),
            temperature=self.config.get("temperature", 0.7)
        )

    def generate(self, messages: list, **kwargs) -> str:
        if self.provider == "openai":
            from langchain.schema import HumanMessage, AIMessage, SystemMessage
            lc_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    lc_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_messages.append(AIMessage(content=msg["content"]))
            response = self.llm(lc_messages)
            return response.content

        elif self.provider == "zhipuai":
            response = self.client.chat.completions.create(
                model=self.config.get("model", "chatglm3-6b"),
                messages=messages,
                temperature=kwargs.get("temperature", 0.7)
            )
            return response.choices[0].message.content

        elif self.provider == "dashscope":
            response = Generation.call(
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                result_format='message'
            )
            return response.output.choices[0].message['content']

        elif self.provider == "deepseek":
            response = self.client.chat.completions.create(
                model=self.config.get("model", "deepseek-chat"),
                messages=messages,
                temperature=kwargs.get("temperature", 0.7)
            )
            return response.choices[0].message.content

        elif self.provider == "minimax":
            response = self.client.completions(
                model=self.config.get("model", "abab5.5-chat"),
                messages=messages,
                temperature=kwargs.get("temperature", 0.7)
            )
            return response.choices[0].message.content

        elif self.provider == "moonshot":
            response = self.client.chat.completions.create(
                model=self.config.get("model", "moonshot-v1-8k"),
                messages=messages,
                temperature=kwargs.get("temperature", 0.7)
            )
            return response.choices[0].message.content

        raise ValueError(f"Unsupported provider: {self.provider}")
