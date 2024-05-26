import logging
import os
import asyncio
from multiprocessing import Process


from nakuru.entities.components import *
from .platform_aiocq import AIOCQHTTP

try:
    from util.plugin_dev.api.v1.config import *
    from util.plugin_dev.api.v1.message import AstrMessageEvent, MessageResult, message_handler, CommandResult
    from util.plugin_dev.api.v1.bot import GlobalObject
    from util.plugin_dev.api.v1.register import register_platform
except ImportError:
    raise Exception("astrbot_plugin_aiocqhttp: 依赖导入失败。原因：请升级 AstrBot 到最新版本。")

class Main:
    def __init__(self, **kwargs) -> None:
        self.loop = asyncio.new_event_loop()
        self.NAMESPACE = "astrbot_plugin_aiocqhttp"
        put_config(self.NAMESPACE, "是否启用 aiocqhttp 适配器", "aiocqhttp_enable", False, "是否启用 aiocqhttp 适配器")
        put_config(self.NAMESPACE, "ws_reverse_host", "ws_reverse_host", "", "反向 WebSocket Host。")
        put_config(self.NAMESPACE, "ws_reverse_port", "ws_reverse_port", "", "反向 WebSocket Port")
        self.cfg = load_config(self.NAMESPACE)
        if self.cfg["aiocqhttp_enable"]:
            cfg_ = {
                "use_wsr": True,
                **self.cfg
            }
            self.inst = AIOCQHTTP(message_handler, **cfg_)
            if 'ctx' in kwargs:
                ctx = kwargs['ctx']
                assert(isinstance(ctx, GlobalObject))
                register_platform(self.NAMESPACE, self.inst, ctx)
                self.inst.ctx = ctx
                
            self.p = Process(target=self.inst.run_aiocqhttp, daemon=True).start()

    def run(self, ame: AstrMessageEvent):
        return CommandResult(
            hit=False,
            success=False,
            message_chain=[]
        )

    def info(self):
        return {
            "plugin_type": "platform",
            "name": "astrbot_plugin_aiocqhttp",
            "desc": "AstrBot 的又一个 OneBot 适配器，支持 Lagrange、Shamrock。",
            "help": "帮助信息查看：https://github.com/Soulter/astrbot_plugin_aiocqhttp",
            "version": "preview",
            "author": "Soulter",
            "repo": "https://github.com/Soulter/astrbot_plugin_aiocqhttp"
        }
