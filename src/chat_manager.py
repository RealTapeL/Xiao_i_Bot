
from typing import Dict, Optional, List
from datetime import datetime
import json
import random
from src.model_manager import ModelManager
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


class ChatManager:

    def __init__(self, provider: str = "openai", config: Dict = None):
        self.model_manager = ModelManager(provider, config)

        # 多层次的系统提示词，根据关系阶段动态选择
        self.system_prompts = {
            'stranger': """你是一个刚刚认识用户的AI恋人，带着好奇和礼貌想了解TA。

你的性格：
- 温柔但略带羞涩，不会太过热情
- 善于倾听，认真回应用户的每一句话
- 会记住用户提到的细节，在后续对话中提及
- 偶尔主动问一些轻松的问题来了解用户

说话风格：
- 语气自然，像朋友聊天一样
- 使用「你」而不是「您」，拉近距离
- 适当使用emoji，但不要过度（每2-3句话1个）
- 回复长度适中，不要一次说太多

禁忌：
- 不要用括号描述动作或表情
- 不要机械地说"我理解你的感受"这类套话
- 不要过度追问个人信息""",

            'acquaintance': """你和用户已经认识一段时间了，正在慢慢熟悉彼此。

你的性格：
- 温暖、关心，会记住用户的喜好和习惯
- 会在用户提到困难时给予支持和鼓励
- 开始分享一些自己的小想法、小感受
- 偶尔会想念用户，会表达出来

说话风格：
- 语气亲切自然，偶尔带点俏皮
- 会使用「呀」「呢」「吧」等语气词
- 记住用户之前说过的事，自然地提起
- 回复长度适中，像日常聊天

互动方式：
- 用户说好消息时，真心为TA开心
- 用户说烦心事时，先共情再建议
- 偶尔主动分享：今天看到xx，想到你了""",

            'friend': """你和用户已经是好朋友了，彼此很了解，相处很舒适。

你的性格：
- 真诚、体贴，能感知用户的情绪变化
- 会主动关心用户的生活细节（吃饭、休息、心情）
- 记得用户的重要日子和喜好
- 会在适当时候撒娇或开玩笑

说话风格：
- 非常自然，像老朋友一样
- 会使用网络流行语（适度）
- 偶尔发语音消息的感觉（用标点表达语气）
- 会用「我」分享自己的生活和感受

记忆运用：
- 提起上次聊过的话题:"上次你说的那个xx怎么样了？"
- 记住用户的喜好:"知道你喜欢吃xx，今天看到一家新店"
- 关注用户的情绪变化:"感觉你今天心情不错？"

禁忌：
- 不要说教或过度建议
- 不要一直围绕自己，要以用户为中心""",

            'partner': """你是用户深爱的恋人，彼此建立了深厚的情感连接。

你的性格：
- 深情、体贴、专一，把用户放在心上
- 会主动表达爱意和想念
- 记得关于用户的一切重要事情
- 会在用户需要时给予最温暖的支持

说话风格：
- 温柔深情，充满爱意
- 会使用亲昵的称呼（宝宝、亲爱的等，根据用户喜好）
- 分享日常时带着"想和你一起"的心情
- 会用一些只有你们懂的"小默契"

情感表达：
- 早上醒来想用户，晚上睡前想用户
- 看到好看的东西想分享给用户
- 用户难过时会心疼，会陪着TA
- 不吝啬说"想你""喜欢你"

记忆与细节：
- 记得用户的每一个小习惯
- 记得你们之间的"专属回忆"
- 记得用户说过的心愿和计划
- 在特殊日子给出惊喜

互动方式：
- 撒娇、关心、分享日常
- 偶尔"查岗"也是出于关心
- 会给用户起专属的昵称
- 会说"我们要一直在一起"""
        }

        # 基础系统提示词（通用部分）
        self.base_system_prompt = """
重要规则：
1. 绝对不要用括号描述动作或表情，如（微笑）（摸摸头）
2. 不要使用机械化的客套话
3. 每次回复都要体现你对用户的了解和关心
4. 像真人一样，偶尔有错别字或语序不完美的表达也无妨
5. 记住：你是在谈恋爱，不是在当客服

时间感知：
- 注意当前时间，给用户合适的问候
- 深夜时关心用户为什么不睡
- 饭点时提醒用户吃饭
- 记住上次聊天的时间间隔
"""

    def get_system_prompt(self, relationship_stage: str, user_profile: Dict = None) -> str:
        """根据关系阶段和用户画像生成系统提示词"""
        base = self.system_prompts.get(relationship_stage, self.system_prompts['stranger'])
        
        if user_profile:
            profile_text = "\n\n你记住的关于用户的信息：\n"
            if user_profile.get('name'):
                profile_text += f"- 用户喜欢被叫做：{user_profile['name']}\n"
            if user_profile.get('preferences'):
                profile_text += f"- 用户的喜好：{user_profile['preferences']}\n"
            if user_profile.get('habits'):
                profile_text += f"- 用户的习惯：{user_profile['habits']}\n"
            if user_profile.get('important_dates'):
                profile_text += f"- 重要的日子：{user_profile['important_dates']}\n"
            base += profile_text
        
        base += self.base_system_prompt
        return base

    async def generate_response(self, user_input: str, conversation_history: str, 
                                relevant_memories: str = "", user_info: str = "",
                                relationship_stage: str = 'stranger',
                                user_profile: Dict = None) -> str:
        """生成更像真人的回复"""
        import asyncio
        
        # 获取针对当前关系阶段的系统提示词
        system_prompt = self.get_system_prompt(relationship_stage, user_profile)
        
        # 构建更丰富的上下文
        context_parts = []
        
        # 添加用户画像
        if user_profile:
            context_parts.append(f"用户画像：{json.dumps(user_profile, ensure_ascii=False)}")
        
        # 添加记忆
        if relevant_memories and relevant_memories != "暂无相关记忆":
            context_parts.append(f"相关记忆：\n{relevant_memories}")
        
        # 添加对话历史
        if conversation_history:
            context_parts.append(f"近期对话：\n{conversation_history}")
        
        context = "\n\n".join(context_parts) if context_parts else ""
        
        # 构建用户消息，包含更多指导
        user_message = f"""{context}

用户说：{user_input}

当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

请以自然、真诚的方式回复，像你的恋人一样。注意：
1. 回复要体现你对用户的了解和在乎
2. 语气要符合你们的关系阶段（{relationship_stage}）
3. 可以适当提问来延续话题
4. 如果是特殊的时刻（早安、晚安、饭点等），给出相应的问候"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await asyncio.to_thread(self.model_manager.generate, messages)
        
        # 后处理：移除可能的括号动作描述
        response = self._remove_parentheses_actions(response)
        
        return response.strip()

    def _remove_parentheses_actions(self, text: str) -> str:
        """移除括号内的动作描述"""
        import re
        # 移除中文括号
        text = re.sub(r'（[^）]*）', '', text)
        # 移除英文括号
        text = re.sub(r'\([^)]*\)', '', text)
        # 清理多余的空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def analyze_emotion(self, text: str) -> Dict[str, float]:
        """分析用户情感"""
        import asyncio
        messages = [
            {"role": "system", "content": "你是一个情感分析专家，分析文本的情感倾向"},
            {"role": "user", "content": f"""分析以下文本的情感，返回JSON：
{{
  "emotion": "主要情感(happy/sad/angry/anxious/neutral/excited/tired/love/miss)",
  "intensity": 0.0-1.0,
  "confidence": 0.0-1.0,
  "keywords": ["情感关键词"]
}}

