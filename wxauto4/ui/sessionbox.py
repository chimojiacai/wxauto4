from __future__ import annotations
from wxauto4 import uia
from wxauto4.param import (
    WxParam,
    WxResponse,
)
from wxauto4.languages import MENU_OPTIONS
from wxauto4.ui.component import Menu
from wxauto4.utils.win32 import SetClipboardText
from wxauto4.logger import wxlog
from wxauto4.ui_config import WxUI41Config
import time
from typing import (
    Union,
    List
)
import re


class SessionBox:
    def __init__(self, control, parent):
        self.control: uia.Control = control
        self.root = parent.root
        self.parent = parent
        self.init()

    def init(self):
        self.searchbox = self.control.GroupControl(ClassName=WxUI41Config.SESSION_SEARCH_FIELD_CLS).EditControl()
        self.session_list = self.control.GroupControl(ClassName=WxUI41Config.SESSION_LIST_CLS).\
            ListControl(ClassName=WxUI41Config.SESSION_TABLE_CLS, Name="会话")
        self.search_content = self.parent.control.WindowControl(ClassName=WxUI41Config.SESSION_SEARCH_CONTENT_CLS)
        
    def roll_up(self, n: int=5):
        self.control.MiddleClick()
        self.control.WheelUp(wheelTimes=n)

    def roll_down(self, n: int=5):
        self.control.MiddleClick()
        self.control.WheelDown(wheelTimes=n)

    def get_session(self) -> List[SessionElement]:
        """获取会话列表
        
        如果找不到会话列表，会尝试多种方式定位
        """
        # 首先尝试标准方式
        if self.session_list.Exists(0):
            children = self.session_list.GetChildren()
            if children:
                return [SessionElement(i, self) for i in children]
        
        # 如果标准方式失败，尝试直接查找ListControl
        wxlog.debug("标准方式获取会话列表失败，尝试备用方式...")
        try:
            # 尝试在SessionBox中直接查找ListControl
            list_controls = []
            def find_list_controls(control, depth=0, max_depth=3):
                """递归查找ListControl"""
                if depth > max_depth:
                    return []
                results = []
                try:
                    if control.ControlTypeName == 'ListControl':
                        # 检查是否是会话列表（通常包含"会话"或有很多子元素）
                        children = control.GetChildren()
                        if len(children) > 0 or '会话' in (control.Name or ''):
                            results.append(control)
                    for child in control.GetChildren():
                        results.extend(find_list_controls(child, depth+1, max_depth))
                except:
                    pass
                return results
            
            list_controls = find_list_controls(self.control)
            
            # 优先使用名称包含"会话"的，或者子元素最多的
            if list_controls:
                # 按子元素数量排序
                list_controls.sort(key=lambda c: len(c.GetChildren()), reverse=True)
                target_list = list_controls[0]
                wxlog.debug(f"找到备用会话列表: {target_list.ClassName}, 子元素数: {len(target_list.GetChildren())}")
                
                children = target_list.GetChildren()
                if children:
                    # 更新session_list引用
                    self.session_list = target_list
                    return [SessionElement(i, self) for i in children]
        except Exception as e:
            wxlog.debug(f"备用方式获取会话列表失败: {e}")
        
        return []

    def search(
            self, 
            keywords: str,
            force: bool = False,
            force_wait: Union[float, int] = 0.5
        ):
        """搜索会话
        
        Args:
            keywords: 搜索关键词
            force: 是否强制搜索（等待固定时间）
            force_wait: 强制搜索等待时间
        """
        try:
            wxlog.debug(f"开始搜索: {keywords}")
            
            # 点击搜索框并清空
            if not self.searchbox.Exists(0.5):
                wxlog.debug("搜索框不存在")
                return []
            
            self.searchbox.Click()
            time.sleep(0.1)
            self.searchbox.SendKeys('{Ctrl}a')  # 全选
            time.sleep(0.1)
            
            # 设置剪贴板并粘贴
            SetClipboardText(keywords)
            time.sleep(0.1)
            
            # 尝试多种粘贴方式
            try:
                self.searchbox.SendKeys('{Ctrl}v')
                time.sleep(0.2)
            except:
                try:
                    self.searchbox.RightClick()
                    time.sleep(0.2)
                    menu = Menu(self)
                    if menu.exists(0.5):
                        menu.select('粘贴')
                        time.sleep(0.2)
                except Exception as e:
                    wxlog.debug(f"粘贴失败: {e}")
            
            # 触发搜索（点击搜索框外部或按回车）
            self.searchbox.MiddleClick()
            time.sleep(0.3)  # 等待搜索结果出现

            if force:
                time.sleep(force_wait)

            # 获取搜索结果
            try:
                if not self.search_content.Exists(1):
                    wxlog.debug("搜索内容窗口不存在")
                    return []
                
                search_result = self.search_content.ListControl()
                if not search_result.Exists(0.5):
                    wxlog.debug("搜索结果列表不存在")
                    return []
                
                children = search_result.GetChildren()
                wxlog.debug(f"找到 {len(children)} 个搜索结果")
                return [SearchResultElement(i) for i in children]
            except Exception as e:
                wxlog.debug(f"获取搜索结果失败: {e}")
                return []
                
        except Exception as e:
            wxlog.debug(f"搜索过程出错: {e}")
            return []
    
    def switch_chat(
        self,
        keywords: str, 
        exact: bool = True,
        force: bool = False,
        force_wait: Union[float, int] = 0.5
    ):
        wxlog.debug(f"切换聊天窗口: {keywords}, {exact}, {force}, {force_wait}")
        
        # 清理关键词（去掉可能的时间戳等信息）
        clean_keywords = keywords.split('?')[0].split('，')[0].split(',')[0].strip()
        
        # 使用搜索框搜索
        wxlog.debug(f"使用搜索框搜索: {clean_keywords}")
        try:
            # 执行搜索
            search_result = self.search(clean_keywords, force, force_wait)
            
            # 等待搜索内容窗口出现
            t0 = time.time()
            max_wait = min(WxParam.SEARCH_CHAT_TIMEOUT, 3)  # 最多等待3秒
            while not self.search_content.Exists(0.5) and (time.time() - t0) < max_wait:
                time.sleep(0.1)
            
            if not self.search_content.Exists(0):
                wxlog.debug("搜索内容窗口未出现")
                return None
            
            # 获取搜索结果列表
            try:
                search_box = self.search_content.ListControl()
                if not search_box.Exists(1):
                    wxlog.debug("搜索结果列表不存在")
                    if self.search_content.Exists(0):
                        self.control.MiddleClick()
                    return None
            except Exception as e:
                wxlog.debug(f"获取搜索结果列表失败: {e}")
                if self.search_content.Exists(0):
                    self.control.MiddleClick()
                return None
            
            # 等待搜索结果出现
            t0 = time.time()
            search_result_items = []
            while (time.time() - t0) < max_wait:
                try:
                    search_result_items = search_box.GetChildren()
                    if search_result_items:
                        wxlog.debug(f"找到 {len(search_result_items)} 个搜索结果项")
                        break
                    time.sleep(0.1)
                except Exception as e:
                    wxlog.debug(f"等待搜索结果时出错: {e}")
                    time.sleep(0.1)
            
            if not search_result_items:
                wxlog.debug("未找到搜索结果项")
                if self.search_content.Exists(0):
                    self.control.MiddleClick()
                return None
            
            # 匹配搜索结果 - 优化匹配逻辑
            # 只匹配：联系人（好友）和群聊下的项，跳过标题和网络搜索结果
            matched_items = []
            
            # 需要识别搜索结果的分组结构
            # 搜索结果可能是：标题（如"联系人"、"群聊"、"聊天记录"、"搜索网络结果"） + 具体项
            current_section = None  # 当前所在的分组：'contact', 'group', 'chat_history', None
            
            for search_result_item in search_result_items:
                try:
                    text: str = search_result_item.Name
                    if not text:
                        continue
                    
                    wxlog.debug(f"检查搜索结果项: {text[:80]}")
                    
                    # 跳过不需要的标题项
                    skip_keywords = ['搜索网络结果', '搜索建议', '查看更多']
                    if any(keyword in text for keyword in skip_keywords):
                        wxlog.debug(f"跳过标题项: {text[:50]}")
                        continue
                    
                    # 识别分组标题
                    if text == '联系人':
                        current_section = 'contact'
                        wxlog.debug("进入联系人分组")
                        continue
                    elif text == '群聊':
                        current_section = 'group'
                        wxlog.debug("进入群聊分组")
                        continue
                    elif text == '聊天记录':
                        current_section = 'chat_history'
                        wxlog.debug("进入聊天记录分组")
                        continue
                    elif '搜索网络结果' in text or '网络' in text:
                        current_section = None  # 网络结果部分，不处理
                        wxlog.debug("跳过网络搜索结果部分")
                        continue
                    
                    # 提取主要名称（去掉"包含:"等后缀信息）
                    main_text = text.split('\n')[0].split('包含:')[0].strip()
                    
                    # 判断是否匹配关键词
                    is_match = False
                    match_text = main_text
                    
                    if exact:
                        # 精确匹配
                        if main_text == clean_keywords or main_text == keywords:
                            is_match = True
                        elif text == clean_keywords or text == keywords:
                            is_match = True
                            match_text = text
                        elif (
                            ' 微信号: ' in text
                            and (split:=text.split(' 微信号: '))[-1].lower() == clean_keywords.lower()
                        ):
                            is_match = True
                            match_text = split[0]
                        elif (
                            ' 昵称: ' in text
                            and (split:=text.split(' 昵称: '))[-1].lower() == clean_keywords.lower()
                        ):
                            is_match = True
                            match_text = split[0]
                    else:
                        # 模糊匹配
                        if clean_keywords in main_text or keywords in main_text:
                            is_match = True
                        elif clean_keywords in text or keywords in text:
                            is_match = True
                            match_text = main_text if main_text else text
                    
                    # 只处理联系人和群聊下的匹配项
                    if is_match and current_section in ['contact', 'group']:
                        matched_items.append({
                            'item': search_result_item,
                            'text': match_text,
                            'type': current_section,
                            'full_text': text
                        })
                        wxlog.debug(f"找到匹配项: {match_text} (类型: {current_section})")
                    elif is_match:
                        wxlog.debug(f"找到匹配项但不在目标分组中: {match_text} (当前分组: {current_section})")
                        
                except Exception as e:
                    wxlog.debug(f"处理搜索结果项时出错: {e}")
                    continue
            
            if not matched_items:
                wxlog.debug("未找到匹配的联系人或群聊")
                if self.search_content.Exists(0):
                    self.control.MiddleClick()
                return None
            
            # 按优先级选择：联系人 > 群聊
            type_priority = {'contact': 0, 'group': 1}
            matched_items.sort(key=lambda x: type_priority.get(x['type'], 99))
            
            # 选择第一个匹配项
            selected = matched_items[0]
            wxlog.debug(f"选择匹配项: {selected['text']} (类型: {selected['type']})")
            
            try:
                selected['item'].Click()
                time.sleep(0.2)  # 减少等待时间：等待点击生效和窗口切换
                # 使用更可靠的方式验证：检查输入框的名称（who属性）
                # 这比get_info()更可靠，因为输入框加载更快
                try:
                    current_who = self.parent._chat_api.who
                    if current_who and (selected['text'] in current_who or current_who in selected['text']):
                        wxlog.debug(f"✓ 确认已切换到聊天窗口: {current_who}")
                    else:
                        wxlog.debug(f"当前聊天窗口: {current_who}, 目标: {selected['text']}")
                except Exception as e:
                    wxlog.debug(f"验证聊天窗口时出错（不影响继续执行）: {e}")
                # 移除额外等待，让调用方决定是否需要等待
                return selected['text']
            except Exception as e:
                wxlog.debug(f"点击搜索结果项失败: {e}")
                if self.search_content.Exists(0):
                    self.control.MiddleClick()
                return None
            
        except Exception as e:
            wxlog.debug(f"切换聊天窗口时出错: {e}")
            import traceback
            wxlog.debug(traceback.format_exc())
            if self.search_content.Exists(0):
                try:
                    self.control.MiddleClick()
                except:
                    pass
            return None

    def open_separate_window(self, name: str):
        """打开独立窗口（优化版：增强稳定性和错误处理，减少延迟）"""
        wxlog.debug(f"打开独立窗口: {name}")
        realname = self.switch_chat(name)
        if not realname:
            return WxResponse.failure('未找到会话')
        
        time.sleep(0.1)  # 减少等待时间：从0.3秒减少到0.1秒
        
        # 查找会话并双击打开独立窗口
        try:
            sessions = [i for i in self.get_session() if uia.IsElementInWindow(self.session_list, i.control)]
            if not sessions:
                return WxResponse.failure('未找到会话列表')
            
            # 查找匹配的会话
            target_session = None
            for session in sessions:
                if session.content.startswith(realname):
                    target_session = session
                    break
            
            if not target_session:
                return WxResponse.failure(f'未找到会话: {realname}')
            
            # 双击打开独立窗口
            target_session.double_click()
            time.sleep(0.2)  # 减少等待时间：从0.5秒减少到0.2秒，独立窗口打开通常很快
            
            return WxResponse.success(data={'nickname': realname})
        except Exception as e:
            wxlog.debug(f"打开独立窗口失败: {e}")
            return WxResponse.failure(f'打开独立窗口失败: {e}')


    def go_top(self):
        wxlog.debug("回到会话列表顶部")
        self.control.MiddleClick()
        self.control.SendKeys('{Home}')

    def go_bottom(self):
        wxlog.debug("回到会话列表底部")
        self.control.MiddleClick()
        self.control.SendKeys('{End}')
    
