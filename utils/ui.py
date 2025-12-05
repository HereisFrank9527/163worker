from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qfluentwidgets import (
    LineEdit, ComboBox, PushButton, ProgressBar, TextEdit, CheckBox,
    setTheme, Theme, FluentWindow, NavigationItemPosition,
    ScrollArea, CardWidget, FluentIcon as FIF,
    InfoBar, InfoBarIcon, InfoBarPosition, HyperlinkButton
)
import sys
import os
import threading
import requests

# 全局版本号变量
CURRENT_VERSION = "1.0.5"

from utils.api import APIHandler
from utils.downloader import SongDownloader
from utils.ncm_converter import NCMConverter

class PlaylistPage(ScrollArea):
    """歌单下载页面"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self.setObjectName("playlistPage")
        
        # 创建主组件
        self.view = QWidget()
        self.setWidget(self.view)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 创建卡片
        self.card = CardWidget(self.view)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setSpacing(15)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        
        # 歌单ID行
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("歌单ID:"))
        self.list_id_entry = LineEdit()
        self.list_id_entry.setFixedWidth(200)
        id_layout.addWidget(self.list_id_entry)
        id_layout.addStretch()
        self.card_layout.addLayout(id_layout)
        
        # 音质和速度限制行
        quality_speed_layout = QHBoxLayout()
        
        # 音质选择
        quality_speed_layout.addWidget(QLabel("音质:"))
        self.quality_combobox = ComboBox()
        quality_options = parent.api_handler.get_quality_options()
        self.quality_combobox.addItems(quality_options)
        self.quality_combobox.setCurrentText(parent.api_handler.get_default_quality())
        self.quality_combobox.setFixedWidth(100)
        quality_speed_layout.addWidget(self.quality_combobox)
        quality_speed_layout.addStretch()
        
        # 下载速度限制
        quality_speed_layout.addWidget(QLabel("下载速度(KiB/s):"))
        self.speed_entry = LineEdit()
        self.speed_entry.setText("2048")
        self.speed_entry.setFixedWidth(80)
        quality_speed_layout.addWidget(self.speed_entry)
        quality_speed_layout.addWidget(QLabel("0表示无限制"))
        self.card_layout.addLayout(quality_speed_layout)
        
        # API请求间隔行
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("API请求间隔(ms):"))
        self.interval_entry = LineEdit()
        self.interval_entry.setText(str(parent.api_handler.get_request_interval()))
        self.interval_entry.setFixedWidth(80)
        interval_layout.addWidget(self.interval_entry)
        self.save_interval_button = PushButton("保存")
        self.save_interval_button.clicked.connect(parent.save_request_interval)
        interval_layout.addWidget(self.save_interval_button)
        interval_layout.addStretch()
        self.card_layout.addLayout(interval_layout)
        
        # 保存路径行
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存路径:"))
        self.save_path_entry = LineEdit()
        self.save_path_entry.setText("./downloads")
        path_layout.addWidget(self.save_path_entry)
        self.browse_button = PushButton("浏览")
        self.browse_button.clicked.connect(parent.browse_save_path)
        path_layout.addWidget(self.browse_button)
        self.card_layout.addLayout(path_layout)
        
        # 跳过已存在文件复选框
        self.skip_existing_checkbox = CheckBox("下载时跳过已存在的同名文件")
        self.skip_existing_checkbox.setChecked(True)  # 默认勾选
        self.card_layout.addWidget(self.skip_existing_checkbox)
        
        # 命名格式选择
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出文件名格式:"))
        self.filename_format_combobox = ComboBox()
        self.filename_format_combobox.addItems(["歌名 - 作者", "作者 - 歌名"])
        self.filename_format_combobox.setCurrentIndex(0)  # 默认选择"歌名 - 作者"
        self.filename_format_combobox.setFixedWidth(150)
        format_layout.addWidget(self.filename_format_combobox)
        format_layout.addStretch()
        self.card_layout.addLayout(format_layout)
        
        # 按钮行
        button_layout = QHBoxLayout()
        self.download_button = PushButton("开始下载")
        self.download_button.clicked.connect(parent.start_download)
        button_layout.addWidget(self.download_button)
        
        self.stop_download_button = PushButton("停止下载")
        self.stop_download_button.clicked.connect(parent.stop_download_task)
        self.stop_download_button.setEnabled(False)
        button_layout.addWidget(self.stop_download_button)
        
        # API检查按钮
        self.check_api_button = PushButton("检查api")
        self.check_api_button.clicked.connect(parent.test_api_feasibility)
        button_layout.addWidget(self.check_api_button)
        
        button_layout.addStretch()
        self.card_layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.card_layout.addWidget(self.progress_bar)
        
        # 进度标签
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.card_layout.addWidget(self.progress_label)
        
        # 添加卡片到主布局
        self.main_layout.addWidget(self.card)
        self.main_layout.addStretch()


class NcmConvertPage(ScrollArea):
    """NCM转换页面"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self.setObjectName("ncmConvertPage")
        
        # 创建主组件
        self.view = QWidget()
        self.setWidget(self.view)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 创建卡片
        self.card = CardWidget(self.view)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setSpacing(15)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        
        # 源文件夹行
        input_path_layout = QHBoxLayout()
        input_path_layout.addWidget(QLabel("源文件夹:"))
        self.ncm_input_entry = LineEdit()
        self.ncm_input_entry.setText("./")
        input_path_layout.addWidget(self.ncm_input_entry)
        self.ncm_browse_input = PushButton("浏览")
        self.ncm_browse_input.clicked.connect(parent.browse_ncm_input)
        input_path_layout.addWidget(self.ncm_browse_input)
        self.card_layout.addLayout(input_path_layout)
        
        # 目标文件夹行
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("目标文件夹:"))
        self.ncm_output_entry = LineEdit()
        self.ncm_output_entry.setText("./trans")
        output_path_layout.addWidget(self.ncm_output_entry)
        self.ncm_browse_output = PushButton("浏览")
        self.ncm_browse_output.clicked.connect(parent.browse_ncm_output)
        output_path_layout.addWidget(self.ncm_browse_output)
        self.card_layout.addLayout(output_path_layout)
        
        # 跳过已存在文件复选框
        self.ncm_skip_existing_checkbox = CheckBox("转换时跳过已存在的同名文件")
        self.ncm_skip_existing_checkbox.setChecked(True)  # 默认勾选
        self.card_layout.addWidget(self.ncm_skip_existing_checkbox)
        
        # 翻转文件名格式复选框
        self.ncm_flip_filename_checkbox = CheckBox("转换时翻转文件名格式（例如：作者 - 歌名 → 歌名 - 作者）")
        self.ncm_flip_filename_checkbox.setChecked(False)  # 默认不翻转
        self.card_layout.addWidget(self.ncm_flip_filename_checkbox)
        
        # 按钮行
        button_layout = QHBoxLayout()
        self.convert_button = PushButton("开始转换")
        self.convert_button.clicked.connect(parent.start_ncm_convert)
        button_layout.addWidget(self.convert_button)
        
        self.stop_convert_button = PushButton("停止转换")
        self.stop_convert_button.clicked.connect(parent.stop_convert_task)
        self.stop_convert_button.setEnabled(False)
        button_layout.addWidget(self.stop_convert_button)
        button_layout.addStretch()
        self.card_layout.addLayout(button_layout)
        
        # 进度条
        self.ncm_progress_bar = ProgressBar()
        self.ncm_progress_bar.setValue(0)
        self.card_layout.addWidget(self.ncm_progress_bar)
        
        # 进度标签
        self.ncm_progress_label = QLabel("准备就绪")
        self.ncm_progress_label.setAlignment(Qt.AlignCenter)
        self.card_layout.addWidget(self.ncm_progress_label)
        
        # 添加卡片到主布局
        self.main_layout.addWidget(self.card)
        self.main_layout.addStretch()


