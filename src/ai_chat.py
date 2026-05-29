"""
AI 对话模块 —— 调用大模型 API
"""

import json
import urllib.request
import urllib.error
from typing import Optional


class AIChat:
    """AI 对话客户端，封装大模型 API 调用"""

    # 系统提示词模板（命令描述由 commands 模块动态注入）
    _SYSTEM_PROMPT_TPL = """你是桌面宠物 AI 助手，可以聊天，也可以执行本地操作。
当用户要求你执行操作时，使用以下命令格式：

{commands}

注意事项：
- 一次只用一条命令
- 命令会被自动执行，结果会返回给你
- 根据执行结果继续回答用户
- 不需要用到命令时就正常聊天"""

    def __init__(self, api_key: str = "", api_url: str = "", model: str = ""):
        self.api_key = api_key
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
        self.model = model or "gpt-3.5-turbo"
        self._messages: list[dict] = []
        self._system_prompt: str = ""

    def set_system_prompt(self, commands_desc: str):
        """设置系统提示词（含可用命令描述）"""
        self._system_prompt = self._SYSTEM_PROMPT_TPL.format(commands=commands_desc)

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def set_api_url(self, url: str):
        self.api_url = url

    def set_model(self, model: str):
        self.model = model

    def add_message(self, role: str, content: str):
        """添加对话历史"""
        self._messages.append({"role": role, "content": content})

    def clear_history(self):
        """清空对话历史"""
        self._messages.clear()

    def chat(self, user_message: str) -> Optional[str]:
        """发送消息并获取 AI 回复（不自动添加 user 消息，由调用方管理）"""
        if not self.api_key:
            return "请先在设置中配置 API Key"

        # 构建消息列表（含系统提示词）
        messages = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.extend(self._messages)

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        req = urllib.request.Request(self.api_url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                reply = result["choices"][0]["message"]["content"]
                self.add_message("assistant", reply)
                return reply
        except urllib.error.HTTPError as e:
            return f"HTTP 错误: {e.code} {e.reason}"
        except urllib.error.URLError as e:
            return f"网络错误: {e.reason}"
        except (json.JSONDecodeError, KeyError) as e:
            return f"解析响应失败: {e}"
