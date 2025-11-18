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
            # 先唤起微信窗口到前台
            wxlog.debug("唤起微信窗口到前台...")
            self.parent._show()
            time.sleep(0.3)  # 等待窗口完全激活
            
            # 重新获取头像按钮（确保按钮是最新的）
            wxlog.debug("查找头像按钮...")
            
            # 方法：找到"微信"按钮，然后在其上方10像素的位置点击
            try:
                # 找到"微信"按钮
                chat_button = self.chat_icon
                if not chat_button.Exists(0.5):
                    wxlog.debug("未找到'微信'按钮")
                    return ""
                
                # 获取"微信"按钮的位置
                rect = chat_button.BoundingRectangle
                wxlog.debug(f"'微信'按钮位置: left={rect.left}, top={rect.top}, right={rect.right}, bottom={rect.bottom}")
                
                # 计算头像按钮的位置（微信按钮正上方，X坐标使用微信按钮的中心）
                # 头像按钮在微信按钮的正上方，偏移量约为按钮高度
                button_height = rect.bottom - rect.top
                button_width = rect.right - rect.left
                avatar_x = rect.left + button_width // 2  # 使用微信按钮的X中心
                avatar_y = rect.top - button_height  # 微信按钮正上方，偏移量为按钮高度
                
                wxlog.debug(f"按钮高度: {button_height}, 按钮宽度: {button_width}")
                
                # 确保Y坐标不为负数
                if avatar_y < 0:
                    avatar_y = max(0, rect.top - 30)  # 如果计算出的坐标超出屏幕，使用较小的固定值
                
                wxlog.debug(f"计算的头像按钮位置: x={avatar_x}, y={avatar_y}")
                
                # 使用绝对坐标点击
                wxlog.debug("使用绝对坐标点击头像按钮...")
                uia.Click(avatar_x, avatar_y)
                time.sleep(0.5)  # 等待弹出组件出现
                
                # 标记已点击（用于后续查找弹出组件）
                clicked = True
            except Exception as e:
                wxlog.debug(f"使用坐标点击失败: {e}")
                import traceback
                wxlog.debug(traceback.format_exc())
                clicked = False
            
            if not clicked:
                return ""
            
            # 查找弹出的组件窗口
            # 通常是一个弹出窗口，显示用户信息
            nickname = ""
            
            # 方法1: 直接查找ContactHeadView控件（用户信息弹窗中的头像按钮，Name就是昵称）
            try:
                wxlog.debug("=" * 60)
                wxlog.debug("方法1: 查找ContactHeadView控件...")
                # 等待一下让弹窗出现
                time.sleep(0.5)
                
                # 从主窗口查找ContactHeadView控件
                main_control = self.parent.control
                wxlog.debug(f"主窗口控件类型: {main_control.ControlTypeName}, 名称: {getattr(main_control, 'Name', 'N/A')}")
                
                # 方法1.1: 通过类名和AutomationId查找
                try:
                    head_view = main_control.ButtonControl(
                        ClassName=WxUI41Config.CONTACT_HEAD_VIEW_CLS,
                        AutomationId=WxUI41Config.CONTACT_HEAD_VIEW_AUTOMATION_ID
                    )
                    if head_view.Exists(1):
                        nickname = head_view.Name if hasattr(head_view, 'Name') else ""
                        wxlog.debug(f"✓ 方法1.1成功: 通过类名和AutomationId找到ContactHeadView, Name='{nickname}'")
                    else:
                        wxlog.debug("方法1.1失败: ContactHeadView控件不存在")
                except Exception as e:
                    wxlog.debug(f"方法1.1失败: {e}")
                
                # 方法1.2: 如果方法1.1失败，通过类名查找
                if not nickname:
                    try:
                        head_views = main_control.FindAll(
                            lambda c: c.ControlTypeName == 'ButtonControl' and 
                                     c.ClassName == WxUI41Config.CONTACT_HEAD_VIEW_CLS,
                            maxDepth=5
                        )
                        wxlog.debug(f"方法1.2: 通过类名找到 {len(head_views)} 个ContactHeadView控件")
                        for hv in head_views:
                            hv_name = getattr(hv, 'Name', '')
                            wxlog.debug(f"  ContactHeadView: Name='{hv_name}'")
                            if hv_name and hv_name.strip():
                                nickname = hv_name.strip()
                                wxlog.debug(f"✓ 方法1.2成功: 找到昵称 '{nickname}'")
                                break
                    except Exception as e:
                        wxlog.debug(f"方法1.2失败: {e}")
                
                # 方法1.3: 如果方法1.2失败，递归查找所有ButtonControl，查找ClassName为ContactHeadView的
                if not nickname:
                    try:
                        wxlog.debug("方法1.3: 递归查找ContactHeadView控件...")
                        def find_contact_head_view(control, depth=0, max_depth=5):
                            if depth > max_depth:
                                return None
                            try:
                                for child in control.GetChildren():
                                    child_type = child.ControlTypeName
                                    child_class = getattr(child, 'ClassName', '')
                                    child_name = getattr(child, 'Name', '')
                                    if child_type == 'ButtonControl' and child_class == WxUI41Config.CONTACT_HEAD_VIEW_CLS:
                                        wxlog.debug(f"    找到ContactHeadView: Name='{child_name}', 深度={depth}")
                                        if child_name and child_name.strip():
                                            return child_name.strip()
                                    result = find_contact_head_view(child, depth + 1, max_depth)
                                    if result:
                                        return result
                            except:
                                pass
                            return None
                        
                        nickname = find_contact_head_view(main_control)
                        if nickname:
                            wxlog.debug(f"✓ 方法1.3成功: 递归找到昵称 '{nickname}'")
                        else:
                            wxlog.debug("方法1.3失败: 递归未找到ContactHeadView")
                    except Exception as e:
                        wxlog.debug(f"方法1.3失败: {e}")
                        import traceback
                        wxlog.debug(traceback.format_exc())
                
            except Exception as e:
                wxlog.debug(f"方法1失败: {e}")
                import traceback
                wxlog.debug(traceback.format_exc())
            
            # 方法2: 如果方法1失败，尝试从主窗口查找弹出的组件
            if not nickname:
                try:
                    wxlog.debug("=" * 60)
                    wxlog.debug("方法2: 从主窗口查找弹出组件...")
                    # 查找主窗口下的弹出组件
                    main_control = self.parent.control
                    wxlog.debug(f"主窗口控件类型: {main_control.ControlTypeName}, 名称: {getattr(main_control, 'Name', 'N/A')}")
                    
                    # 尝试查找各种可能的弹出组件
                    popup_controls = []
                    try:
                        # 递归查找所有子控件
                        def find_popup_controls(control, depth=0, max_depth=3):
                            if depth > max_depth:
                                return
                            try:
                                children = control.GetChildren()
                                wxlog.debug(f"  深度 {depth}: 找到 {len(children)} 个子控件")
                                for child in children:
                                    child_name = getattr(child, 'Name', '')
                                    child_type = child.ControlTypeName
                                    if child_name and child_name.strip():
                                        # 如果名称不是常见的导航项，可能是弹出组件
                                        known_names = ['微信', '通讯录', '收藏', '聊天文件', '朋友圈', '搜一搜', '视频号', '看一看', '小程序面板', '手机', '更多', '导航']
                                        if child_name not in known_names:
                                            wxlog.debug(f"    找到可能的弹出组件: 类型={child_type}, 名称='{child_name}'")
                                            # 检查是否是标题或大文本（可能是昵称）
                                            if child_type in ['TextControl', 'Text'] or 'title' in child_name.lower():
                                                popup_controls.append((child, child_name))
                                                wxlog.debug(f"      → 添加到候选列表")
                                            find_popup_controls(child, depth + 1, max_depth)
                            except Exception as e:
                                wxlog.debug(f"    查找子控件时出错: {e}")
                        
                        find_popup_controls(main_control)
                        wxlog.debug(f"总共找到 {len(popup_controls)} 个候选弹出组件")
                    except Exception as e:
                        wxlog.debug(f"递归查找失败: {e}")
                        import traceback
                        wxlog.debug(traceback.format_exc())
                    
                    # 获取第一个弹出组件的名称（通常是最大的文本，可能是昵称）
                    if popup_controls:
                        wxlog.debug("检查候选弹出组件...")
                        # 优先选择TextControl类型的控件
                        for control, name in popup_controls:
                            wxlog.debug(f"  候选: 类型={control.ControlTypeName}, 名称='{name}'")
                            if control.ControlTypeName in ['TextControl', 'Text']:
                                nickname = name.strip()
                                wxlog.debug(f"✓ 方法2成功: 从TextControl找到昵称 '{nickname}'")
                                break
                        # 如果没找到TextControl，使用第一个
                        if not nickname and popup_controls:
                            nickname = popup_controls[0][1].strip()
                            wxlog.debug(f"✓ 方法2成功: 使用第一个候选找到昵称 '{nickname}'")
                    else:
                        wxlog.debug("方法2失败: 未找到候选弹出组件")
                except Exception as e:
                    wxlog.debug(f"从主窗口查找弹出组件失败: {e}")
                    import traceback
                    wxlog.debug(traceback.format_exc())
            
            # 方法3: 查找菜单窗口（类似Menu类的方式）
            if not nickname:
                try:
                    wxlog.debug("=" * 60)
                    wxlog.debug("方法3: 查找菜单窗口...")
                    wins = GetAllWindows(classname=WxUI41Config.MENU_WIN_CLS, name="Weixin")
                    wxlog.debug(f"找到 {len(wins)} 个菜单窗口")
                    for win in wins:
                        control = uia.ControlFromHandle(win[0])
                        wxlog.debug(f"菜单窗口: 类名={control.ClassName}, 名称={getattr(control, 'Name', 'N/A')}")
                        if control.ClassName == WxUI41Config.MENU_CLS:
                            # 获取菜单的名称（通常是昵称）
                            nickname = control.Name if hasattr(control, 'Name') else ""
                            if nickname:
                                wxlog.debug(f"✓ 方法3成功: 从菜单窗口找到昵称 '{nickname}'")
                                break
                    if not nickname:
                        wxlog.debug("方法3失败: 未找到菜单窗口或菜单窗口无名称")
                except Exception as e:
                    wxlog.debug(f"查找菜单窗口失败: {e}")
                    import traceback
                    wxlog.debug(traceback.format_exc())
            
            wxlog.debug("=" * 60)
            if nickname:
                wxlog.debug(f"✓ 最终获取到昵称: '{nickname}'")
            else:
                wxlog.debug("✗ 未能获取到昵称")
            wxlog.debug("=" * 60)
            
            # 关闭弹出组件（点击其他地方或按ESC）
            try:
                wxlog.debug("关闭弹出组件...")
                # 点击"微信"按钮来关闭弹出组件
                self.chat_icon.Click()
                time.sleep(0.1)
            except Exception as e:
                wxlog.debug(f"关闭弹出组件失败: {e}")
            
            return nickname.strip() if nickname else ""
        except Exception as e:
            # 如果出错，尝试关闭可能打开的弹出组件
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

