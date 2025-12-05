import requests
import json
import os
import sys
import time

class APIHandler:
    def __init__(self, config_path='config.json'):
        self.config = self.load_config(config_path)
    
    def load_config(self, config_path):
        """加载配置文件"""
        # 处理PyInstaller打包后的情况
        if hasattr(sys, '_MEIPASS'):
            # 在打包环境中，使用_MEIPASS中的配置文件
            config_path = os.path.join(sys._MEIPASS, config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def request_with_retry(self, url, max_retries=3):
        """带重试机制的请求方法"""
        # 获取请求间隔（毫秒）
        request_interval = self.config['apis']['song_download'].get('request_interval', 1000) / 1000  # 转换为秒
        
        for retry in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if retry < max_retries - 1:
                    time.sleep(request_interval)
                else:
                    raise e
    
    def extract_song_id_from_url(self, url):
        """从URL中提取歌曲ID"""
        import re
        # 匹配URL中最后一个&id=或&id=后面的数字
        match = re.search(r'id=([0-9]+)', url)
        if match:
            return match.group(1)
        # 如果没有找到id参数，尝试匹配最后一个数字串
        match = re.search(r'([0-9]+)$', url)
        if match:
            return match.group(1)
        # 如果都没有找到，返回空字符串
        return ''
    
    def get_playlist_songs(self, list_id):
        """获取歌单歌曲列表，支持多个API"""
        # 获取歌单API列表
        playlist_apis = self.config['apis']['playlists']
        
        # 遍历所有API，直到找到可用的API
        for api in playlist_apis:
            try:
                url = api['request_format'].format(list_id=list_id)
                response = self.request_with_retry(url)
                
                if api['response_type'] == 'json':
                    data = response.json()
                    
                    # 根据API类型处理响应
                    if api['name'] == 'Injahow歌单API':
                        # Injahow API直接返回歌曲列表
                        if isinstance(data, list):
                            songs = data
                        else:
                            print(f"{api['name']}响应不是预期的列表格式: {type(data).__name__}")
                            continue
                    else:
                        # 传统网易云API处理
                        if isinstance(data, dict):
                            # 处理不同的API响应结构
                            if 'result' in data and 'tracks' in data['result']:
                                # 标准响应格式，包含result.tracks字段
                                songs = data['result']['tracks']
                            elif 'tracks' in data:
                                # 直接包含tracks字段的响应格式
                                songs = data['tracks']
                            else:
                                # 未知响应格式，尝试下一个API
                                print(f"{api['name']}响应缺少预期的'result.tracks'或'tracks'字段")
                                continue
                        else:
                            print(f"{api['name']}响应不是预期的JSON对象格式")
                            continue
                    
                    # 确保songs是列表
                    if not isinstance(songs, list):
                        print(f"{api['name']}获取的歌曲列表不是预期的列表格式")
                        continue
                    
                    result = []
                    for i, song in enumerate(songs):
                        try:
                            # 提取歌曲信息
                            song_name = song[api['data_paths']['song_name']]
                            artist = song[api['data_paths']['artist']]
                            
                            # 处理歌曲ID，从URL中提取或直接获取
                            song_id_data = song[api['data_paths']['song_id']]
                            if isinstance(song_id_data, str) and 'http' in song_id_data:
                                # 从URL中提取歌曲ID
                                song_id = self.extract_song_id_from_url(song_id_data)
                            else:
                                # 直接使用ID
                                song_id = str(song_id_data)
                            
                            song_info = {
                                'name': song_name,
                                'artist': artist,
                                'id': song_id
                            }
                            result.append(song_info)
                        except Exception as e:
                            # 记录单首歌曲处理失败，但继续处理其他歌曲
                            print(f"{api['name']}处理第{i+1}首歌曲失败: {str(e)}")
                            continue
                    
                    # 如果成功获取到歌曲列表，返回结果
                    if result:
                        print(f"使用{api['name']}成功获取到{len(result)}首歌曲")
                        return result
                    else:
                        print(f"{api['name']}未获取到有效歌曲列表")
            except Exception as e:
                # 记录API请求失败，尝试下一个API
                print(f"{api['name']}请求失败: {str(e)}")
                continue
        
        # 所有API都失败
        raise Exception("所有歌单API都请求失败，请检查网络连接或稍后重试")
    
    def get_song_download_url(self, song_id, quality=None):
        """获取歌曲下载链接"""
        download_api = self.config['apis']['song_download']
        
        if quality is None:
            quality = download_api['default_quality']
        
        url = download_api['request_format'].format(song_id=song_id, quality=quality)
        
        response = self.request_with_retry(url)
        
        if download_api['response_type'] == 'text':
            return response.text.strip()
        elif download_api['response_type'] == 'json':
            data = response.json()
            # 根据实际API响应结构调整
            return data.get('url', '')
        else:
            raise ValueError(f"Unsupported response type: {download_api['response_type']}")
    
    def get_request_interval(self):
        """获取API请求间隔（毫秒）"""
        return self.config['apis']['song_download'].get('request_interval', 1000)
    
    def set_request_interval(self, interval):
        """设置API请求间隔（毫秒）"""
        self.config['apis']['song_download']['request_interval'] = interval
        # 保存配置到文件
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def extract_data(self, data, path):
        """从嵌套数据中提取指定路径的值，添加错误处理"""
        keys = path.split('.')
        result = data
        
        for i, key in enumerate(keys):
            try:
                # 处理列表索引，如 artists[0]
                if '[' in key and ']' in key:
                    list_key, index = key.split('[')
                    index = int(index[:-1])
                    result = result[list_key][index]
                else:
                    result = result[key]
            except (KeyError, IndexError, TypeError) as e:
                # 详细的错误信息，包括当前路径和数据结构
                error_path = '.'.join(keys[:i+1])
                raise KeyError(f"无法从路径 '{error_path}' 提取数据。\n"\
                             f"当前数据结构: {str(result)}\n"\
                             f"完整路径: {path}\n"\
                             f"错误类型: {type(e).__name__}\n"\
                             f"错误信息: {str(e)}") from e
        
        return result
    
    def get_quality_options(self):
        """获取支持的音质选项"""
        return self.config['apis']['song_download']['quality_options']
    
    def get_default_quality(self):
        """获取默认音质"""
        return self.config['apis']['song_download']['default_quality']