import logging, time

from util.plugin_dev.api.v1.platform import Platform
from util.plugin_dev.api.v1.bot import GlobalObject
from util.plugin_dev.api.v1.message import AstrBotMessage, MessageMember
from util.cmd_config import CmdConfig
from aiocqhttp import CQHttp, Event
from nakuru.entities.components import *
from SparkleLogging.utils.core import LogManager
from logging import Logger

try:
    from util.plugin_dev.api.v1.message import MessageType
except ImportError:
    from type.message import MessageType

logger: Logger = LogManager.GetLogger(log_name='astrbot-core')

class AIOCQHTTP(Platform):
    def __init__(self, message_handler: callable, **kwargs) -> None:
        message_handler = message_handler
        super().__init__(message_handler)
        self.kwargs = kwargs
        self.cc = CmdConfig()
        self.ctx: GlobalObject = None
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)   
        
    def compat_onebot2astrbotmsg(self, event: Event) -> AstrBotMessage:
        if not self.ctx:
            logger.warning("aiocqhttp 适配器没有获取到机器人上下文，请升级 AstrBot 到最新版本。")
            return
        
        abm = AstrBotMessage()
        abm.self_id = str(event.self_id)
        abm.tag = "aiocqhttp"
        
        abm.sender = MessageMember(str(event.sender['user_id']), event.sender['nickname'])        

        if event['message_type'] == 'group':
            abm.type = MessageType.GROUP_MESSAGE
        elif event['message_type'] == 'private':
            abm.type = MessageType.FRIEND_MESSAGE
        
        if self.ctx.unique_session:
            abm.session_id = abm.sender.user_id
        else:
            abm.session_id = str(event.group_id) if abm.type == MessageType.GROUP_MESSAGE else abm.sender.user_id
        
        abm.message_id = str(event.message_id)
        abm.message = []
        
        message_str = ""
        for m in event.message:
            t = m['type']
            a = None
            if t == 'at':
                a = At(**m['data'])
                abm.message.append(a)
            if t == 'text':
                a = Plain(text=m['data']['text'])
                message_str += m['data']['text'].strip()
                abm.message.append(a)
            if t == 'image':
                a = Image(file=m['data']['file'])
                abm.message.append(a)
        abm.timestamp = int(time.time())
        abm.message_str = message_str
        
        return abm
            
    def run_aiocqhttp(self):
        kwargs = self.kwargs
        if not (kwargs['use_wsr'] and kwargs['ws_reverse_host'] and kwargs['ws_reverse_port']):
            return
        self.bot = CQHttp()
        
        @self.bot.on_message('group')
        async def group(event: Event):
            abm = self.compat_onebot2astrbotmsg(event)
            if abm:
                await self.handle_msg(event, abm)
            return {'reply': event.message}
        
        self.bot.run(host=kwargs['ws_reverse_host'], port=int(kwargs['ws_reverse_port']), use_ws_reverse=True)
        
    async def handle_msg(self, event: Event, message: AstrBotMessage):
        await super().handle_msg()
        
        nicks = self.ctx.nick
        
        # 检查是否回复
        reply = False
        
        for msg in message.message:
            if type(msg) == At and str(msg.qq) == message.self_id:
                reply = True
                break
        
        if message.type == MessageType.FRIEND_MESSAGE:
            reply = True
                
        if not reply:
            for nick in nicks:
                if message.message_str.startswith(nick):
                    reply = True
                    break
                
        if not reply:
            return
        
        # 解析 role
        sender_id = str(message.sender.user_id)
        if sender_id == self.cc.get('admin_qq', '') or \
                sender_id in self.cc.get('other_admins', []):
            role = 'admin'
        else:
            role = 'member'
        
        message_result = await self.message_handler(
            message=message,
            session_id=message.session_id,
            role=role,
            platform='astrbot_plugin_aiocqhttp'
        )
        
        if message_result is None:
            return
        await self.reply_msg(event, message, message_result.result_message)
        if message_result.callback is not None:
            message_result.callback()
        
    async def reply_msg(self,
                        event: Event,
                        message: AstrBotMessage,
                        result_message: list):
        await super().reply_msg()
        """
        插件开发者请使用send方法, 可以不用直接调用这个方法。
        """
        await self.bot.send(event, result_message)
        