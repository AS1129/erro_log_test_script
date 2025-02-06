import os
import datetime
import subprocess
import torch
from transformers import pipeline
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import threading

stop_event = threading.Event()

def run_command(command, timestamp):
    try:
        # subprocess.Popenを使って非同期にコマンドを実行
        process = subprocess.Popen(
            command.split(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 標準出力とエラーを取得
        output, error = (
            process.communicate()
        )  # communicate()はプロセスが終了するのを待ちます

        # 出力とエラーをCSVに追加
        df = pd.read_csv(LOG_FILE)
        new_row = pd.DataFrame(
            [
                {
                    "Timestamp": timestamp,
                    "Command": command,
                    "Output": output,
                    "Error": error,
                    "User_Notes": "",
                    "Summary": "",
                    "Error_Summary": "",
                    "Notes_Summary": "",
                }
            ]
        )
        df = pd.concat([df, new_row], ignore_index=True)  # concatを使用
        df.to_csv(LOG_FILE, index=False)

        # 表を更新
        load_csv()

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


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


# 要約ボタンの処理
def summarize_logs():
    df = pd.read_csv(LOG_FILE)

    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Select Error", "Please Select a line")
        return

    # データフレームが空でないことを確認
    if df.empty:
        messagebox.showwarning("Empty Log", "The log file is empty.")
        return

    try:
        # Hugging Faceの要約モデルをローカルでロード
        summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=-1 if torch.cuda.is_available() else -1,
        )

        # 各行のErrorとUser_Notesに対して要約を生成
        index = tree.index(selected_item)

        error_text = df.at[index, "Error"]
        user_notes = df.at[index, "User_Notes"]

        # Errorの要約
        if pd.notna(error_text) and error_text.strip():
            input_length = len(error_text.split())
            max_length = min(input_length, 100)  # 最大でも100
            max_length = max(max_length, 5)  # 最小でも5
            error_summary = summarizer(
                error_text, max_length=max_length, min_length=3, do_sample=False
            )[0]["summary_text"]
            df.at[index, "Error_Summary"] = error_summary
        else:
            df.at[index, "Error_Summary"] = "No error to summarize"

        # User_Notesの要約
        if pd.notna(user_notes) and user_notes.strip():
            input_length = len(user_notes.split())
            max_length = min(input_length, 100)  # 最大でも100
            max_length = max(max_length, 5)  # 最小でも5
            notes_summary = summarizer(
                user_notes, max_length=max_length, min_length=3, do_sample=False
            )[0]["summary_text"]
            df.at[index, "Notes_Summary"] = notes_summary
        else:
            df.at[index, "Notes_Summary"] = "No notes to summarize"

        # 要約後の内容をCSVに保存
        df.to_csv(LOG_FILE, index=False)

        # 表を更新
        load_csv()

    except Exception as e:
        messagebox.showerror("Error", f"要約中にエラーが発生しました: {e}")


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

    # ポップアップウィンドウを作成
    popup = tk.Toplevel(root)
    popup.title("Detailed View")

    # ラジオボタンを追加して選べるようにする
    content_var = tk.StringVar(value="User_Notes")

    def update_label():
        content = {
            "User_Notes": row["User_Notes"],
            "Error": row["Error"],
            "Error_Summary": row["Error_Summary"],
            "Notes_Summary": row["Notes_Summary"],
        }.get(content_var.get(), "No content available.")

        if isinstance(content, float) and pd.isna(content):
            content = "No content available."
        label.config(text=content)

    label = tk.Label(popup, text="", wraplength=400)
    label.pack(padx=10, pady=10)

    radio_frame = tk.Frame(popup)
    radio_frame.pack(padx=10, pady=10)

    tk.Radiobutton(
        radio_frame,
        text="User Notes",
        variable=content_var,
        value="User_Notes",
        command=update_label,
    ).pack(side=tk.LEFT)
    tk.Radiobutton(
        radio_frame,
        text="Error",
        variable=content_var,
        value="Error",
        command=update_label,
    ).pack(side=tk.LEFT)
    tk.Radiobutton(
        radio_frame,
        text="Error Summary",
        variable=content_var,
        value="Error_Summary",
        command=update_label,
    ).pack(side=tk.LEFT)
    tk.Radiobutton(
        radio_frame,
        text="Notes Summary",
        variable=content_var,
        value="Notes_Summary",
        command=update_label,
    ).pack(side=tk.LEFT)

    # 初期状態で内容を更新
    update_label()

    button = tk.Button(popup, text="Close", command=popup.destroy)
    button.pack(pady=5)


# GUIの終了処理
def on_close():
    stop_event.set()  # スレッド終了イベントをセット
    root.quit()  # イベントループを終了
    root.destroy()  # GUIを終了
    # os._exit(0)  # ターミナルの終了も強制


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


def command_loop(log_file):
    df = pd.read_csv(LOG_FILE)
    while not stop_event.is_set():
        try:
            command = input("$ ")
            if command.lower() in ["exit", "quit"]:
                break

            # コマンド実行
            result = subprocess.run(
                command.split(),
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # 出力とエラーを記録
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # print(result.stderr)

            # データフレーム作成
            new_row = pd.DataFrame(
                [
                    {
                        "Timestamp": timestamp,
                        "Command": command,
                        "Output": result.stdout,
                        "Error": result.stderr.replace(os.path.expanduser("~"), "***"),
                        "User_Notes": "",
                        "Summary": "",
                        "Error_Summary": "",
                        "Notes_Summary": "",
                    }
                ]
            )

            # 例：新しい行を表示（もしくはファイルに保存）
            df = pd.concat([df, new_row], ignore_index=True)  # concatを使用
            df.to_csv(LOG_FILE, index=False)

            # 表を更新
            load_csv()

        except KeyboardInterrupt:
            print("\nExiting...")
            break


if __name__ == "__main__":
    LOG_FILE = "command_log.csv"
    os.chmod(LOG_FILE, 0o600)  # 読み書き可能だが他のユーザーには見えない

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

    thread = threading.Thread(target=command_loop, args=(LOG_FILE,))
    thread.start()

    # メインGUIループ（これが常に動作）
    root.mainloop()
