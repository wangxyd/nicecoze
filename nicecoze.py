# encoding:utf-8

import json
import os
from urllib.parse import urlparse

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *


@plugins.register(
    name="Nicecoze",
    desire_priority=100,
    hidden=True,
    desc="一款优化coze-discord-proxy返回结果的插件。",
    version="1.0",
    author="空心菜",
)
class Nicecoze(Plugin):
    def __init__(self):
        super().__init__()
        try:
            self.handlers[Event.ON_DECORATE_REPLY] = self.on_decorate_reply
            logger.info("[Nicecoze] inited.")
        except Exception as e:
            logger.warn("[Nicecoze] init failed, ignore.")
            raise e

    def on_decorate_reply(self, e_context: EventContext):
        if e_context["reply"].type != ReplyType.TEXT:
            return
        reply = e_context["reply"]
        try:
            content_list = reply.content.strip().split('\n')
            # 提取CDP返回的Markdown图片链接中的网址，并修改ReplyType为IMAGE_URL，以便CoW自动下载Markdown链接中的图片
            if len(content_list)==2 and self.is_url(content_list[0]):
                if content_list[1] == f"![Image]({content_list[0]})":
                    reply = Reply(ReplyType.IMAGE_URL, content_list[0])
                    e_context["reply"] = reply
                    e_context.action = EventAction.CONTINUE
                    logger.info(f"[Nicecoze] Change ReplyType from TEXT to IMAGE_URL: {content_list[0]}")
                else:
                    logger.debug(f"[Nicecoze] URL in content but not a markdown image url.")
            # 去掉每行结尾的Markdown链接中网址部分的小括号，避免微信误以为“)”是网址的一部分导致微信中无法打开该页面
            else:
                new_content_list = [re.sub(r'\((https?://[^\s]+)\)$', r' \1', line) for line in content_list]
                reply = Reply(ReplyType.TEXT, '\n'.join(new_content_list))
                e_context["reply"] = reply
                e_context.action = EventAction.CONTINUE
        except Exception:
            pass

    def is_url(self, string):
        """
        判断字符串是否为URL的urllib库方法
        """
        try:
            result = urlparse(string)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def get_help_text(self, **kwargs):
        return "一款优化coze-discord-proxy返回结果的插件。"

