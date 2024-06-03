# encoding:utf-8

import re

import plugins
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *


@plugins.register(
    name="NiceCoze",
    desire_priority=66,
    hidden=False,
    desc="优化coze-discord-proxy的返回结果。",
    version="1.2",
    author="空心菜",
)
class NiceCoze(Plugin):
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
        try:
            channel = e_context["channel"]
            context = e_context["context"]
            content = e_context["reply"].content.strip()
            # 避免图片无法下载时，重复调用插件导致没有响应的问题
            if content.startswith("[DOWNLOAD_ERROR]"):
                return
            # 提取CDP返回的Markdown图片链接中的网址，并修改ReplyType为IMAGE_URL，以便CoW自动下载Markdown链接中的图片
            if all(x in content for x in ['![', 'http']) and any(x in content for x in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']):
                logger.debug(f"[Nicecoze] starting decorate_markdown_image, content={content}")
                replies = self.decorate_markdown_image(content)
                if replies:
                    logger.info(f"[Nicecoze] sending {len(replies)} images ...")
                    e_context["reply"].content = "[DOWNLOAD_ERROR]\n" + e_context["reply"].content
                    for reply in replies:
                        channel.send(reply, context)
                    e_context["reply"] = Reply(ReplyType.TEXT, f"{len(replies)}张图片已发送，收到了吗？")
                    e_context.action = EventAction.BREAK_PASS
                    return
            # 去掉每行结尾的Markdown链接中网址部分的小括号，避免微信误以为“)”是网址的一部分导致微信中无法打开该页面
            content_list = content.split('\n')
            new_content_list = [re.sub(r'\((https?://[^\s]+)\)$', r' \1', line) for line in content_list]
            if new_content_list != content_list:
                logger.info(f"[Nicecoze] parenthesis in the url has been removed, content={content}")
                reply = Reply(ReplyType.TEXT, '\n'.join(new_content_list).strip())
                e_context["reply"] = reply
        except Exception as e:
            logger.warn(f"[Nicecoze] on_decorate_reply failed, content={content}, error={e}")
        finally:
            e_context.action = EventAction.CONTINUE

    def decorate_markdown_image(self, content):
        # 完全匹配Coze画图的Markdown图片
        markdown_image_ciciai = r"([\S\s]*)\!?\[(?P<image_name>.*)\]\((?P<image_url>https\:\/\/\S+?\.ciciai\.com\/[\S]*\.png(\?[\S]*)?)\)([\S\s]*)"
        match_obj_ciciai = re.fullmatch(markdown_image_ciciai, content)
        if match_obj_ciciai and match_obj_ciciai.group('image_url'):
            image_name, image_url = match_obj_ciciai.group('image_name'), match_obj_ciciai.group('image_url')
            logger.info(f"[Nicecoze] markdown_image_ciciai found, image_name={image_name}, image_url={image_url}")
            reply = Reply(ReplyType.IMAGE_URL, image_url)
            return [reply]
        # 完全匹配一张Markdown图片（格式：`![name](url)`）
        markdown_image1 = r"\!\[(?P<image_name>.*)\]\((?P<image_url>https?\:\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(:[0-9]{1,5})?(\/[\S]*)\.(jpg|jpeg|png|gif|bmp|webp)(\?[\S]*)?)\)"
        match_obj1 = re.fullmatch(markdown_image1, content, re.DOTALL)
        if match_obj1 and match_obj1.group('image_url'):
            image_name, image_url = match_obj1.group('image_name'), match_obj1.group('image_url')
            logger.info(f"[Nicecoze] markdown_image1 found, image_name={image_name}, image_url={image_url}")
            reply = Reply(ReplyType.IMAGE_URL, image_url)
            return [reply]
        # 匹配多张Markdown图片(格式：`url\n![Image](url)`)
        markdown_image2 = r"(?P<image_url>https?\:\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(:[0-9]{1,5})?(\/[\S]*)\.(jpg|jpeg|png|gif|bmp|webp)(\?[\S]*)?)\n*\!\[Image\]\((?P=image_url)\)"
        match_iter2 = re.finditer(markdown_image2, content)
        replies = []
        for match in match_iter2:
            image_url = match.group('image_url')
            logger.info(f"[Nicecoze] markdown_image2 found, image_url={image_url}")
            reply = Reply(ReplyType.IMAGE_URL, image_url)
            replies.append(reply)
        if replies:
            return replies
        if content.startswith('![') and 'http' in content and any(img in content for img in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']):
            logger.info(f"[Nicecoze] it seems markdown image in the content but not matched, content={content}.")

    def get_help_text(self, **kwargs):
        return "优化coze-discord-proxy的返回结果。"

