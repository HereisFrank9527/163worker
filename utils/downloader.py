import requests
import os
import time

class SongDownloader:
    def __init__(self, api_handler):
        self.api_handler = api_handler
        # 获取API请求间隔（毫秒）
        self.request_interval = self.api_handler.config['apis']['song_download'].get('request_interval', 1000) / 1000  # 转换为秒
        self.last_request_time = 0
    
    def download_song(self, song_info, save_path, quality=None, speed_limit=0, skip_existing=False, filename_format=0):
        """下载单个歌曲，支持失败重试、跳过已存在文件和自定义文件名格式"""
        max_retries = 3
        retry_delay = 3  # 秒
        
        # 根据格式构建文件名
        if filename_format == 0:
            # 歌名 - 作者
            filename = f"{song_info['name']} - {song_info['artist']}.mp3"
        else:
            # 作者 - 歌名
            filename = f"{song_info['artist']} - {song_info['name']}.mp3"
        # 替换非法字符
        filename = self.sanitize_filename(filename)
        filepath = os.path.join(save_path, filename)
        
        # 检查文件是否已存在，如果是则跳过
        if skip_existing and os.path.exists(filepath):
            return True, f"已跳过: {filename}（文件已存在）"
        
        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        
        for attempt in range(max_retries):
            try:
                # 控制API请求间隔
                current_time = time.time()
                elapsed = current_time - self.last_request_time
                if elapsed < self.request_interval:
                    time.sleep(self.request_interval - elapsed)
                
                # 获取下载链接
                download_url = self.api_handler.get_song_download_url(song_info['id'], quality)
                self.last_request_time = time.time()
                
                if not download_url:
                    raise ValueError(f"Failed to get download URL for song: {song_info['name']}")
                
                # 下载歌曲
                self.download_file(download_url, filepath, speed_limit)
                
                return True, filepath
            except Exception as e:
                if attempt < max_retries - 1:
                    # 等待重试
                    time.sleep(retry_delay)
                    print(f"Download attempt {attempt+1} failed for song {song_info['name']}, retrying in {retry_delay} seconds...")
                else:
                    # 最后一次尝试失败
                    return False, f"Failed after {max_retries} attempts: {str(e)}"
    
    def download_file(self, url, filepath, speed_limit=0):
        """下载文件，支持限速"""
        chunk_size = 1024
        
        # 添加超时设置，防止网络请求无限期等待
        with requests.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as file:
                start_time = time.time()
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        # 限速处理
                        if speed_limit > 0:
                            elapsed = time.time() - start_time
                            expected_time = downloaded / (speed_limit * 1024)
                            if elapsed < expected_time:
                                time.sleep(expected_time - elapsed)
    
    def download_playlist(self, list_id, save_path, quality=None, speed_limit=0):
        """下载整个歌单"""
        try:
            # 获取歌单歌曲列表
            songs = self.api_handler.get_playlist_songs(list_id)
            
            if not songs:
                raise ValueError(f"No songs found in playlist: {list_id}")
            
            # 确保保存目录存在
            os.makedirs(save_path, exist_ok=True)
            
            results = []
            for song in songs:
                success, message = self.download_song(song, save_path, quality, speed_limit)
                results.append({
                    'song': song,
                    'success': success,
                    'message': message
                })
            
            return results
        except Exception as e:
            return [{'song': None, 'success': False, 'message': str(e)}]
    
    def sanitize_filename(self, filename):
        """替换文件名中的非法字符"""
        illegal_chars = '<>:/\\|?*"'
            
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        return filename