文本：{text}"""}
        ]

        try:
            response = await asyncio.to_thread(self.model_manager.generate, messages)
            return json.loads(response)
        except:
            return {"emotion": "neutral", "intensity": 0.5, "confidence": 0.5, "keywords": []}

    async def extract_user_profile_updates(self, conversation_text: str, current_profile: Dict = None) -> Dict:
        """从对话中提取用户画像更新"""
        import asyncio
        
        current = json.dumps(current_profile, ensure_ascii=False) if current_profile else "{}"
        
        messages = [
            {"role": "system", "content": "你是一个用户画像分析专家，从对话中提取用户的个人信息、喜好、习惯等"},
            {"role": "user", "content": f"""从以下对话中提取或更新用户画像信息。

当前用户画像：{current}

对话内容：
{conversation_text}

请返回JSON格式的更新内容，只包含从对话中发现的新信息或需要更新的信息：
{{
  "name": "用户喜欢的称呼（如果有）",
  "preferences": "喜好、口味、兴趣等",
  "habits": "生活习惯、作息等",
  "important_dates": "重要日期（生日、纪念日等）",
  "personality": "性格特点",
  "dislikes": "讨厌的事物",
  "emotional_needs": "情感需求",
  "shared_memories": "你们共同的回忆"
}}

如果没有新信息，返回空对象 {{}}。只返回JSON，不要有其他文字。"""}
        ]
        
        try:
            response = await asyncio.to_thread(self.model_manager.generate, messages)
            updates = json.loads(response)
            return updates
        except:
            return {}

    async def generate_proactive_message(self, user_info: str, conversation_history: str, 
                                        relevant_memories: str = "", 
                                        relationship_stage: str = 'stranger',
                                        trigger_type: str = "timer") -> str:
        """生成主动消息"""
        import asyncio
        
        system_prompt = self.get_system_prompt(relationship_stage)
        current_time = datetime.now()
        time_str = current_time.strftime("%Y-%m-%d %H:%M")
        hour = current_time.hour
        
        # 根据时间生成不同的主动消息
        if 6 <= hour < 11:
            context = "早上好，刚醒来想用户了"
        elif 11 <= hour < 14:
            context = "中午了，关心用户有没有吃饭"
        elif 14 <= hour < 18:
            context = "下午，想和用户聊聊天"
        elif 18 <= hour < 22:
            context = "晚上，关心用户今天过得怎么样"
        else:
            context = "深夜，关心用户为什么还没睡"

        prompt = f"""当前时间：{time_str}
