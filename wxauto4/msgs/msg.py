from wxauto4.utils.tools import (
    detect_message_direction
)
from wxauto4 import uia
from wxauto4.ui_config import WxUI41Config
from .mattr import (
    SystemMessage,
    FriendMessage,
    SelfMessage
)
from .mtype import *
from . import self as selfmsg
from . import friend as friendmsg
from typing import (
    TYPE_CHECKING,
    Literal,
    Dict,
    Any
)
import time
import os
import re

if TYPE_CHECKING:
    from wxauto4.ui.chatbox import ChatBox

def _detect_direction_by_position(control: uia.Control, parent: 'ChatBox') -> tuple:
    """通过消息控件在聊天窗口中的位置来判断方向（备用方法）
    
    Returns:
        tuple: (direction, confidence) - direction 为 'left' 或 'right', confidence 为置信度 (0-1)
    """
    try:
        control_rect = control.BoundingRectangle
        msgbox_rect = parent.msgbox.BoundingRectangle
        
        # 计算消息中心点和消息框中心点
        msg_center_x = (control_rect.left + control_rect.right) / 2
        msgbox_center_x = (msgbox_rect.left + msgbox_rect.right) / 2
        msgbox_width = msgbox_rect.right - msgbox_rect.left
        
        # 计算位置比例：正数表示在右侧，负数表示在左侧
        position_ratio = (msg_center_x - msgbox_center_x) / (msgbox_width / 2) if msgbox_width > 0 else 0
        
        # 如果位置比例明显偏向一侧，使用位置判断
        # 阈值：降低到5%，因为有些消息可能位置不够明显
        threshold = 0.05
        
        # 如果位置比例接近0（在中心），可能是计算问题，尝试使用消息控件的左边界来判断
        if abs(position_ratio) < 0.01:
            # 如果消息控件的左边界在消息框的右半部分，可能是自己发送的
            msg_left_ratio = (control_rect.left - msgbox_rect.left) / msgbox_width if msgbox_width > 0 else 0.5
            if msg_left_ratio > 0.6:
                # 消息左边界在消息框右半部分，很可能是自己发送的
                return 'right', 0.5
            elif msg_left_ratio < 0.4:
                # 消息左边界在消息框左半部分，很可能是好友发送的
                return 'left', 0.5
        
        if position_ratio > threshold:
            # 明显在右侧，自己发送
            confidence = min(abs(position_ratio) * 2, 1.0)  # 增强置信度
            return 'right', confidence
        elif position_ratio < -threshold:
            # 明显在左侧，好友发送
            confidence = min(abs(position_ratio) * 2, 1.0)  # 增强置信度
            return 'left', confidence
        else:
            # 位置不明确，返回 None
            return None, 0.0
    except:
        return None, 0.0

def parse_msg_attr(
    control: uia.Control,
    parent: 'ChatBox'
):
    msg_direction_hash = {
        'left': 'friend',
        'right': 'self'
    }
    if control.AutomationId:
        # 方法1：通过截图检测（主要方法）
        msg_screenshot = control.ScreenShot()
        msg_direction, msg_direction_distence = detect_message_direction(msg_screenshot)
        os.remove(msg_screenshot)
        
        # 方法2：通过控件位置检测（备用方法，用于验证和修正）
        position_direction, position_confidence = _detect_direction_by_position(control, parent)
        
        # 如果截图检测的结果与位置检测不一致，且位置检测的置信度较高，使用位置检测的结果
        # 这样可以修正截图检测的错误
        if position_direction and position_confidence > 0.3:
            if position_direction != msg_direction:
                # 位置检测与截图检测不一致，且位置检测置信度较高，使用位置检测结果
                msg_direction = position_direction
                msg_direction_distence = position_confidence * 1000  # 转换为距离格式
        
        msg_attr = msg_direction_hash.get(msg_direction)

        additonal_attr = {
            'direction': msg_direction,
            'direction_distence': msg_direction_distence
        }
        
    else:
        msg_attr = 'system'

    if msg_attr == 'system':
        return SystemMessage(control, parent)
    elif msg_attr == 'friend':
        # return FriendMessage(control, parent)
        return parse_msg_type(control, parent, 'Friend', additonal_attr)
    elif msg_attr == 'self':
        # return SelfMessage(control, parent)
        return parse_msg_type(control, parent, 'Self', additonal_attr)

def _find_message_type_from_children(control: uia.Control) -> tuple:
    """从子控件中查找消息类型和内容
    返回: (message_type, content_text, child_control)
    """
    try:
        children = control.GetChildren()
        for child in children:
            child_classname = child.ClassName
            child_name = child.Name
            
            # 优先检查 ChatBubbleReferItemView（图片、动画表情等）
            if child_classname == WxUI41Config.MSG_REFER_ITEM_CLS:
                name_result = _classify_by_name(child_name)
                if name_result:
                    return (name_result, child_name, child)
            
            # 检查 ChatTextItemView（文本消息）
            elif child_classname == WxUI41Config.MSG_TEXT_ITEM_CLS:
                # 如果是文本消息，继续检查是否有其他更重要的子控件
                pass
            
            # 检查其他特殊类型
            classname_result = _classify_by_classname(child_classname)
            if classname_result:
                return (classname_result, child_name, child)
    except:
        pass
    return (None, None, None)

