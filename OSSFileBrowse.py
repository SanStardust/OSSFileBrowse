import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote
import requests
import xml.etree.ElementTree as ET

class OSSBrowser:
    def __init__(self, master):
        self.master = master
        # 设置窗口标题
        master.title("OSS文件浏览器")

        # 获取屏幕宽度和高度
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        # 计算窗口的宽度和高度
        window_width = 1600
        window_height = 800
        # 计算窗口左上角的坐标
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        # 设置窗口的位置和大小：放到屏幕中间
        master.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 顶部 URL 输入区域：容器
        top_frame = ttk.Frame(master)
        top_frame.pack(pady=10, fill='x')
        # 顶部URL输入区域：输入框和按钮
        self.url_entry = ttk.Entry(top_frame, width=80)
        self.url_entry.pack(side='left', padx=5)
        self.fetch_btn = ttk.Button(top_frame, text="输入 OSS 地址进行分析", command=self.fetch_xml)
        self.fetch_btn.pack(side='left')

        # 底部主体区域：创建可拖动分割容器
        main_paned = ttk.PanedWindow(master, orient='horizontal')
        main_paned.pack(fill='both', expand=True)

        # 左侧文件列表容器
        self.left_frame = ttk.Frame(main_paned)
        main_paned.add(self.left_frame, weight=1)
        # 右侧动态按钮和URL显示容器
        self.right_frame = ttk.Frame(main_paned)
        main_paned.add(self.right_frame, weight=3)
        
        # 创建滚动条容器
        list_container = ttk.Frame(self.left_frame)
        list_container.grid(row=0, column=0, sticky='nsew')
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        # 水平滚动条
        h_scroll = ttk.Scrollbar(list_container, orient='horizontal')
        h_scroll.grid(row=1, column=0, sticky='ew')

        # 左侧文件列表 Listbox
        self.listbox = tk.Listbox(list_container, width=30, xscrollcommand=h_scroll.set)
        self.listbox.grid(row=0, column=0, sticky='nsew')
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)
        h_scroll.config(command=self.listbox.xview)
        self.listbox.bind('<<ListboxSelect>>', self.show_url)  # 为Listbox添加选择事件监听，当用户选择列表项时触发show_url方法

        # 右侧搜索框和搜索按钮
        search_frame = ttk.Frame(self.right_frame)
        search_frame.pack(fill='x', pady=5)
        self.filter_entry = ttk.Entry(search_frame)
        self.filter_entry.pack(side='left', fill='x', expand=True)
        self.confirm_btn = ttk.Button(search_frame, text="搜索", command=self.handle_search)
        self.confirm_btn.pack(side='left', padx=5)

        # 右侧动态按钮和 URL 显示
        self.right_frame = ttk.Frame(self.right_frame)
        self.right_frame.pack(side='left', fill='both', expand=True, padx=5)
        self.button_frame = ttk.Frame(self.right_frame)
        self.button_frame.pack(fill='x', pady=5)
        self.url_text = tk.Text(self.right_frame, wrap=tk.WORD)
        self.url_text.pack(fill='both', expand=True)
        
        # 添加复制按钮
        self.copy_btn = ttk.Button(self.right_frame, text="复制当前所有 URL", command=self.copy_urls)
        self.copy_btn.pack(side='bottom', pady=5)

        # 初始化变量
        self.keys = []
        self.base_url = ""
        self.current_extension = None

    # 当用户输入 OSS URL 然后点击确定后执行
    def fetch_xml(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("错误", "请输入有效的URL")
            return

        try:
            response = requests.get(url)
            response.raise_for_status()
            resp = ET.fromstring(response.content)
            self.base_url = url.split('?')[0]
            self.base_url = self.base_url if self.base_url[-1] == '/' else self.base_url + '/'
            
            # 解析XML获取Keys并提取后缀
            self.keys = [key.text for key in resp.findall('.//{*}Contents/{*}Key')]
            # 提取唯一文件后缀
            extensions = {key.split('.')[-1].lower() for key in self.keys if key is not None and '.' in key}
            self.update_buttons(extensions)
            self.update_listbox()
            
        except requests.RequestException as e:
            messagebox.showerror("请求错误", f"网络请求失败: {str(e)}")
        except ET.ParseError as e:
            messagebox.showerror("解析错误", f"XML解析失败: {str(e)}")

    def update_buttons(self, extensions):
        # 清空现有按钮
        for widget in self.button_frame.winfo_children():
            widget.destroy()

        # 获取容器实际宽度
        self.button_frame.update_idletasks()
        frame_width = self.button_frame.winfo_width()
        available_width = frame_width - 20  # 留出边距

        # 初始化布局参数
        row = 0
        col = 0
        current_width = 0
        max_row_height = 0

        # 生成并排列按钮
        for ext in sorted(extensions):
            btn = ttk.Button(self.button_frame, text=ext.upper(), width=10,  # 设置按钮宽度
                           command=lambda e=ext: self.filter_by_extension(e))
            btn_width = btn.winfo_reqwidth() + 10  # 包含padding
            
            # 检查是否需要换行
            if current_width + btn_width > available_width and col > 0:
                row += 1
                col = 0
                current_width = 0
                max_row_height = 0
            
            # 放置按钮并更新布局参数
            btn.grid(row=row, column=col, padx=5, pady=2, sticky='w')
            current_width += btn_width
            max_row_height = max(max_row_height, btn.winfo_reqheight())
            col += 1

        # 更新容器高度
        total_height = (row + 1) * (max_row_height + 8)  # 包含行间距
        self.button_frame.config(height=total_height)
        self.button_frame.grid_propagate(False)

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        for key in self.keys:
            # 检查 key 是否为 None，如果是则跳过，否则插入到列表框中
            if key is not None:
                self.listbox.insert(tk.END, key)

    def handle_search(self, event=None):
        self.current_extension = None
        filter_text = self.filter_entry.get().lower()
        filtered = self.apply_filter(filter_text)
        self.show_url(filtered)

    def apply_filter(self,filter_text):
        filtered = [k for k in self.keys if k is not None and filter_text in k.lower()]
        return filtered

    def filter_by_extension(self, extension):
        filtered = self.apply_filter(extension)
        self.url_text.delete(1.0, tk.END)
        full_urls = '\n'.join([f"{self.base_url}{key}" for key in filtered])
        self.url_text.insert(tk.END, full_urls)

    def show_url(self, filtered):
        self.url_text.delete(1.0, tk.END)
        full_urls = '\n'.join([f"{self.base_url}{key}" for key in filtered])
        self.url_text.insert(tk.END, full_urls)

    def copy_urls(self):
        if not self.base_url:
            messagebox.showerror("错误", "请先获取OSS地址")
            return
        
        urls = self.url_text.get(1.0, tk.END).split('\n')
        encoded_urls = []
        for url in urls:
            if url.strip():
                encoded_key = quote(url.replace(self.base_url, '').lstrip('/'))
                encoded_urls.append(f"{self.base_url}{encoded_key}")
        
        result = '\n'.join(encoded_urls)
        self.master.clipboard_clear()
        self.master.clipboard_append(result)
        messagebox.showinfo("成功", "已复制{0}个URL到剪贴板".format(len(encoded_urls)))


if __name__ == "__main__":
    root = tk.Tk()
    app = OSSBrowser(root)
    root.mainloop()