class HomePage(ScrollArea):
    """主页"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self.setObjectName("homePage")
        
        # 创建主组件
        self.view = QWidget()
        self.setWidget(self.view)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 创建卡片
        self.card = CardWidget(self.view)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setSpacing(20)
        self.card_layout.setContentsMargins(30, 30, 30, 30)
        
        # 项目标题
        self.title_label = QLabel("163worker")
        self.title_label.setStyleSheet("font-size: 36px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.card_layout.addWidget(self.title_label)
        
        # 项目描述
        self.desc_label = QLabel("网易云音乐下载器 & NCM转换器")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.card_layout.addWidget(self.desc_label)
        
        # 按钮布局
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(20)
        self.button_layout.setAlignment(Qt.AlignCenter)
        
        # 项目链接按钮
        self.github_button = HyperlinkButton(
            url='https://github.com/HereisFrank9527/163worker',
            text='GitHub项目链接',
            parent=self
        )
        self.button_layout.addWidget(self.github_button)
        
        #项目门户按钮
        self.website_button = HyperlinkButton(
            url='https://ncm.dgtsr.top/',
            text='项目网站',
            parent=self
        )
        self.button_layout.addWidget(self.website_button)

        # 赞助链接按钮
        self.afdian_button = HyperlinkButton(
            url='https://afdian.com/a/0xffff',
            text='赞助链接',
            parent=self
        )
        self.button_layout.addWidget(self.afdian_button)
        
        self.card_layout.addLayout(self.button_layout)
        
        # 添加卡片到主布局
        self.main_layout.addWidget(self.card)
        
        # 添加免责声明
        self.disclaimer_label = QLabel()
        self.disclaimer_label.setText("⚠️ 本项目仅供技术交流使用，尊重网易云版权，转换和下载的文件请在24小时内删除")
        self.disclaimer_label.setStyleSheet("background-color: #FFF3CD; color: #856404; padding: 10px; border-radius: 5px; font-size: 14px;")
        self.disclaimer_label.setAlignment(Qt.AlignCenter)
        self.disclaimer_label.setWordWrap(True)
        self.main_layout.addWidget(self.disclaimer_label)
        
        self.main_layout.addStretch()


class LogPage(ScrollArea):
    """日志页面"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self.setObjectName("logPage")
        
        # 创建主组件
        self.view = QWidget()
        self.setWidget(self.view)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 创建卡片
        self.card = CardWidget(self.view)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        
        # 日志文本框
        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.card_layout.addWidget(self.log_text)
        
        # 添加卡片到主布局
        self.main_layout.addWidget(self.card)
        self.main_layout.addStretch()