class SessionElement:
    def __init__(
            self, 
            control: uia.Control, 
            parent: SessionBox, 
        ):
        self.root = parent.root
        self.parent = parent
        self.control = control
        self.content = control.Name

    @property
    def texts(self) -> List[str]:
        """拆分当前会话控件中的文本行"""

        return [
            line for line in str(self.content).split('\n')
            if line and line.strip()
        ]

    @property
    def name(self) -> str:
        """会话名称"""

        if self.texts:
            return self.texts[0]
        return ''

    @property
    def unread_count(self) -> int:
        """未读消息数量"""

        unread_pattern = re.compile(r'\[(\d+)条\]')
        for text in self.texts:
            if match := unread_pattern.search(text):
                return int(match.group(1))
        return 0

    def _menu_option_text(self, option_key: str) -> str:
        option = MENU_OPTIONS.get(option_key, {})
        lang = getattr(WxParam, 'LANGUAGE', 'cn')
        text = option.get(lang) if isinstance(option, dict) else None
        if not text:
            text = option.get('cn') if isinstance(option, dict) else None
        return text or option_key

    def select_menu_option(self, option_key: str, wait=0.3):
        """根据配置语言选择菜单项"""

        option_text = self._menu_option_text(option_key)
        return self.select_option(option_text, wait)

    def __repr__(self):
        content = str(self.content).replace('\n', ' ')
        if len(content) > 5:
            content = content[:5] + '...'
        return f"<wxauto4 Session Element({content})>"
    
    def roll_into_view(self):
        uia.RollIntoView(self.control.GetParentControl(), self.control)

    # @uilock
    def _click(self, right: bool=False, double: bool=False):
        self.roll_into_view()
        if right:
            self.control.RightClick()
        elif double:
            self.control.DoubleClick()
        else:
            self.control.Click()

    def click(self):
        self._click()

    def right_click(self):
        self._click(right=True)

    def double_click(self):
        self._click()
        self._click(double=True)

    def select_option(self, option: str, wait=0.3):
        self.roll_into_view()
        self.control.RightClick()
        time.sleep(wait)
        menu = Menu(self.parent)
        return menu.select(option)

    def pin(self):
        """置顶聊天"""

        return self.select_menu_option('置顶')

    def unpin(self):
        """取消置顶聊天"""

        return self.select_menu_option('取消置顶')

    def mark_unread(self):
        """标记为未读"""

        return self.select_menu_option('标为未读')

    def toggle_mute(self):
        """切换消息免打扰状态"""

        return self.select_menu_option('消息免打扰')

    def open_in_separate_window(self):
        """在独立窗口中打开会话"""

        return self.select_menu_option('在独立窗口打开')

    def hide(self):
        """不显示聊天"""

        return self.select_menu_option('不显示聊天')

    def delete(self):
        """删除聊天"""

        return self.select_menu_option('删除聊天')

class SearchResultElement:
    def __init__(self, control):
        self.control = control
        self.content = control.Name
        self.type = control.ClassName

    def __repr__(self):
        content = str(self.content).replace('\n', ' ')
        if len(content) > 5:
            content = content[:5] + '...'
        return f"<wxauto4 Search Element({content})>"

    def get_all_text(self):
        return [
            line for line in str(self.content).split('\n')
            if line and line.strip()
        ]
    
    def click(self):
        uia.RollIntoView(self.control.GetParentControl(), self.control)
        self.control.Click()

    def close(self):
        self.control.SendKeys('{Esc}')
