import torch
from transformers import pipeline
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk
import pandas as pd
import datetime
import os
import subprocess
import threading

# 設定
LOG_FILE = "command_log.csv"  # コマンドと結果を保存するCSV
OLLAMA_URL = "http://localhost:11434/api/generate"  # Ollama（ローカルLLM

import torch
torch.cuda.synchronize()  # GPUの同期を強制する

# CSVファイルが存在しない場合、ヘッダーを作成
if not os.path.exists(LOG_FILE):
    df = pd.DataFrame(columns=["Timestamp", "Command", "Output", "Error", "User_Notes", "Summary", "Error_Summary", "Notes_Summary"])
    df.to_csv(LOG_FILE, index=False)

# Tkinterウィンドウ作成
root = tk.Tk()
root.title("Error Result and Research Result")

# CSVを表示する関数
def load_csv():
    df = pd.read_csv(LOG_FILE)

    # 表を更新
    for row in tree.get_children():
        tree.delete(row)
    for i, row in df.iterrows():
        tree.insert("", "end", values=(row["Timestamp"], row["Command"], row["Output"], row["Error"], row["User_Notes"], row["Error_Summary"], row["Notes_Summary"]))

# 実行結果と調査結果を保存する関数
def add_user_notes():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Select Error", "Please Select a line")
        return
    
    # 右側に調査結果を入力
    user_notes = user_notes_entry.get()
    if user_notes.strip() == "":
        messagebox.showwarning("Input Error", "Please input your research result")
        return
    
    index = tree.index(selected_item)
    df = pd.read_csv(LOG_FILE)
    df.at[index, "User_Notes"] = user_notes
    df.to_csv(LOG_FILE, index=False)
    
    load_csv()
    user_notes_entry.delete(0, tk.END)  # 入力フィールドをクリア

# 要約ボタンの処理
def summarize_logs():
    df = pd.read_csv(LOG_FILE)
    
    # データフレームが空でないことを確認
    if df.empty:
        messagebox.showwarning("Empty Log", "The log file is empty.")
        return

    try:
        # Hugging Faceの要約モデルをローカルでロード
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=-1 if torch.cuda.is_available() else -1)

        # 各行のErrorとUser_Notesに対して要約を生成
        for index, row in df.iterrows():
            error_text = row["Error"]
            user_notes = row["User_Notes"]
            
            # Errorの要約
            if pd.notna(error_text) and error_text.strip():
                input_length = len(error_text.split())
                max_length = min(input_length, 100)  # 最大でも100
                max_length = max(max_length, 5)  # 最小でも5
                error_summary = summarizer(error_text, max_length=max_length, min_length=3, do_sample=False)[0]['summary_text']
                df.at[index, "Error_Summary"] = error_summary
            else:
                df.at[index, "Error_Summary"] = "No error to summarize"
            
            # User_Notesの要約
            if pd.notna(user_notes) and user_notes.strip():
                input_length = len(user_notes.split())
                max_length = min(input_length, 100)  # 最大でも100
                max_length = max(max_length, 5)  # 最小でも5
                notes_summary = summarizer(user_notes, max_length=max_length, min_length=3, do_sample=False)[0]['summary_text']
                df.at[index, "Notes_Summary"] = notes_summary
            else:
                df.at[index, "Notes_Summary"] = "No notes to summarize"

        # 要約後の内容をCSVに保存
        df.to_csv(LOG_FILE, index=False)
        
        # 表を更新
        load_csv()

    except Exception as e:
        messagebox.showerror("Error", f"要約中にエラーが発生しました: {e}")


# CSVファイルを開く関数
def open_file():
    global LOG_FILE
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        LOG_FILE = file_path
        load_csv()

# コマンド実行の関数（非同期で実行する）
def execute_command():
    command = command_entry.get()
    if not command.strip():
        messagebox.showwarning("Input Error", "Please enter a command")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # コマンド実行を非同期で行う
    thread = threading.Thread(target=run_command, args=(command, timestamp))
    thread.start()

