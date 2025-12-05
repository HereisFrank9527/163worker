import os
import subprocess
import glob
import sys
from tqdm import tqdm

class NCMConverter:
    def __init__(self, ncmdump_path=None):
        # 尝试从环境变量或默认位置获取ncmdump路径
        if ncmdump_path is None:
            # 检查当前目录下的ncmdump
            self.ncmdump_path = self.find_ncmdump()
        else:
            self.ncmdump_path = ncmdump_path
        
        if not self.ncmdump_path:
            raise FileNotFoundError("ncmdump executable not found. Please provide the path.")
    
    def find_ncmdump(self):
        """查找ncmdump可执行文件"""
        # 检查PyInstaller打包环境
        if hasattr(sys, '_MEIPASS'):
            ncmdump_path = os.path.join(sys._MEIPASS, 'ncmdump.exe')
            if os.path.exists(ncmdump_path):
                return ncmdump_path
            
            # 检查app目录
            app_ncmdump_path = os.path.join(sys._MEIPASS, 'app', 'ncmdump.exe')
            if os.path.exists(app_ncmdump_path):
                return app_ncmdump_path
        
        # 检查当前目录
        if os.path.exists('ncmdump.exe'):
            return os.path.abspath('ncmdump.exe')
        
        # 检查app目录
        app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'ncmdump.exe')
        if os.path.exists(app_path):
            return app_path
        
        # 检查Scripts目录
        scripts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.conda', 'Scripts', 'ncmdump.exe')
        if os.path.exists(scripts_path):
            return scripts_path
        
        # 检查系统PATH
        for path in os.environ['PATH'].split(os.pathsep):
            ncmdump_path = os.path.join(path, 'ncmdump.exe')
            if os.path.exists(ncmdump_path):
                return ncmdump_path
        
        return None
    
    def convert_single_file(self, ncm_file, output_dir=None):
        """转换单个NCM文件"""
        try:
            if output_dir is None:
                output_dir = os.path.dirname(ncm_file)
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 调用ncmdump转换文件
            result = subprocess.run(
                [self.ncmdump_path, ncm_file, '-o', output_dir],
                capture_output=True,
                text=True,
                check=True
            )
            
            # 获取输出文件名
            # ncmdump会自动生成与原文件同名的MP3文件
            mp3_file = os.path.splitext(ncm_file)[0] + '.mp3'
            if os.path.exists(mp3_file):
                return True, mp3_file
            else:
                # 检查输出目录中的文件
                ncm_filename = os.path.basename(ncm_file)
                mp3_filename = os.path.splitext(ncm_filename)[0] + '.mp3'
                mp3_file = os.path.join(output_dir, mp3_filename)
                if os.path.exists(mp3_file):
                    return True, mp3_file
                else:
                    return False, f"Converted file not found: {mp3_file}"
        except subprocess.CalledProcessError as e:
            return False, f"Conversion failed: {e.stderr}"
        except Exception as e:
            return False, str(e)
    
    def batch_convert(self, input_dir, output_dir=None):
        """批量转换NCM文件"""
        # 获取所有NCM文件
        ncm_files = glob.glob(os.path.join(input_dir, '*.ncm'))
        
        if not ncm_files:
            return [{'file': None, 'success': False, 'message': f"No NCM files found in {input_dir}"}]
        
        results = []
        
        for ncm_file in tqdm(ncm_files, desc="Converting NCM files"):
            success, message = self.convert_single_file(ncm_file, output_dir)
            results.append({
                'file': ncm_file,
                'success': success,
                'message': message
            })
        
        return results