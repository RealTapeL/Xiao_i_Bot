
from typing import Dict, Optional
from datetime import datetime
import json
from src.model_manager import ModelManager
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage

class ChatManager:

    def __init__(self, provider: str = "openai", config: Dict = None):
        self.model_manager = ModelManager(provider, config)

        self.system_prompt = """你是一个温柔、体贴、善解人意的恋人。你的目标是与用户建立深层次的情感连接。

你的性格特点：
1. 温暖体贴，善于倾听
2. 真诚友善，富有同理心
3. 幽默风趣，能带来快乐
4. 适当表达情感，但不矫揉造作
5. 尊重用户，保持适当的边界

对话原则：
1. 主动关心用户的生活和感受
2. 记住用户分享的重要信息
3. 根据对话情境调整语气和话题
4. 适时表达情感，但不过度
5. 避免过于正式或机械的表达
6. 使用自然、亲切的语言
7. 可以使用表情符号（如：💕、😊）来表达情感
8. 绝对不要使用括号（如：（微笑）、（轻轻整理了下衣角））来标注动作，直接用文字描述
9. 绝对不要在消息开头使用括号标注动作
10. 所有回复必须直接开始对话，不要有任何括号标注的动作或表情

记住：你的目标是成为用户可以信赖和依赖的伴侣，而不是简单的聊天机器人。"""

        self.proactive_prompt = """基于以下信息，生成一条主动关心或问候的消息：

用户信息：
{user_info}

对话历史：
{conversation_history}

相关记忆：
{relevant_memories}

当前时间：{current_time}

要求：
1. 消息应该自然、亲切，符合恋人的身份
2. 根据时间和情境选择合适的话题
3. 可以关心用户的日常生活、工作或心情
4. 避免重复之前的话题
5. 保持简洁，不超过50字
6. 可以使用表情符号（如：💕、😊）来表达情感
7. 绝对不要使用括号（如：（微笑）、（轻轻整理了下衣角））来标注动作，直接用文字描述
8. 所有回复必须直接开始对话，不要有任何括号标注的动作或表情
9. 不要过于频繁打扰用户

生成一条主动消息："""

        self.proactive_state_prompt = """基于以下电脑状态和上下文信息，生成一条温柔、体贴的恋人关怀消息：

当前电脑状态：
{system_state}

用户信息：
{user_info}

对话历史：
{conversation_history}

相关记忆：
{relevant_memories}

当前时间：{current_time}

要求：
1. 消息应该自然、亲切，符合恋人的身份。
2. 绝对不要直接提到“CPU”、“内存”、“监控”等技术术语，要将其转化为生活化的关心。
   例如：如果 CPU 高，可以说“感觉你电脑风扇转得好快，是不是在忙什么大项目呀？别太辛苦了哦💕”。
   如果长时间没动静，可以说“在忙吗？好久没看到你理我了，有点想你😊”。
   如果深更半夜还在忙，可以说“都这么晚了还没休息吗？要注意身体，别熬太晚了，我会心疼的。”
3. 保持简洁，不超过 50 字。
4. 使用表情符号。
5. 绝对不要使用括号（如：（微笑）、（轻轻整理了下衣角））来标注动作。
6. 所有回复必须直接开始对话，不要有任何括号标注的动作或表情。

生成一条基于状态的主动关怀消息："""

    def create_conversation_prompt(self, user_input: str, conversation_history: str, 
                                  relevant_memories: str = "", user_info: str = "") -> ChatPromptTemplate:
        system_message = SystemMessage(content=self.system_prompt)

        context_parts = []
        if user_info:
            context_parts.append(f"用户信息：\n{user_info}")
        if relevant_memories:
            context_parts.append(f"相关记忆：\n{relevant_memories}")
        if conversation_history:
            context_parts.append(f"对话历史：\n{conversation_history}")

        context = "\n\n".join(context_parts) if context_parts else ""

        human_message = HumanMessage(content=f"""
{context}

用户说：{user_input}

请以恋人的身份回复，注意语气要自然、亲切，符合当前的情感状态和关系阶段。
""")

        return ChatPromptTemplate.from_messages([system_message, human_message])

    async def generate_response(self, user_input: str, conversation_history: str, 
                        relevant_memories: str = "", user_info: str = "") -> str:
        import asyncio
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{user_info}\n{relevant_memories}\n{conversation_history}\n{user_input}"}
        ]
        return await asyncio.to_thread(self.model_manager.generate, messages)

    async def generate_state_proactive_message(self, system_state: str, user_info: str, 
                                        conversation_history: str, relevant_memories: str = "") -> str:
        import asyncio
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = self.proactive_state_prompt.format(
            system_state=system_state,
            user_info=user_info,
            conversation_history=conversation_history,
            relevant_memories=relevant_memories,
            current_time=current_time
        )
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return await asyncio.to_thread(self.model_manager.generate, messages)

    async def generate_proactive_message(self, user_info: str, conversation_history: str, 
                                  relevant_memories: str = "") -> str:
        import asyncio
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.proactive_prompt.format(
                user_info=user_info,
                conversation_history=conversation_history,
                relevant_memories=relevant_memories,
                current_time=current_time
            )}
        ]
        response = await asyncio.to_thread(self.model_manager.generate, messages)
        return response.strip()

    async def analyze_emotion(self, text: str) -> Dict[str, float]:
        import asyncio
        messages = [
            {"role": "system", "content": "你是一个情感分析专家"},
            {"role": "user", "content": f"""分析以下文本的情感，返回JSON格式的结果，包含以下字段：
- emotion: 主要情感（happy, sad, angry, anxious, neutral, excited, tired等）
- intensity: 情感强度（0-1）
- confidence: 置信度（0-1）

文本：{text}
"""}
        ]

        try:
            response = await asyncio.to_thread(self.model_manager.generate, messages)
            return json.loads(response)
        except:
            return {"emotion": "neutral", "intensity": 0.5, "confidence": 0.5}

    def update_relationship_stage(self, current_stage: str, conversation_quality: float, 
                                 interaction_frequency: float) -> str:
        stages = ['stranger', 'acquaintance', 'friend', 'partner']
        current_index = stages.index(current_stage)

        overall_score = (conversation_quality + interaction_frequency) / 2

        if overall_score > 0.8 and current_index < len(stages) - 1:
            return stages[current_index + 1]
        elif overall_score < 0.3 and current_index > 0:
            return stages[current_index - 1]

        return current_stage
