# encoding:utf-8

import re
import requests

import plugins
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *


@plugins.register(
    name="NiceCoze",
    desire_priority=66,
    hidden=False,
    desc="优化Coze返回结果中的图片和网址链接。",
    version="1.5",
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
            # 提取Coze返回的Markdown图片链接中的网址，并修改ReplyType为IMAGE_URL，以便CoW自动下载Markdown链接中的图片
            #if all(x in content for x in ['![', 'http']) and any(x in content for x in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']):
            if 'http' in content and any(x in content for x in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
                logger.debug(f"[Nicecoze] starting decorate_markdown_image, content={content}")
                replies = self.decorate_markdown_image(content)
                if replies:
                    logger.info(f"[Nicecoze] sending {len(replies)} images ...")
                    e_context["reply"].content = "[DOWNLOAD_ERROR]\n" + e_context["reply"].content
                    for reply in replies:
                        channel.send(reply, context)
                    #e_context["reply"] = Reply(ReplyType.TEXT, f"{len(replies)}张图片已发送，收到了吗？")
                    # “x张图片已发送，收到了吗？”提示的初衷是告诉我们画/搜了几张图片以及下载/发送失败了几张图片，可以将e_context["reply"]设置为None关闭该提示！
                    e_context["reply"] = None
                    e_context.action = EventAction.BREAK_PASS
                    return
            # 提取Coze返回的包含https://s.coze.cn/t/xxx网址的Markdown链接中的图片网址
            markdown_s_coze_cn = r"([\S\s]*)\!?\[(?P<link_name>.*)\]\((?P<link_url>https\:\/\/s\.coze\.cn\/t\/[\S]*?)\)([\S\s]*)"
            match_obj_s_coze_cn = re.fullmatch(markdown_s_coze_cn, content)
            if match_obj_s_coze_cn and match_obj_s_coze_cn.group('link_url'):
                link_url = match_obj_s_coze_cn.group('link_url')
                logger.info(f"[Nicecoze] match_obj_s_coze_cn found, link_url={link_url}")
                response = requests.get(url=link_url, allow_redirects=False)
                original_url = response.headers.get('Location')
                if response.status_code in [301, 302] and original_url and any(x in original_url for x in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
                    logger.info(f"[Nicecoze] match_obj_s_coze_cn found and original_url is a image url, original_url={original_url}")
                    reply = Reply(ReplyType.IMAGE_URL, original_url)
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                else:
                    logger.info(f"[Nicecoze] match_obj_s_coze_cn found but failed to get original_url or original_url is not a image url, response.status_code={response.status_code}, original_url={original_url}")
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
        # 完全匹配Coze画图的Markdown图片，coze.com对应ciciai.com，coze.cn对应coze.cn
        markdown_image_official = r"([\S\s]*)\!?\[(?P<image_name>.*)\]\((?P<image_url>https\:\/\/\S+?\.(ciciai\.com|coze\.cn)\/[\S]*\.png(\?[\S]*)?)\)([\S\s]*)"
        match_obj_official = re.fullmatch(markdown_image_official, content)
        if match_obj_official and match_obj_official.group('image_url'):
            image_name, image_url = match_obj_official.group('image_name'), match_obj_official.group('image_url')
            logger.info(f"[Nicecoze] markdown_image_official found, image_name={image_name}, image_url={image_url}")
            reply = Reply(ReplyType.IMAGE_URL, image_url)
            return [reply]
        # 完全匹配一张Markdown图片（格式：`![name](url)`）
        markdown_image_single = r"\!\[(?P<image_name>.*)\]\((?P<image_url>https?\:\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(:[0-9]{1,5})?(\/[\S]*)\.(jpg|jpeg|png|gif|bmp|webp)(\?[\S]*)?)\)"
        match_obj_single = re.fullmatch(markdown_image_single, content, re.DOTALL)
        if match_obj_single and match_obj_single.group('image_url'):
            image_name, image_url = match_obj_single.group('image_name'), match_obj_single.group('image_url')
            logger.info(f"[Nicecoze] markdown_image_single found, image_name={image_name}, image_url={image_url}")
            reply = Reply(ReplyType.IMAGE_URL, image_url)
            return [reply]
        # 匹配多张Markdown图片(格式：`url\n![Image](url)`)
        markdown_image_multi = r"(?P<image_url>https?\:\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(:[0-9]{1,5})?(\/[\S]*)\.(jpg|jpeg|png|gif|bmp|webp)(\?[\S]*)?)\n*\!\[Image\]\((?P=image_url)\)"
        match_iter_multi = re.finditer(markdown_image_multi, content)
        replies = []
        for match in match_iter_multi:
            image_url = match.group('image_url')
            logger.info(f"[Nicecoze] markdown_image_multi found, image_url={image_url}")
            reply = Reply(ReplyType.IMAGE_URL, image_url)
            replies.append(reply)
        if replies:
            return replies
        if content.startswith('![') and 'http' in content and any(img in content for img in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']):
            logger.info(f"[Nicecoze] it seems markdown image in the content but not matched, content={content}.")

    def get_help_text(self, **kwargs):
        return "优化Coze返回结果中的图片和网址链接。"
