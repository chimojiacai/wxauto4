from wxauto4 import uia
from wxauto4.param import (
    WxParam, 
    WxResponse,
)
from wxauto4.utils.win32 import GetAllWindows
from wxauto4.ui_config import WxUI41Config
from wxauto4.logger import wxlog
import time

class NavigationBox:
    def __init__(self, control, parent):
        self.control: uia.Control = control
        self.root = parent.root
        self.parent = parent
        self.init()

    def init(self):
        # 获取头像按钮（在"微信"按钮上面，通常是第一个按钮）
        self.my_icon = None
        try:
            # 获取导航栏的所有按钮
            buttons = self.control.GetChildren()
            # 头像按钮通常是第一个按钮（在"微信"按钮上面）
            if buttons:
                self.my_icon = buttons[0]
        except:
            pass
        
        self.chat_icon = self.control.ButtonControl(Name=self._lang('微信'))
        self.contact_icon = self.control.ButtonControl(Name=self._lang('通讯录'))
        self.favorites_icon = self.control.ButtonControl(Name=self._lang('收藏'))
        self.files_icon = self.control.ButtonControl(Name=self._lang('聊天文件'))
        self.moments_icon = self.control.ButtonControl(Name=self._lang('朋友圈'))
        self.browser_icon = self.control.ButtonControl(Name=self._lang('搜一搜'))
        self.video_icon = self.control.ButtonControl(Name=self._lang('视频号'))
        self.stories_icon = self.control.ButtonControl(Name=self._lang('看一看'))
        self.mini_program_icon = self.control.ButtonControl(Name=self._lang('小程序面板'))
        self.phone_icon = self.control.ButtonControl(Name=self._lang('手机'))
        self.settings_icon = self.control.ButtonControl(Name=self._lang('更多'))
    
    def get_user_nickname(self) -> str:
        """获取当前登录者的昵称
        
        点击导航栏的头像按钮，获取弹出组件的name作为昵称
        
        Returns:
            str: 当前登录者的昵称，如果获取失败返回空字符串
        """
        try:
            # 唤起微信窗口到前台并居中
            self.parent._show()
            time.sleep(0.1)  # 减少等待时间：从0.3秒减少到0.1秒
            
            # 找到"微信"按钮并计算头像按钮位置
            chat_button = self.chat_icon
            if not chat_button.Exists(0.3):  # 减少超时时间：从0.5秒减少到0.3秒
                return ""
            
            rect = chat_button.BoundingRectangle
            button_height = rect.bottom - rect.top
            button_width = rect.right - rect.left
            avatar_x = rect.left + button_width // 2
            avatar_y = rect.top - button_height
            if avatar_y < 0:
                avatar_y = max(0, rect.top - 30)
            
            # 点击头像按钮
            uia.Click(avatar_x, avatar_y)
            time.sleep(0.3)  # 减少等待时间：从0.5秒减少到0.3秒
            
            # 从弹窗窗口中查找ContactHeadView控件
            nickname = ""
            try:
                wins = GetAllWindows(classname=WxUI41Config.MENU_WIN_CLS, name="Weixin")
                for win in wins:
                    control = uia.ControlFromHandle(win[0])
                    if control.ClassName in ['mmui::ProfileUniquePop', 'mmui::XPopover', WxUI41Config.MENU_CLS]:
                        # 从弹窗中查找ContactHeadView控件
                        try:
                            head_view = control.ButtonControl(
                                ClassName=WxUI41Config.CONTACT_HEAD_VIEW_CLS,
                                AutomationId=WxUI41Config.CONTACT_HEAD_VIEW_AUTOMATION_ID
                            )
                            if head_view.Exists(1):
                                nickname = head_view.Name if hasattr(head_view, 'Name') else ""
                                if nickname:
                                    break
                        except:
                            pass
                        
                        # 如果直接查找失败，递归查找
                        if not nickname:
                            def find_in_popup(ctrl, depth=0, max_depth=5):
                                if depth > max_depth:
                                    return None
                                try:
                                    for child in ctrl.GetChildren():
                                        if (child.ControlTypeName == 'ButtonControl' and 
                                            getattr(child, 'ClassName', '') == WxUI41Config.CONTACT_HEAD_VIEW_CLS):
                                            child_name = getattr(child, 'Name', '')
                                            if child_name and child_name.strip():
                                                return child_name.strip()
                                        result = find_in_popup(child, depth + 1, max_depth)
                                        if result:
                                            return result
                                except:
                                    pass
                                return None
                            
                            nickname = find_in_popup(control)
                            if nickname:
                                break
            except:
                pass
            
            # 关闭弹出组件
            try:
                self.chat_icon.Click()
                time.sleep(0.1)
            except:
                pass
            
            return nickname.strip() if nickname else ""
        except:
            try:
                self.chat_icon.Click()
            except:
                pass
            return ""

    def _lang(self, text):
        return text

    def switch_to_chat_page(self):
        self.chat_icon.Click()

    def switch_to_contact_page(self):
        self.contact_icon.Click()

    def switch_to_favorites_page(self):
        self.favorites_icon.Click()

    def switch_to_files_page(self):
        self.files_icon.Click()

    def switch_to_browser_page(self):
        self.browser_icon.Click()

    def switch_to_moments_page(self):
        self.moments_icon.Click()

    def switch_to_video_page(self):
        self.video_icon.Click()

    def switch_to_stories_page(self):
        self.stories_icon.Click()

    def switch_to_mini_program_page(self):
        self.mini_program_icon.Click()

    def switch_to_phone_page(self):
        self.phone_icon.Click()

    def switch_to_settings_page(self):
        self.settings_icon.Click()