# 非同期でコマンドを実行し、出力を表示する
def run_command(command, timestamp):
    try:
        # subprocess.Popenを使って非同期にコマンドを実行
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 標準出力とエラーを取得
        output, error = process.communicate()  # communicate()はプロセスが終了するのを待ちます
        
        # 出力とエラーをCSVに追加
        df = pd.read_csv(LOG_FILE)
        new_row = pd.DataFrame([{
            "Timestamp": timestamp,
            "Command": command,
            "Output": output,
            "Error": error,
            "User_Notes": "",
            "Summary": "",
            "Error_Summary": "",
            "Notes_Summary": ""
        }])
        df = pd.concat([df, new_row], ignore_index=True)  # concatを使用
        df.to_csv(LOG_FILE, index=False)

        # 表を更新
        load_csv()

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


# ダブルクリックで詳細を表示する関数
def on_item_double_click(event):
    selected_item = tree.selection()
    if not selected_item:
        return
    
    # 選択された行のデータを取得
    selected_item_id = selected_item[0]
    df = pd.read_csv(LOG_FILE)
    row_index = tree.index(selected_item_id)  # 選択されたアイテムのインデックスを取得
    row = df.iloc[row_index]

    # User NotesまたはSummaryの内容を表示するポップアップを作成
    content = row["User_Notes"] if row["User_Notes"] else row["Summary"]
    
    # contentがNaN（float型）であれば、空文字列に置き換え
    if isinstance(content, float) and pd.isna(content):
        content = "No content available."

    if not content.strip():
        content = "No content available."

    # ポップアップウィンドウを作成
    popup = tk.Toplevel(root)
    popup.title("Detailed View")

    label = tk.Label(popup, text=content, wraplength=400)
    label.pack(padx=10, pady=10)

    button = tk.Button(popup, text="Close", command=popup.destroy)
    button.pack(pady=5)


# GUIが閉じられる際に適切にターミナルを終了させるために、`root.quit()`を追加
def on_close():
    root.quit()  # イベントループを終了
    root.destroy()  # GUIを終了

root.protocol("WM_DELETE_WINDOW", on_close)  # ウィンドウを閉じた時の処理を設定

# Tkinterウィジェット配置
frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

style = ttk.Style()
style.configure("Treeview", font=("MS Gothic", 10)) 

# ツリー表示（CSVの内容を表示）
tree = ttk.Treeview(frame, columns=("Timestamp", "Command", "Output", "Error", "User_Notes", "Error_Summary", "Notes_Summary"), show="headings", height=10)
tree.grid(row=0, column=0, columnspan=5)

tree.heading("Timestamp", text="Timestamp")
tree.heading("Command", text="Command")
tree.heading("Output", text="Output")
tree.heading("Error", text="Error")
tree.heading("User_Notes", text="User Notes")
tree.heading("Error_Summary", text="Error Summary")
tree.heading("Notes_Summary", text="Notes Summary")

# ダブルクリックイベントをバインド
tree.bind("<Double-1>", on_item_double_click)

# 調査結果入力欄
user_notes_label = tk.Label(frame, text="Input your research result:")
user_notes_label.grid(row=1, column=0, padx=10, pady=10)
user_notes_entry = tk.Entry(frame, width=50)
user_notes_entry.grid(row=1, column=1, padx=10, pady=10)

# コマンド入力欄
command_label = tk.Label(frame, text="Enter command to execute:")
command_label.grid(row=2, column=0, padx=10, pady=10)
command_entry = tk.Entry(frame, width=50)
command_entry.grid(row=2, column=1, padx=10, pady=10)

# ボタン
buttons_frame = tk.Frame(root)
buttons_frame.pack(padx=10, pady=10)

open_button = tk.Button(buttons_frame, text="Open CSV", command=open_file)
open_button.grid(row=0, column=0, padx=10)

add_notes_button = tk.Button(buttons_frame, text="Add research result", command=add_user_notes)
add_notes_button.grid(row=0, column=1, padx=10)

summarize_button = tk.Button(buttons_frame, text="Summary", command=summarize_logs)
summarize_button.grid(row=0, column=2, padx=10)

execute_button = tk.Button(buttons_frame, text="Execute Command", command=execute_command)
execute_button.grid(row=0, column=3, padx=10)

# 初期読み込み
load_csv()

# メインループ
root.mainloop()
