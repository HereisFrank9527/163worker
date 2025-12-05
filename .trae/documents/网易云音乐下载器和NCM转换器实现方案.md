# 网易云音乐下载器和NCM转换器实现方案

## 项目概述

实现一个具有可视化UI的应用程序，包含两大功能：

1. 通过API下载网易云歌单中的音乐，支持下载速度控制
2. 将本地NCM文件批量转换为MP3格式

## 设计原则

* 代码与数据分离，所有API配置存储在JSON文件中

* 模块化设计，便于维护和扩展

* 友好的可视化UI

* 支持多种音质选择

* 支持下载速度控制

## 项目结构

```
163downloader/
├── main.py              # 主程序入口，UI整合
├── config.json          # API配置文件
├── utils/
│   ├── api.py           # API请求处理
│   ├── downloader.py    # 歌曲下载功能
│   ├── ncm_converter.py # NCM转换功能
│   └── ui.py            # UI组件
└── requirements.txt     # 依赖库列表
```

## JSON配置文件设计

```json
{
  "apis": {
    "playlist": {
      "name": "网易云歌单API",
      "request_format": "https://music.163.com/api/playlist/detail?id={list_id}",
      "response_type": "json",
      "data_paths": {
        "songs": "result.tracks",
        "song_name": "name",
        "artist": "artists[0].name",
        "song_id": "id"
      }
    },
    "song_download": {
      "name": "网易云歌曲直链API",
      "request_format": "https://www.byfuns.top/api/1/?id={song_id}&level={quality}",
      "response_type": "text",
      "supports_quality": true,
      "quality_options": [
        "standard",
        "higher",
        "exhigh",
        "lossless",
        "hire"
      ],
      "default_quality": "standard"
    }
  },
  "download": {
    "default_speed_limit": 0,  # 0表示无限制
    "default_save_path": "./downloads"
  }
}
```

## 核心功能模块

### 1. API请求模块 (api.py)

* 读取config.json配置

* 动态构建API请求

* 解析API响应数据

* 支持不同类型的API响应（JSON/文本）

### 2. 歌曲下载模块 (downloader.py)

* 获取歌单信息

* 解析歌曲列表

* 获取歌曲直链

* 支持限速下载

* 下载进度显示

* 错误处理

### 3. NCM转换模块 (ncm\_converter.py)

* 批量读取NCM文件

* 使用现成库转换为MP3

* 转换进度显示

* 错误处理

### 4. 可视化UI模块 (ui.py)

* 主窗口设计

* 歌单下载功能区

  * 歌单ID输入

  * 音质选择

  * 下载速度设置

  * 保存路径选择

  * 开始下载按钮

  * 下载进度显示

* NCM转换功能区

  * 源文件夹选择

  * 目标文件夹选择

  * 开始转换按钮

  * 转换进度显示

* 日志显示区

## 技术栈

* **Python 3.x**

* **requests** - HTTP请求

* **tkinter** - 可视化UI（内置库）

* **mutagen** - 音频元数据处理

* **ncmdump** - NCM文件转换

* **tqdm** - 进度显示

## 实现步骤

1. 创建项目结构和配置文件
2. 实现API请求模块
3. 实现歌曲下载模块
4. 实现NCM转换模块
5. 实现可视化UI
6. 整合所有模块
7. 测试和优化

## 预期效果

* 用户可以通过UI输入歌单ID，选择音质和下载速度，下载歌单中的所有歌曲

* 用户可以选择本地NCM文件所在文件夹，批量转换为MP3格式

* 所有操作都有清晰的进度显示

* 支持错误处理和日志记录

* 代码结构清晰，便于维护和扩展

## 扩展性考虑

* 支持添加更多的API提供商

* 支持更多的音频格式转换

* 支持更多的下载速度控制选项

* 支持歌曲搜索功能

* 支持歌词下载功能

