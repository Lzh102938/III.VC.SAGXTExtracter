import os
import errno
import gta.gxt
import tkinter as tk
import tkinter.font as tkFont
from tkinter import scrolledtext
from tkinter import filedialog
from tkinter import messagebox
import sys

def createOutputDir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def readOutTable(gxt, reader, name, outDirName):
    output_file_path = os.path.join(outDirName, name + '.txt')

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(f'[{name}]\n')  # 在文件顶部添加原始文件名

        for text in reader.parseTKeyTDat(gxt):
            f.write(text[0] + '=' + text[1] + '\n')

def gxt_processing(file_path, outDirName):
    gxt_name = os.path.splitext(os.path.basename(file_path))[0]
    gxt_dir = os.path.join(os.path.dirname(file_path), gxt_name)
    createOutputDir(gxt_dir)
    
    with open(file_path, 'rb') as gxt:
        gxtversion = gta.gxt.getVersion(gxt)

        if not gxtversion:
            print('未知GXT版本！', file=sys.stderr)
            return

        print("成功识别GXT版本：{}".format(gxtversion))

        gxtReader = gta.gxt.getReader(gxtversion)

        Tables = []
        if gxtReader.hasTables():
            Tables = gxtReader.parseTables(gxt)

        for t in Tables:
            table_name = t[0]
            readOutTable(gxt, gxtReader, table_name, gxt_dir)

        # Collect the text content
        text_content = []
        for t in Tables:
            table_name = t[0]
            table_file_path = os.path.join(gxt_dir, table_name + '.txt')
            with open(table_file_path, 'r', encoding='utf-8') as table_file:
                text_content.append(table_file.read())

        # Save the collected text to a same-named .txt file
        output_txt_path = os.path.join(os.path.dirname(file_path), outDirName + '.txt')
        with open(output_txt_path, 'w', encoding='utf-8') as output_file:
            output_file.write('\n\n'.join(text_content))

    return text_content

def open_gxt_path(file_path):
    if os.path.isfile(file_path) and file_path.lower().endswith(".gxt"):
        outDirName = os.path.splitext(os.path.basename(file_path))[0]
        text_content = gxt_processing(file_path, outDirName)
        output_text.delete(1.0, tk.END)  # 清空文本框
        output_text.insert(tk.END, '\n\n'.join(text_content))
        root.title(f"GXT 文本查看器 - {outDirName}.gxt")
    else:
        messagebox.showerror("错误", "无效的 GXT 文件路径")

def select_gxt_file():
    file_path = filedialog.askopenfilename(filetypes=[("GXT 文件", "*.gxt")])
    if file_path:
        gxt_path_entry.delete(0, tk.END)  # 清空输入框
        gxt_path_entry.insert(0, file_path)
        open_gxt_path(file_path)

def open_gxt_from_input():
    file_path = gxt_path_entry.get()
    open_gxt_path(file_path)

def open_about_window():
    about_window = tk.Toplevel(root)
    about_window.title("关于")
    about_window.geometry("640x480")  # Set the window size to 640x480

    about_text = tk.Text(about_window, wrap=tk.WORD, font=("微软雅黑", 16))
    about_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    about_text.tag_config("title", font=("微软雅黑", 16, "bold"))
    about_text.tag_config("content", font=("微软雅黑", 15))
    about_text.tag_config("warning", font=("微软雅黑", 17, "bold"), foreground="red")
    about_text.tag_config("important", font=("微软雅黑", 16), foreground="red")
    about_text.tag_config("ver", font=("微软雅黑", 15), foreground="green")

    about_text.insert(tk.END, "版本号：Release V1.1\n\n", "ver")
    about_text.insert(tk.END, "☆☆☆☆★★★★★★☆☆☆☆\n", "important")
    about_text.insert(tk.END, "本软件由Lzh10_慕黑创作\n借用GitHub上开源GXT解析代码\n", "content")
    about_text.insert(tk.END, "温馨提示：仅支持VC和SA版本GXT解析\n\n", "important")    
    about_text.insert(tk.END, "此工具完全免费且开源，若通过付费渠道获取均为盗版！\n", "content")
    about_text.insert(tk.END, "若您是盗版受害者，联系QQ：", "content")
    about_text.insert(tk.END, "235810290\n\n", "title")
    about_text.insert(tk.END, "免责声明：使用本软件导致的版权问题概不负责！\n\n", "warning")
    about_text.insert(tk.END, "开源&检测更新：\n", "content")
    about_text.insert(tk.END, "https://github.com/Lzh102938/VC.SAGXTExtracter\n\n", "title")    
    about_text.insert(tk.END, "☆☆☆☆★★★★★★☆☆☆☆\n\n", "important")
    about_text.insert(tk.END, "更新日志：\nV1.1添加了TABLE分文本功能", "content")

    # Add a scroll bar
    scroll_bar = tk.Scrollbar(about_text)
    scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_bar.config(command=about_text.yview)
    about_text.config(yscrollcommand=scroll_bar.set)

    about_text.config(state=tk.DISABLED)

if len(sys.argv) > 1:
    gxt_to_open = sys.argv[1]
    open_gxt_path(gxt_to_open)
else:
    root = tk.Tk()
    root.title("GXT 文本查看器")

    gxt_path_label = tk.Label(root, text="GXT 路径：")
    gxt_path_label.pack(padx=10, pady=5, anchor="w")

    gxt_path_entry = tk.Entry(root, width=50)
    gxt_path_entry.pack(padx=10, pady=0)

    select_button = tk.Button(root, text="选择 GXT 文件", command=select_gxt_file)
    select_button.pack(padx=10, pady=5)

    open_button = tk.Button(root, text="打开", command=open_gxt_from_input)
    open_button.pack(padx=10, pady=5)

    about_button = tk.Button(root, text="关于", command=open_about_window)
    about_button.pack(padx=10, pady=5)

    # 创建自定义字体
    font_style = tkFont.Font(family="微软雅黑", size=12)  # 可根据需要调整字体和大小

    # 创建输出文本框
    output_text = scrolledtext.ScrolledText(root, wrap=tk.NONE, width=80, height=20, font=font_style)
    output_text.pack(padx=10, pady=5)

    root.mainloop()
