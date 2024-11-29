import os
import requests
import pandas as pd

# 创建下载文件夹
def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"文件夹创建成功: {folder_path}")
    else:
        print(f"文件夹已存在: {folder_path}")

# 下载文件的函数
def download_file(url, folder_path, file_name):
    file_path = os.path.join(folder_path, file_name)
    # 检查文件是否已存在
    if os.path.exists(file_path):
        print(f"文件已存在，跳过下载: {file_name}")
        return  # 文件已存在，直接返回

    try:
        response = requests.get(url, stream=True, timeout=10)  # 增加 timeout
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"下载成功: {file_name} 到 {file_path}")
        else:
            print(f"下载失败: {file_name}，状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"下载文件时出错: {file_name}，错误: {str(e)}")

# 批量下载视频和图片
def download_resources(data, target_folder):
    if not data or not isinstance(data, dict):
        print("数据为空或格式不正确，跳过当前任务。")
        return

    if 'data' in data and 'material' in data['data']:
        create_folder(target_folder)
        for material in data['data']['material']:
            if 'list' in material:
                for item in material['list']:
                    mid = item.get('mid', 'unknown_id')
                    url = item.get('url', '')
                    if url:
                        file_extension = url.split('.')[-1]
                        file_name = f"{mid}.{file_extension}"
                        download_file(url, target_folder, file_name)
                    else:
                        print(f"未找到 URL 对于 {mid}")
            else:
                print("'list' key not found in material")
    else:
        print("'material' key not found in data or 'data' key missing")

# 获取数据
def fetch_data(text):
    params = {
        "text": text,
        "type": "video",
        "duration": "0",
        "rankCategory": "",  # 分类不限制
        "plateType": "3",
        "materialSource": "0"
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    }

    cookies = {
        # 替换为你自己的有效 cookies
        "BDUSS": "UVyYUhxUURTMHV3MkNoQXZmbkV-amdrajgteXdCc0xYYlljWU1TMElxZ1F-d3RtRVFBQUFBJCQAAAAAAAAAAAEAAACSAUs~sMLS5V-7w9OwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBy5GUQcuRlN",
        "BDUSS_BFESS": "UVyYUhxUURTMHV3MkNoQXZmbkV-amdrajgteX   dCc0xYYlljWU1TMElxZ1F-d3RtRVFBQUFBJCQAAAAAAAAAAAEAAACSAUs~sMLS5V-7w9OwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBy5GUQcuRlN",
        "BAIDUID": "F822AE8D8B45E45D72E048A998CBD941:FG=1",
        "MCITY": "-218%3A",
        "PSTM": "1731491557",
        "BIDUPSID": "45397B1BE57BDA86ED391ACC1B2CF473",
    }

    try:
        response = requests.get(
            url="https://aigc.baidu.com/aigc/saas/pc/v1/assist/searchList",
            headers=headers,
            cookies=cookies,
            params=params,
            timeout=10  # 增加超时时间
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'data' in data:  # 确保返回结果是字典且包含 'data'
                return data
            else:
                print(f"API 返回的数据格式不正确: {data}")
                return None
        else:
            print(f"接口返回错误状态码: {response.status_code}, 响应内容: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求数据时出错: {text}，错误: {str(e)}")
        return None

# 读取 Excel 文件中的书名列，并返回一个字符串数组
def read_book_titles_from_excel(file_path, sheet_name='Sheet1', column_name='书名'):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
        if column_name in df.columns:
            book_titles = df[column_name].dropna().astype(str).tolist()
            return book_titles
        else:
            print(f"列 '{column_name}' 不存在于 Excel 文件中。")
            return []
    except Exception as e:
        print(f"读取 Excel 文件时出错: {str(e)}")
        return []

# 主函数：遍历书名并执行下载
def main():
    # 定义 Excel 文件路径和下载路径
    file_path = r"D:\桌面\新建 XLSX 工作表.xlsx"
    target_base_folder =r"D:\桌面\1128"  # 自定义的下载文件夹路径

    # 获取书名数组
    book_titles = read_book_titles_from_excel(file_path)

    if not book_titles:
        print("没有书名可供处理，退出程序。")
        return

    # 遍历书名数组并开始下载任务
    for text in book_titles:
        print(f"正在处理: {text}")
        target_folder = os.path.join(target_base_folder, text)
        data = fetch_data(text)

        # 检查 fetch_data 的返回值
        if data is None:
            print(f"未能获取数据，跳过: {text}")
            continue

        download_resources(data, target_folder)

# 执行主函数
if __name__ == "__main__":
    main()