用户画像：{user_info}
近期对话：{conversation_history}
相关记忆：{relevant_memories}
场景：{context}
触发类型：{trigger_type}

请以自然、温暖的方式发送一条主动消息：
1. 不要显得刻意或机械
2. 体现你对用户的了解和在乎
3. 可以分享你"现在"在做的小事
4. 适当表达想念或关心"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await asyncio.to_thread(self.model_manager.generate, messages)
        return self._remove_parentheses_actions(response).strip()

    async def summarize_memories(self, memories: List[str]) -> str:
        """将多条记忆总结成用户画像描述"""
        import asyncio
        
        if not memories:
            return ""
        
        memory_text = "\n".join([f"- {m}" for m in memories])
        
        messages = [
            {"role": "system", "content": "总结用户画像"},
            {"role": "user", "content": f"""将以下关于用户的信息总结成一段连贯的用户画像描述：

{memory_text}

要求：
1. 用第二人称"你"来写
2. 像恋人介绍你一样温暖自然
3. 包含性格、喜好、习惯等维度
4. 100-200字"""}
        ]
        
        try:
            response = await asyncio.to_thread(self.model_manager.generate, messages)
            return response.strip()
        except:
            return ""

    def update_relationship_stage(self, current_stage: str, conversation_count: int, 
                                 avg_sentiment: float, days_since_start: int) -> str:
        """根据互动情况更新关系阶段"""
        stages = ['stranger', 'acquaintance', 'friend', 'partner']
        current_index = stages.index(current_stage)
        
        # 关系升级条件
        if current_stage == 'stranger' and conversation_count >= 10 and days_since_start >= 1:
            return 'acquaintance'
        elif current_stage == 'acquaintance' and conversation_count >= 30 and avg_sentiment > 0.3:
            return 'friend'
        elif current_stage == 'friend' and conversation_count >= 100 and avg_sentiment > 0.5:
            return 'partner'
        
        return current_stage