class MusicDownloaderUI(FluentWindow):
    """主窗口"""
    # 定义信号，用于在子线程中更新UI
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    ncm_progress_signal = pyqtSignal(int, str)
    download_complete_signal = pyqtSignal(int, int)
    download_error_signal = pyqtSignal(str)
    ncm_complete_signal = pyqtSignal(int, int)
    ncm_error_signal = pyqtSignal(str)
    button_state_signal = pyqtSignal(bool, bool)
    ncm_button_state_signal = pyqtSignal(bool, bool)
    api_test_signal = pyqtSignal(str, str, int)  # 用于API测试结果通知，参数：title, content, type(0:success, 1:warning, 2:error)
    version_signal = pyqtSignal(str)  # 用于更新最新版本号的信号
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网易云音乐下载器 & NCM转换器")
        self.resize(800, 600)
        
        # 初始化最新版本号
        self.latest_version = ""
        # 连接版本更新信号
        self.version_signal.connect(self.update_latest_version)
        
        # 获取最新版本号
        self.get_latest_version()
        
        # 连接信号槽
        self.log_signal.connect(self.log_slot)
        self.progress_signal.connect(self.progress_slot)
        self.ncm_progress_signal.connect(self.ncm_progress_slot)
        self.download_complete_signal.connect(self.download_complete_slot)
        self.download_error_signal.connect(self.download_error_slot)
        self.ncm_complete_signal.connect(self.ncm_complete_slot)
        self.ncm_error_signal.connect(self.ncm_error_slot)
        self.button_state_signal.connect(self.button_state_slot)
        self.ncm_button_state_signal.connect(self.ncm_button_state_slot)
        self.api_test_signal.connect(self.api_test_result_slot)
        
        # 初始化API处理器
        self.api_handler = APIHandler()
        self.downloader = SongDownloader(self.api_handler)
        
        # 尝试初始化NCM转换器
        try:
            self.ncm_converter = NCMConverter()
        except FileNotFoundError as e:
            self.ncm_converter = None
            InfoBar.warning(
                title="NCM转换器初始化失败",
                content=f"{e}\nNCM转换功能将不可用",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
        
        # 停止标志
        self.stop_download = False
        self.stop_convert = False
        
        # 创建页面
        self.home_page = HomePage(self)
        self.playlist_page = PlaylistPage(self)
        self.ncm_page = NcmConvertPage(self)
        self.log_page = LogPage(self)
        
        # 添加页面到导航栏
        self.addSubInterface(self.home_page, FIF.HOME, "主页")
        self.addSubInterface(self.playlist_page, FIF.CLOUD_DOWNLOAD, "歌单下载")
        self.addSubInterface(self.ncm_page, FIF.UPDATE, "NCM转换")
        self.addSubInterface(self.log_page, FIF.COMMAND_PROMPT, "日志", NavigationItemPosition.BOTTOM)
        
        # 获取页面组件引用
        self.list_id_entry = self.playlist_page.list_id_entry
        self.quality_combobox = self.playlist_page.quality_combobox
        self.speed_entry = self.playlist_page.speed_entry
        self.save_path_entry = self.playlist_page.save_path_entry
        self.skip_existing_checkbox = self.playlist_page.skip_existing_checkbox
        self.filename_format_combobox = self.playlist_page.filename_format_combobox
        self.download_button = self.playlist_page.download_button
        self.stop_download_button = self.playlist_page.stop_download_button
        self.progress_bar = self.playlist_page.progress_bar
        self.progress_label = self.playlist_page.progress_label
        
        self.ncm_input_entry = self.ncm_page.ncm_input_entry
        self.ncm_output_entry = self.ncm_page.ncm_output_entry
        self.ncm_skip_existing_checkbox = self.ncm_page.ncm_skip_existing_checkbox
        self.ncm_flip_filename_checkbox = self.ncm_page.ncm_flip_filename_checkbox
        self.convert_button = self.ncm_page.convert_button
        self.stop_convert_button = self.ncm_page.stop_convert_button
        self.ncm_progress_bar = self.ncm_page.ncm_progress_bar
        self.ncm_progress_label = self.ncm_page.ncm_progress_label
        
        self.log_text = self.log_page.log_text
        
        # 添加版本号显示到主页
        self.current_version_label = QLabel(f"当前版本: {CURRENT_VERSION}")
        self.current_version_label.setAlignment(Qt.AlignCenter)
        self.home_page.card_layout.addWidget(self.current_version_label)
        
        self.latest_version_label = QLabel("最新版本: 正在获取...")
        self.latest_version_label.setAlignment(Qt.AlignCenter)
        self.home_page.card_layout.addWidget(self.latest_version_label)
        
        # 添加帮助提示文字
        self.help_label = QLabel("如有问题，可前往网站寻求帮助")
        self.help_label.setAlignment(Qt.AlignCenter)
        self.help_label.setStyleSheet("color: #666666; font-size: 14px;")
        self.home_page.card_layout.addWidget(self.help_label)
        
        # 启动时自动测试API可行性
        self.test_api_feasibility()
        
        # 延迟显示MessageBox，确保主窗口已经加载完成
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.show_startup_message)
    

    
    def browse_save_path(self):
        """浏览保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if path:
            self.save_path_entry.setText(path)
    
    def browse_ncm_input(self):
        """浏览NCM源文件夹"""
        path = QFileDialog.getExistingDirectory(self, "选择NCM源文件夹")
        if path:
            self.ncm_input_entry.setText(path)
    
    def browse_ncm_output(self):
        """浏览NCM目标文件夹"""
        path = QFileDialog.getExistingDirectory(self, "选择NCM目标文件夹")
        if path:
            self.ncm_output_entry.setText(path)
    
    def start_download(self):
        """开始下载歌单"""
        list_id = self.list_id_entry.text().strip()
        quality = self.quality_combobox.currentText()
        save_path = self.save_path_entry.text()
        
        try:
            speed_limit = int(self.speed_entry.text())
        except ValueError:
            InfoBar.error(
                title="错误",
                content="下载速度必须是整数",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self
            )
            return
        
        if not list_id:
            InfoBar.error(
                title="错误",
                content="请输入歌单ID",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self
            )
            return
        
        # 重置停止标志
        self.stop_download = False
        
        # 禁用下载按钮，启用停止按钮
        self.download_button.setEnabled(False)
        self.stop_download_button.setEnabled(True)
        
        # 获取跳过已存在文件选项
        skip_existing = self.skip_existing_checkbox.isChecked()
        # 获取文件名格式
        filename_format = self.filename_format_combobox.currentIndex()  # 0: 歌名 - 作者, 1: 作者 - 歌名
        
        # 启动下载线程
        threading.Thread(target=self.download_playlist, args=(list_id, save_path, quality, speed_limit, skip_existing, filename_format), daemon=True).start()
    
    def download_playlist(self, list_id, save_path, quality, speed_limit, skip_existing, filename_format):
        """下载歌单的线程函数"""
        try:
            self.log(f"开始下载歌单: {list_id}")
            self.log(f"音质: {quality}, 保存路径: {save_path}")
            self.log(f"跳过已存在文件: {'是' if skip_existing else '否'}")
            self.log(f"文件名格式: {'歌名 - 作者' if filename_format == 0 else '作者 - 歌名'}")
            
            # 获取歌单歌曲
            self.log("正在获取歌单歌曲列表...")
            songs = self.api_handler.get_playlist_songs(list_id)
            self.log(f"获取到 {len(songs)} 首歌曲")
            
            # 开始下载
            success_count = 0
            fail_count = 0
            skip_count = 0
            total_songs = len(songs)
            
            for i, song in enumerate(songs):
                # 检查停止标志
                if self.stop_download:
                    self.log("下载已停止")
                    break
                
                # 通过信号槽更新进度
                progress = (i + 1) / total_songs * 100
                self.progress_signal.emit(int(progress), f"正在下载: {song['artist']} - {song['name']} ({i+1}/{total_songs})")
                
                self.log(f"[{i+1}/{total_songs}] 正在处理: {song['artist']} - {song['name']}")
                success, message = self.downloader.download_song(song, save_path, quality, speed_limit, skip_existing, filename_format)
                
                if success:
                    if "已跳过" in message:
                        self.log(f"[{i+1}/{total_songs}] {message}")
                        skip_count += 1
                    else:
                        self.log(f"[{i+1}/{total_songs}] 下载成功: {message}")
                        success_count += 1
                else:
                    self.log(f"[{i+1}/{total_songs}] 下载失败: {message}")
                    fail_count += 1
            
            # 通过信号槽更新完成状态
            self.progress_signal.emit(100, "下载完成")
            self.log(f"歌单下载完成! 成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}, 总计: {total_songs}")
            
            # 发送下载完成信号
            self.download_complete_signal.emit(success_count, fail_count)
        except KeyError as e:
            # 详细记录KeyError，特别是API响应结构问题
            self.log(f"下载失败: API响应结构异常 - {str(e)}")
            # 发送下载错误信号
            self.download_error_signal.emit(f"API响应结构异常: {str(e)}")
        except requests.RequestException as e:
            # 网络请求相关错误
            self.log(f"下载失败: 网络请求异常 - {str(e)}")
            self.download_error_signal.emit(f"网络请求异常: {str(e)}")
        except Exception as e:
            # 其他类型错误
            import traceback
            error_detail = traceback.format_exc()
            self.log(f"下载失败: 发生未知错误 - {str(e)}")
            self.log(f"错误详细信息: {error_detail}")
            self.download_error_signal.emit(f"未知错误: {str(e)}")
        finally:
            # 发送按钮状态更新信号
            self.button_state_signal.emit(True, False)
    
    def start_ncm_convert(self):
        """开始NCM转换"""
        if self.ncm_converter is None:
            InfoBar.error(
                title="错误",
                content="NCM转换器未初始化，无法使用转换功能",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self
            )
            return
        
        input_dir = self.ncm_input_entry.text()
        output_dir = self.ncm_output_entry.text()
        
        if not os.path.exists(input_dir):
            InfoBar.error(
                title="错误",
                content="源文件夹不存在",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self
            )
            return
        
        # 重置停止标志
        self.stop_convert = False
        
        # 获取跳过已存在文件选项
        skip_existing = self.ncm_skip_existing_checkbox.isChecked()
        # 获取翻转文件名格式选项
        flip_filename = self.ncm_flip_filename_checkbox.isChecked()
        
        # 禁用转换按钮，启用停止按钮
        self.convert_button.setEnabled(False)
        self.stop_convert_button.setEnabled(True)
        
        # 启动转换线程
        threading.Thread(target=self.convert_ncm_files, args=(input_dir, output_dir, skip_existing, flip_filename), daemon=True).start()
    
    def convert_ncm_files(self, input_dir, output_dir, skip_existing=False, flip_filename=False):
        """转换NCM文件的线程函数"""
        try:
            self.log(f"开始转换NCM文件，源目录: {input_dir}")
            self.log(f"跳过已存在文件: {'是' if skip_existing else '否'}")
            self.log(f"翻转文件名格式: {'是' if flip_filename else '否'}")
            
            # 获取所有NCM文件
            import glob
            ncm_files = glob.glob(os.path.join(input_dir, '*.ncm'))
            
            if not ncm_files:
                self.log("未找到NCM文件")
                # 发送转换完成信号，成功和失败计数都为0
                self.ncm_complete_signal.emit(0, 0)
                return
            
            self.log(f"找到 {len(ncm_files)} 个NCM文件")
            
            # 开始转换
            success_count = 0
            fail_count = 0
            skip_count = 0
            total_files = len(ncm_files)
            
            for i, ncm_file in enumerate(ncm_files):
                # 检查停止标志
                if self.stop_convert:
                    self.log("转换已停止")
                    break
                
                # 通过信号槽更新进度
                progress = (i + 1) / total_files * 100
                self.ncm_progress_signal.emit(int(progress), f"正在转换: {os.path.basename(ncm_file)} ({i+1}/{total_files})")
                
                self.log(f"[{i+1}/{total_files}] 正在处理: {os.path.basename(ncm_file)}")
                
                # 构建目标文件名
                ncm_basename = os.path.splitext(os.path.basename(ncm_file))[0]
                target_filename = f"{ncm_basename}.mp3"
                
                # 如果需要翻转文件名格式
                if flip_filename and " - " in ncm_basename:
                    # 分割歌手和歌名
                    parts = ncm_basename.split(" - ")
                    if len(parts) >= 2:
                        # 翻转顺序
                        name = " - ".join(parts[1:])
                        artist = parts[0]
                        target_filename = f"{name} - {artist}.mp3"
                
                # 检查目标文件是否已存在
                target_path = os.path.join(output_dir, target_filename)
                if skip_existing and os.path.exists(target_path):
                    self.log(f"[{i+1}/{total_files}] 已跳过: {target_filename}（文件已存在）")
                    skip_count += 1
                    continue
                
                # 执行转换
                success, message = self.ncm_converter.convert_single_file(ncm_file, output_dir)
                
                if success:
                    # 转换成功，检查转换后的文件名
                    converted_file = message
                    converted_basename = os.path.basename(converted_file)
                    converted_path = os.path.join(output_dir, converted_basename)
                    
                    # 如果文件名不符合要求，重命名
                    if converted_basename != target_filename and os.path.exists(converted_path):
                        try:
                            os.rename(converted_path, target_path)
                            self.log(f"[{i+1}/{total_files}] 转换成功: {target_filename}（已重命名）")
                        except Exception as e:
                            self.log(f"[{i+1}/{total_files}] 转换成功，但重命名失败: {str(e)}")
                    else:
                        self.log(f"[{i+1}/{total_files}] 转换成功: {target_filename}")
                    success_count += 1
                else:
                    self.log(f"[{i+1}/{total_files}] 转换失败: {message}")
                    fail_count += 1
            
            # 通过信号槽更新完成状态
            self.ncm_progress_signal.emit(100, "转换完成")
            self.log(f"NCM转换完成! 成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}, 总计: {total_files}")
            
            # 发送转换完成信号
            self.ncm_complete_signal.emit(success_count, fail_count)
        except Exception as e:
            self.log(f"转换失败: {str(e)}")
            
            # 发送转换错误信号
            self.ncm_error_signal.emit(str(e))
        finally:
            # 发送按钮状态更新信号
            self.ncm_button_state_signal.emit(True, False)
    
    def stop_download_task(self):
        """停止下载任务"""
        self.stop_download = True
        self.log("正在停止下载...")
    
    def save_request_interval(self):
        """保存API请求间隔设置"""
        try:
            interval = int(self.playlist_page.interval_entry.text())
            if interval < 0:
                raise ValueError("请求间隔不能为负数")
            
            self.api_handler.set_request_interval(interval)
            self.log(f"API请求间隔已设置为 {interval} 毫秒")
            InfoBar.success(
                title="成功",
                content=f"API请求间隔已设置为 {interval} 毫秒",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self
            )
        except ValueError as e:
            InfoBar.error(
                title="错误",
                content=f"请输入有效的请求间隔: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self
            )
    
    def test_api_feasibility(self):
        """测试API可行性"""
        def test_api():
            """测试API的线程函数"""
            try:
                # 测试歌单API
                self.log("正在测试API可行性...")
                # 使用一个公开的歌单ID进行测试
                test_playlist_id = "3778678"
                songs = self.api_handler.get_playlist_songs(test_playlist_id)
                
                if songs:
                    self.log("API测试成功")
                    # 使用信号槽机制显示InfoBar通知
                    self.api_test_signal.emit("API测试成功", "API服务正常，可以使用下载功能", 0)
                else:
                    self.log("API测试失败: 未获取到歌曲列表")
                    # 使用信号槽机制显示InfoBar通知
                    self.api_test_signal.emit("API测试警告", "API服务可能异常，获取歌曲列表为空。可手动再次检测", 1)
            except Exception as e:
                self.log(f"API测试失败: {str(e)}")
                # 使用信号槽机制显示InfoBar通知
                self.api_test_signal.emit("API测试失败", f"API服务异常，无法使用下载功能: {str(e)}。可手动再次检测", 2)
        
        # 在后台线程中测试API
        threading.Thread(target=test_api, daemon=True).start()
        
    def get_latest_version(self):
        """获取最新版本号"""
        def fetch_version():
            """获取版本号的线程函数"""
            try:
                url = "https://ncm.dgtsr.top/version/"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                latest_version = response.text.strip()
                self.version_signal.emit(latest_version)
            except Exception as e:
                self.log(f"获取最新版本号失败: {str(e)}")
                self.version_signal.emit("获取失败")
        
        # 在后台线程中获取最新版本号
        threading.Thread(target=fetch_version, daemon=True).start()
        
    def update_latest_version(self, version):
        """更新最新版本号显示的槽函数"""
        self.latest_version = version
        self.latest_version_label.setText(f"最新版本: {version}")
    
    def api_test_result_slot(self, title, content, type):
        """API测试结果通知槽函数"""
        if type == 0:
            # 成功
            InfoBar.success(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
        elif type == 1:
            # 警告
            InfoBar.warning(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
        else:
            # 错误
            InfoBar.error(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
    
    def stop_convert_task(self):
        """停止转换任务"""
        self.stop_convert = True
        self.log("正在停止转换...")
    
    def log(self, message):
        """记录日志"""
        # 通过信号槽机制更新日志，确保线程安全
        self.log_signal.emit(message)
    
    def log_slot(self, message):
        """日志更新槽函数"""
        self.log_text.append(message)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def progress_slot(self, progress, text):
        """进度更新槽函数"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(text)
    
    def download_complete_slot(self, success_count, fail_count):
        """下载完成槽函数"""
        if fail_count == 0:
            # 完全成功
            InfoBar.success(
                title="成功",
                content=f"歌单下载完成! 成功: {success_count}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
        elif success_count > 0:
            # 部分成功
            InfoBar.warning(
                title="部分成功",
                content=f"歌单下载完成! 成功: {success_count}, 失败: {fail_count}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
        else:
            # 完全失败
            InfoBar.error(
                title="失败",
                content=f"歌单下载失败! 失败: {fail_count}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
    
    def download_error_slot(self, error_message):
        """下载错误槽函数"""
        InfoBar.error(
            title="错误",
            content=f"下载失败: {error_message}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=self
        )
    
    def button_state_slot(self, download_enabled, stop_enabled):
        """按钮状态更新槽函数"""
        self.download_button.setEnabled(download_enabled)
        self.stop_download_button.setEnabled(stop_enabled)
    
    def ncm_progress_slot(self, progress, text):
        """NCM转换进度更新槽函数"""
        self.ncm_progress_bar.setValue(progress)
        self.ncm_progress_label.setText(text)
    
    def ncm_complete_slot(self, success_count, fail_count):
        """NCM转换完成槽函数"""
        if fail_count == 0:
            # 完全成功
            InfoBar.success(
                title="成功",
                content=f"NCM转换完成! 成功: {success_count}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
        elif success_count > 0:
            # 部分成功
            InfoBar.warning(
                title="部分成功",
                content=f"NCM转换完成! 成功: {success_count}, 失败: {fail_count}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
        else:
            # 完全失败
            InfoBar.error(
                title="失败",
                content=f"NCM转换失败! 失败: {fail_count}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self
            )
    
    def ncm_error_slot(self, error_message):
        """NCM转换错误槽函数"""
        InfoBar.error(
            title="错误",
            content=f"NCM转换失败: {error_message}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=self
        )
    
    def ncm_button_state_slot(self, convert_enabled, stop_enabled):
        """NCM转换按钮状态更新槽函数"""
        self.convert_button.setEnabled(convert_enabled)
        self.stop_convert_button.setEnabled(stop_enabled)
    
    def show_startup_message(self):
        """显示启动提示信息"""
        from qfluentwidgets import MessageBox
        title = "使用提示"
        content = "考虑到api不稳定等原因，强烈建议使用网易云客户端下载后使用转换器进行转换而非直接下载\n报告错误请附上点击左下角按钮显示的日志"
        # 使用MessageBox.show()进行非阻塞显示
        msg_box = MessageBox(title, content, self)
        msg_box.setClosableOnMaskClicked(True)
        msg_box.setDraggable(True)
        # 使用show()而非exec()，非阻塞显示
        msg_box.show()

def main():
    """主函数"""
    # 高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # 设置主题为浅色主题
    setTheme(Theme.LIGHT)
    
    app = QApplication(sys.argv)
    
    # 设置应用图标，处理PyInstaller打包后的情况
    icon_path = "./images/icon.ico"
    if hasattr(sys, '_MEIPASS'):
        icon_path = os.path.join(sys._MEIPASS, icon_path)
    app.setWindowIcon(QIcon(icon_path))
    
    window = MusicDownloaderUI()
    # 调整窗口大小
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
