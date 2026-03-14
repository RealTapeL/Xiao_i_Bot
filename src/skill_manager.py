"""
Skill Manager - Manages various skills/plugins for the bot
"""
import os
import json
import subprocess
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SkillResult:
    success: bool
    result: str
    error: Optional[str] = None

class BaseSkill:
    """Base class for all skills"""
    
    name: str = "base"
    description: str = "Base skill"
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        raise NotImplementedError
    
    def get_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description
        }

class XiaohongshuSkill(BaseSkill):
    """Xiaohongshu (Little Red Book) skill using MCP"""
    
    name = "xiaohongshu"
    description = "小红书技能 - 搜索帖子、发布内容、查看笔记等"
    
    def __init__(self):
        self.mcp_server_process: Optional[subprocess.Popen] = None
        self.initialized = False
    
    async def _ensure_server_running(self) -> bool:
        """Ensure MCP server is running"""
        if self.initialized:
            return True
        
        try:
            # Start MCP server in background
            # Using npx to run xhs-mcp
            process = subprocess.Popen(
                ["npx", "-y", "xhs-mcp", "mcp", "--mode", "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.mcp_server_process = process
            self.initialized = True
            logger.info("Xiaohongshu MCP server started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Xiaohongshu MCP server: {e}")
            return False
    
    async def search_posts(self, keyword: str, limit: int = 10) -> SkillResult:
        """Search Xiaohongshu posts"""
        try:
            # Use subprocess to call xhs-mcp CLI
            result = subprocess.run(
                ["npx", "-y", "xhs-mcp", "search", keyword, "--limit", str(limit)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return SkillResult(success=True, result=result.stdout)
            else:
                return SkillResult(success=False, result="", error=result.stderr)
        except subprocess.TimeoutExpired:
            return SkillResult(success=False, result="", error="Search timeout")
        except Exception as e:
            return SkillResult(success=False, result="", error=str(e))
    
    async def get_note_detail(self, note_id: str) -> SkillResult:
        """Get note detail by ID"""
        try:
            result = subprocess.run(
                ["npx", "-y", "xhs-mcp", "note", note_id],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return SkillResult(success=True, result=result.stdout)
            else:
                return SkillResult(success=False, result="", error=result.stderr)
        except Exception as e:
            return SkillResult(success=False, result="", error=str(e))
    
    async def publish_post(self, title: str, content: str, images: List[str] = None) -> SkillResult:
        """Publish a new post"""
        try:
            cmd = ["npx", "-y", "xhs-mcp", "publish", "--title", title, "--content", content]
            
            if images:
                for img in images:
                    cmd.extend(["--image", img])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return SkillResult(success=True, result=result.stdout)
            else:
                return SkillResult(success=False, result="", error=result.stderr)
        except Exception as e:
            return SkillResult(success=False, result="", error=str(e))
    
    async def get_feeds(self, limit: int = 10) -> SkillResult:
        """Get discovery feeds"""
        try:
            result = subprocess.run(
                ["npx", "-y", "xhs-mcp", "feeds", "--limit", str(limit)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return SkillResult(success=True, result=result.stdout)
            else:
                return SkillResult(success=False, result="", error=result.stderr)
        except Exception as e:
            return SkillResult(success=False, result="", error=str(e))
    
    async def get_user_notes(self, user_id: str = None, limit: int = 10) -> SkillResult:
        """Get user's notes"""
        try:
            cmd = ["npx", "-y", "xhs-mcp", "usernote"]
            
            if user_id:
                cmd.extend(["--user-id", user_id])
            
            cmd.extend(["--limit", str(limit)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return SkillResult(success=True, result=result.stdout)
            else:
                return SkillResult(success=False, result="", error=result.stderr)
        except Exception as e:
            return SkillResult(success=False, result="", error=str(e))
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute skill based on action"""
        action = params.get("action", "")
        
        if action == "search":
            keyword = params.get("keyword", "")
            limit = params.get("limit", 10)
            return await self.search_posts(keyword, limit)
        
        elif action == "note_detail":
            note_id = params.get("note_id", "")
            return await self.get_note_detail(note_id)
        
        elif action == "publish":
            title = params.get("title", "")
            content = params.get("content", "")
            images = params.get("images", [])
            return await self.publish_post(title, content, images)
        
        elif action == "feeds":
            limit = params.get("limit", 10)
            return await self.get_feeds(limit)
        
        elif action == "user_notes":
            user_id = params.get("user_id")
            limit = params.get("limit", 10)
            return await self.get_user_notes(user_id, limit)
        
        else:
            return SkillResult(
                success=False, 
                result="", 
                error=f"Unknown action: {action}"
            )
    
    def cleanup(self):
        """Cleanup resources"""
        if self.mcp_server_process:
            self.mcp_server_process.terminate()
            self.initialized = False


class SkillManager:
    """Manages all skills"""
    
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self._register_default_skills()
    
    def _register_default_skills(self):
        """Register default skills"""
        self.register_skill(XiaohongshuSkill())
    
    def register_skill(self, skill: BaseSkill):
        """Register a new skill"""
        self.skills[skill.name] = skill
        logger.info(f"Registered skill: {skill.name}")
    
    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Get skill by name"""
        return self.skills.get(name)
    
    def list_skills(self) -> List[Dict]:
        """List all available skills"""
        return [skill.get_schema() for skill in self.skills.values()]
    
    async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> SkillResult:
        """Execute a skill"""
        skill = self.get_skill(skill_name)
        if not skill:
            return SkillResult(
                success=False, 
                result="", 
                error=f"Skill not found: {skill_name}"
            )
        
        try:
            return await skill.execute(params)
        except Exception as e:
            logger.error(f"Error executing skill {skill_name}: {e}")
            return SkillResult(success=False, result="", error=str(e))
    
    def cleanup(self):
        """Cleanup all skills"""
        for skill in self.skills.values():
            if hasattr(skill, 'cleanup'):
                skill.cleanup()
