import os
import readline
import datetime
import subprocess
import torch
from transformers import pipeline
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk
import pandas as pd
import datetime
import os
import subprocess
import threading


# CSVファイルを開く関数
def open_file():
    global LOG_FILE
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        LOG_FILE = file_path
        load_csv()


# CSVを表示する関数
def load_csv():
    df = pd.read_csv(LOG_FILE)

    # 表を更新
    for row in tree.get_children():
        tree.delete(row)
    for i, row in df.iterrows():
        tree.insert(
            "",
            "end",
            values=(
                row["Timestamp"],
                row["Command"],
                row["Output"],
                row["Error"],
                row["User_Notes"],
                row["Error_Summary"],
                row["Notes_Summary"],
            ),
        )


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


if __name__ == "__main__":
    LOG_FILE = "command_log.csv"

    # CSVファイルが存在しない場合、ヘッダーを作成
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(
            columns=[
                "Timestamp",
                "Command",
                "Output",
                "Error",
                "User_Notes",
                "Summary",
                "Error_Summary",
                "Notes_Summary",
            ]
        )
        df.to_csv(LOG_FILE, index=False)

    # Tkinterウィンドウ作成
    root = tk.Tk()
    root.title("Error Result and Research Result")

    root.protocol("WM_DELETE_WINDOW", on_close)  # ウィンドウを閉じた時の処理を設定

    # Tkinterウィジェット配置
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)

    style = ttk.Style()
    style.configure("Treeview", font=("MS Gothic", 10))

    # ツリー表示（CSVの内容を表示）
    tree = ttk.Treeview(
        frame,
        columns=(
            "Timestamp",
            "Command",
            "Output",
            "Error",
            "User_Notes",
            "Error_Summary",
            "Notes_Summary",
        ),
        show="headings",
        height=10,
    )
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

    add_notes_button = tk.Button(
        buttons_frame, text="Add research result", command=add_user_notes
    )
    add_notes_button.grid(row=0, column=1, padx=10)

    summarize_button = tk.Button(buttons_frame, text="Summary", command=summarize_logs)
    summarize_button.grid(row=0, column=2, padx=10)

    execute_button = tk.Button(
        buttons_frame, text="Execute Command", command=execute_command
    )
    execute_button.grid(row=0, column=3, padx=10)

    # 初期読み込み
    load_csv()

    while True:

        # メインループ
        root.mainloop()

        try:
            command = input("$ ")
            if command.lower() in ["exit", "quit"]:
                break

            # ログ記録（コマンド）
            # with open(LOG_FILE, "a") as f:
            #     f.write(f"{datetime.datetime.now()} Command: {command}\n")

            # コマンド実行
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # 出力とエラーを記録
            # if result.stdout:
            #     with open(history_file, "a") as f:
            #         f.write(f"{datetime.datetime.now()} Output: {result.stdout}\n")

            # if result.stderr:
            #     with open(history_file, "a") as f:
            #         f.write(f"{datetime.datetime.now()} Error: {result.stderr}\n")


            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame(
                [
                    {
                        "Timestamp": timestamp,
                        "Command": command,
                        "Output": result.stdout,
                        "Error": result.stderr,
                        "User_Notes": "",
                        "Summary": "",
                        "Error_Summary": "",
                        "Notes_Summary": "",
                    }
                ]
            )

        except KeyboardInterrupt:
            print("\nExiting...")
            break
