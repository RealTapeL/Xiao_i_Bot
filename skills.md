# Skills Guide

This guide explains how to use the skills system in Xiao_i_Bot, with detailed documentation for the Xiaohongshu (Little Red Book) integration.

## Overview

The skills system is an extensible plugin architecture that allows the bot to integrate with external services. Each skill can provide various functions such as searching content, publishing posts, getting user information, etc.

## Available Skills

### Xiaohongshu (Little Red Book)

The Xiaohongshu skill integrates with the [xhs-mcp](https://github.com/algovate/xhs-mcp) server to provide automation capabilities for Xiaohongshu (xiaohongshu.com).

## Prerequisites

Before using the Xiaohongshu skill, you need to:

1. **Install Node.js and npm**
   ```bash
   # Check if installed
   node --version
   npm --version
   ```

2. **Install xhs-mcp**
   ```bash
   npx -y install xhs-mcp
   ```

3. **Install Puppeteer browser** (first time only)
   ```bash
   npx xhs-mcp browser
   # or
   npx puppeteer browsers install chrome
   ```

4. **Login to Xiaohongshu**
   ```bash
   npx xhs-mcp login
   ```
   
   This will open a browser window for you to scan the QR code and login. The session will be saved for future use.

## Commands

### /xhs - Xiaohongshu Operations

The `/xhs` command provides various Xiaohongshu operations:

```
/xhs search <keyword>  - Search for posts
/xhs feeds            - Get discovery feeds
/xhs user             - View your notes
/xhs note <id>        - Get note details
```

### /skills - List Available Skills

Shows all available skills and their descriptions:

```
/skills
```

## Usage Examples

### Search for Posts

Search for content on Xiaohongshu:

```
/xhs search Python教程
```

Response:
```
🔍 搜索结果：「Python教程」

[Results will be displayed here]
```

### Get Discovery Feeds

Get recommended content from the discovery page:

```
/xhs feeds
```

### View Your Notes

View your own published notes:

```
/xhs user
```

### Get Note Details

Get detailed information about a specific note:

```
/xhs note 123456789
```

## Adding More Skills

The skills system is designed to be extensible. You can add new skills by:

1. Creating a new class that extends `BaseSkill` in `src/skill_manager.py`
2. Implementing the `execute` method
3. Registering the skill in `SkillManager`

Example:

```python
from src.skill_manager import BaseSkill, SkillResult

class MyNewSkill(BaseSkill):
    name = "my_new_skill"
    description = "Description of my new skill"
    
    async def execute(self, params: dict) -> SkillResult:
        # Implement your skill logic here
        result = do_something()
        return SkillResult(success=True, result=result)
```

## Configuration

### Environment Variables

No additional environment variables are required for the skills system. Each skill may have its own configuration options.

### Proxy Settings

If you need to use a proxy to access Xiaohongshu, configure it in your `.env` file:

```
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

## Troubleshooting

### Login Issues

If you encounter login issues:

1. Delete the saved session: `npx xhs-mcp logout`
2. Login again: `npx xhs-mcp login`
3. Re-scan the QR code

### Timeout Errors

If operations timeout, try again or check your network connection.

### Browser Not Found

If Puppeteer cannot find the browser:

```bash
npx xhs-mcp browser
```

## Security Notes

- Keep your Xiaohongshu session secure
- Do not share your login credentials
- The bot stores session data locally

## More Information

For more details about xhs-mcp, visit:
- https://github.com/algovate/xhs-mcp
- https://algovate.github.io/xhs-mcp/