def parse_msg_type(
        control: uia.Control,
        parent,
        attr: Literal['Self', 'Friend'],
        additonal_attr: Dict[str, Any]
    ):
    """
    多层次消息类型识别算法
    基于ClassName、Name等多重验证确保识别准确性
    """
    if attr == 'Friend':
        msgtype = friendmsg
    else:
        msgtype = selfmsg

    msg_text = control.Name
    msg_classname = control.ClassName
    msg_automation_id = control.AutomationId
    
    # 第一层：ClassName强特征识别（最可靠）
    classname_result = _classify_by_classname(msg_classname)
    if classname_result:
        return getattr(msgtype, f'{attr}{classname_result}')(control, parent, additonal_attr)
    
    # 第二层：基于ClassName分类后的详细识别
    if msg_classname == WxUI41Config.MSG_BUBBLE_ITEM_CLS:
        # 先检查子控件，找到真正的消息类型（图片、动画表情等可能在子控件中）
        child_type, child_content, child_control = _find_message_type_from_children(control)
        if child_type:
            # 如果子控件有更明确的类型，使用子控件的信息
            # 但使用主控件作为消息控件（保持一致性）
            return getattr(msgtype, f'{attr}{child_type}')(control, parent, additonal_attr)
        
        # Name前缀特征识别
        prefix_result = _classify_by_name_prefix(msg_text)
        if prefix_result:
            return getattr(msgtype, f'{attr}{prefix_result}')(control, parent, additonal_attr)
        
        # Name完全匹配识别（图片、动画表情等）
        name_result = _classify_by_name(msg_text)
        if name_result:
            return getattr(msgtype, f'{attr}{name_result}')(control, parent, additonal_attr)
        
        # 如果都不匹配，归类为其他消息
        return getattr(msgtype, f'{attr}OtherMessage')(control, parent, additonal_attr)
    
    # 处理 ChatBubbleReferItemView（动画表情等）
    elif msg_classname == WxUI41Config.MSG_REFER_ITEM_CLS:
        # 通过名称识别
        name_result = _classify_by_name(msg_text)
        if name_result:
            return getattr(msgtype, f'{attr}{name_result}')(control, parent, additonal_attr)
        # 如果无法识别，归类为其他消息
        return getattr(msgtype, f'{attr}OtherMessage')(control, parent, additonal_attr)
    
    elif msg_classname == WxUI41Config.MSG_TEXT_ITEM_CLS:
        # 第三层：引用消息处理
        if _is_quote_message(msg_text):
            return getattr(msgtype, f'{attr}QuoteMessage')(control, parent, additonal_attr)
        else:
            return getattr(msgtype, f'{attr}TextMessage')(control, parent, additonal_attr)
    
    return getattr(msgtype, f'{attr}OtherMessage')(control, parent, additonal_attr)


def _classify_by_classname(classname: str) -> str:
    classname_mapping = {
        WxUI41Config.MSG_VOICE_ITEM_CLS: "VoiceMessage",
        WxUI41Config.MSG_CARD_ITEM_CLS: "PersonalCardMessage",
        # 注意：MSG_REFER_ITEM_CLS 可能用于多种消息类型（动画表情、引用消息等）
        # 需要通过名称进一步识别，不在这里直接映射
    }
    return classname_mapping.get(classname, "")


def _classify_by_name_prefix(name: str) -> str:
    if name.startswith("[链接]"):
        return "LinkMessage"

    elif name.startswith("位置"):
        return "LocationMessage"

    elif name.startswith("文件\n"):
        return "FileMessage"

    elif name.startswith("视频"):
        return "VideoMessage"

    return ""

def _classify_by_name(name: str) -> str:
    """通过消息名称识别消息类型"""
    if not name:
        return ""
    name = name.strip()
    if name == "图片":
        return "ImageMessage"
    elif name == "动画表情":
        return "EmojiMessage"
    elif "表情" in name:
        return "EmojiMessage"
    return ""

def _is_quote_message(name: str) -> bool:
    quote_pattern = r'^(.*?)\s*\n引用\s+(.+?)\s+的消息\s*:\s*(.*)$'
    return bool(re.search(quote_pattern, name, re.DOTALL))
    
    
def parse_msg(
    control: uia.Control,
    parent
):
    # t0 = time.time()
    result = parse_msg_attr(control, parent)
    
    # t1 = time.time()
    # msgtype = str(result.__class__.__name__).ljust(20)
    # ms = int((t1 - t0)*1000)
    # print(f'parse_msg: {msgtype} {"□"*ms} {ms}ms')
    return result