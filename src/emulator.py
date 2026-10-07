import argparse
import csv
import os
import tkinter as tk
import zipfile
from datetime import datetime

DEFAULT_TAIL_LINES = 10
DELAY_SCRIPT_START = 500
DELAY_SCRIPT_STEP = 800
MAX_EXIT_ARGS = 1
MAX_CD_ARGS = 1
MAX_PWD_ARGS = 0
MAX_UNAME_ARGS = 1


class TerminalEmulator:
    """Главный класс графического эмулятора UNIX-оболочки.

    Выполняет все операции VFS исключительно в оперативной памяти.
    """

    def __init__(self, root, vfs_path, log_path, script_path):
        """Инициализирует графический интерфейс и VFS."""
        self.root = root
        self.vfs_path = vfs_path
        self.log_path = log_path
        self.script_path = script_path

        vfs_name = os.path.basename(vfs_path) if vfs_path else "None"
        self.root.title(f"VFS: {vfs_name}")
        self.root.geometry("750x550")

        self.current_path = "/"
        self.script_commands = []
        self.is_running_script = False
        self.vfs_files = {}

        self.terminal = tk.Text(
            root,
            bg="#1c1c1c",
            fg="#00ff00",
            insertbackground="#00ff00",
            font=("Courier", 12),
            padx=10,
            pady=10,
        )
        self.terminal.pack(expand=True, fill=tk.BOTH)

        self.terminal.bind("<Key>", self.handle_keypress)
        self.terminal.bind("<Button-1>", lambda e: self.terminal.focus_set())
        self.terminal.focus_set()


        self.print_text("Welcome to UNIX Shell Emulator (Final Stage)\n")
        self.load_vfs()
        self.insert_prompt()

        if self.script_path:
            self.load_and_run_script()

    def print_text(self, text):
        """Печатает текст в поле графического терминала."""
        self.terminal.insert(tk.END, text)
        self.terminal.see(tk.END)

    def insert_prompt(self):
        """Выводит строку приглашения командной строки UNIX."""
        prompt = f"user@emulator:{self.current_path}$ "
        self.print_text(prompt)
        self.input_start_index = self.terminal.index(tk.INSERT)

    def log_event(self, command_str, error_msg=""):
        """Записывает событие вызова команды в лог-файл формата CSV."""
        if not self.log_path:
            return
        file_exists = os.path.exists(self.log_path)
        try:
            with open(
                self.log_path, mode="a", newline="", encoding="utf-8"
            ) as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Command", "Error Message"])
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([time_str, command_str, error_msg])
        except Exception:
            pass
    def handle_keypress(self, event):
        """Обрабатывает нажатия клавиш пользователем, защищая промпт."""
        if event.keysym == "Return":
            start_idx = self.input_start_index
            user_input = self.terminal.get(start_idx, tk.END).strip()
            self.print_text("\n")
            if user_input:
                self.execute_command(user_input)
            else:
                self.insert_prompt()
            return "break"
        elif event.keysym == "BackSpace":
            if self.terminal.index(tk.INSERT) == self.input_start_index:
                return "break"
        self.terminal.mark_set(tk.INSERT, tk.END)


    def load_vfs(self):
        """Загружает дерево VFS из ZIP-архива в оперативную память."""
        if not self.vfs_path or not os.path.exists(self.vfs_path):
            self.print_text("VFS Error: Archive not found.\n\n")
            return
        if not zipfile.is_zipfile(self.vfs_path):
            self.print_text("VFS Error: Invalid format.\n\n")
            return

        try:
            self.vfs_files["/"] = {"type": "dir", "owner": "root"}
            with zipfile.ZipFile(self.vfs_path, "r") as archive:
                for name in archive.namelist():
                    self._process_zip_entry(archive, name)
            self.print_text("VFS successfully loaded into memory.\n\n")
        except Exception as e:
            self.print_text(f"VFS Error: {e}\n\n")

    def _process_zip_entry(self, archive, name):
        """Вспомогательный метод для обработки одной записи в архиве."""
        norm = name.replace("\\", "/")
        parts = [p for p in norm.split("/") if p]
        curr = ""
        for i, part in enumerate(parts):
            curr = curr + "/" + part
            if curr in self.vfs_files:
                continue
            if i == len(parts) - 1 and not name.endswith("/"):
                try:
                    data = archive.read(name)
                    content = data.decode("utf-8", errors="replace")
                except Exception:
                    content = "[Binary Data]"
                self.vfs_files[curr] = {
                    "type": "file",
                    "content": content,
                    "owner": "root",
                }
            else:
                self.vfs_files[curr] = {"type": "dir", "owner": "root"}

    def _resolve_path(self, target_path):
        """Преобразует относительный путь в абсолютный виртуальный путь."""
        if not target_path:
            return self.current_path
        if target_path.startswith("/"):
            combined = target_path
        else:
            if self.current_path == "/":
                combined = "/" + target_path
            else:
                combined = self.current_path + "/" + target_path

        resolved_parts = []
        for part in combined.split("/"):
            if not part or part == ".":
                continue
            if part == "..":
                if resolved_parts:
                    resolved_parts.pop()
            else:
                resolved_parts.append(part)
        return "/" + "/".join(resolved_parts)

    def execute_command(self, input_string, from_script=False):
        """Парсит строку ввода и перенаправляет её в нужный метод подкоманды."""
        parts = input_string.split()
        if not parts:
            if not from_script:
                self.insert_prompt()
            return ""

        cmd = parts[0]
        args = parts[1:]
        err = ""

        if cmd == "exit":
            err = self._cmd_exit(args, input_string)
        elif cmd == "pwd":
            err = self._cmd_pwd(args)
        elif cmd == "uname":
            err = self._cmd_uname(args)
        elif cmd == "cd":
            err = self._cmd_cd(args)
        elif cmd == "ls":
            err = self._cmd_ls(args)
        elif cmd == "tail":
            err = self._cmd_tail(args)
        elif cmd == "mkdir":
            err = self._cmd_mkdir(args)
        elif cmd == "chown":
            err = self._cmd_chown(args)
        else:
            err = f"sh: command not found: {cmd}"
            self.print_text(f"{err}\n")

        if cmd != "exit" or err:
            self.log_event(input_string, err)
            if not from_script:
                self.insert_prompt()
        return err
    def _cmd_exit(self, args, input_string):
        """Выполняет команду завершения работы оболочки."""
        if len(args) > MAX_EXIT_ARGS:
            err = "sh: exit: too many arguments"
            self.print_text(f"{err}\n")
            return err
        if len(args) == MAX_EXIT_ARGS and not args[0].isdigit():
            err = f"sh: exit: {args[0]}: numeric argument required"
            self.print_text(f"{err}\n")
            self.log_event(input_string, err)
            self.root.quit()
            return err
        self.log_event(input_string, "")
        self.root.quit()
        return ""

    def _cmd_pwd(self, args):
        """Выводит текущую рабочую директорию VFS."""
        if len(args) > MAX_PWD_ARGS:
            err = "pwd: too many arguments"
            self.print_text(f"{err}\n")
            return err
        self.print_text(f"{self.current_path}\n")
        return ""

    def _cmd_uname(self, args):
        """Выводит информацию о виртуальной операционной системе."""
        if len(args) > MAX_UNAME_ARGS or (args and args[0] not in ["-a", "-r"]):
            err = "uname: extra operand"
            self.print_text(f"{err}\n")
            return err
        if args and args[0] == "-a":
            self.print_text("PythonVFSOS 1.0.0 Stage-5 x86_64 GNU/Linux\n")
        elif args and args[0] == "-r":
            self.print_text("1.0.0-stage5\n")
        else:
            self.print_text("Linux\n")
        return ""

    def _cmd_cd(self, args):
        """Меняет текущую директорию в пространстве VFS."""
        if len(args) > MAX_CD_ARGS:
            err = "sh: cd: too many arguments"
            self.print_text(f"{err}\n")
            return err
        target = args[0] if args else "/"
        resolved = self._resolve_path(target)
        if resolved in self.vfs_files and self.vfs_files[resolved]["type"] == "dir":
            self.current_path = resolved
            return ""
        err = f"sh: cd: {target}: No such file or directory"
        self.print_text(f"{err}\n")
        return err

    def _cmd_ls(self, args):
        """Выводит список файлов и папок в VFS с поддержкой -a и -l."""
        show_all, use_long, path_arg, err = self._parse_ls_args(args)
        if err:
            return err

        target_dir = (
            self._resolve_path(path_arg) if path_arg else self.current_path
        )
        if (
            target_dir not in self.vfs_files 
            or self.vfs_files[target_dir]["type"] != "dir"
        ):
            err = f"ls: cannot access '{path_arg}': No such directory"
            self.print_text(f"{err}\n")
            return err

        items = self._collect_ls_items(target_dir, use_long)
        if show_all:
            dots = (
                ["drwxr-xr-x root .", "drwxr-xr-x root .."] 
                if use_long else [".", ".."]
            )
            items = dots + items

        if items:
            delim = "\n" if use_long else "  "
            self.print_text(delim.join(sorted(items)) + "\n")
        return ""

    def _collect_ls_items(self, target_dir, use_long):
        """Собирает элементы директории для команды ls."""
        items = []
        for k in self.vfs_files.keys():
            if k == "/":
                continue
            k_parent = "/".join(k.split("/")[:-1]) or "/"
            if k_parent == target_dir:
                name = k.split("/")[-1]
                if use_long:
                    owner = self.vfs_files[k].get("owner", "root")
                    t_char = (
                        "d" if self.vfs_files[k]["type"] == "dir" else "-"
                    )
                    items.append(f"{t_char}rwxr-xr-x {owner} {name}")
                else:
                    items.append(name)
        return items


    def _parse_ls_args(self, args):
        """Парсит входящие аргументы для команды ls."""
        show_all, use_long, path_arg = False, False, None
        for arg in args:
            if arg.startswith("-"):
                if arg in ["-a", "-la", "-al"]:
                    show_all = True
                    use_long = "l" in arg
                elif arg == "-l":
                    use_long = True
                else:
                    err = f"ls: invalid option -- '{arg}'"
                    self.print_text(f"{err}\n")
                    return False, False, None, err
            else:
                if path_arg is None:
                    path_arg = arg
                else:
                    err = "ls: too many arguments"
                    self.print_text(f"{err}\n")
                    return False, False, None, err
        return show_all, use_long, path_arg, ""
    def _cmd_tail(self, args):
        """Выводит последние строки текстового файла из VFS."""
        num_lines, file_arg, err = self._parse_tail_args(args)
        if err:
            return err
        if not file_arg:
            err = "tail: missing file operand"
            self.print_text(f"{err}\n")
            return err

        tgt = self._resolve_path(file_arg)
        if tgt in self.vfs_files and self.vfs_files[tgt]["type"] == "file":
            lines = self.vfs_files[tgt]["content"].splitlines()
            tail_lines = lines[-num_lines:] if num_lines > 0 else []
            for line in tail_lines:
                self.print_text(f"{line}\n")
            return ""
        err = f"tail: cannot open '{file_arg}': No such file"
        self.print_text(f"{err}\n")
        return err

    def _parse_tail_args(self, args):
        """Парсит входящие аргументы для команды tail."""
        two=2
        num_lines, file_arg, i = DEFAULT_TAIL_LINES, None, 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("-n"):
                val = arg[2:] if len(arg) > two else (
                    args[i + 1] if i + 1 < len(args) else ""
                )
                if len(arg) == two:
                    i += 1
                if val.isdigit():
                    num_lines = int(val)
                else:
                    err = f"tail: invalid number of lines: '{val}'"
                    self.print_text(f"{err}\n")
                    return 0, None, err
            elif arg.startswith("-"):
                err = f"tail: invalid option -- '{arg}'"
                self.print_text(f"{err}\n")
                return 0, None, err
            else:
                if file_arg is None:
                    file_arg = arg
                else:
                    err = "tail: too many arguments"
                    self.print_text(f"{err}\n")
                    return 0, None, err
            i += 1
        return num_lines, file_arg, ""

    def _cmd_mkdir(self, args):
        """Создает новые директории внутри VFS (только в памяти)."""
        if not args:
            err = "mkdir: missing operand"
            self.print_text(f"{err}\n")
            return err
        for target in args:
            resolved = self._resolve_path(target)
            parent = "/".join(resolved.split("/")[:-1]) or "/"
            if resolved in self.vfs_files:
                err = f"mkdir: cannot create '{target}': File exists"
                self.print_text(f"{err}\n")
                return err
            if parent not in self.vfs_files or self.vfs_files[parent]["type"] != "dir":
                err = f"mkdir: cannot create '{target}': Parent dir missing"
                self.print_text(f"{err}\n")
                return err
            self.vfs_files[resolved] = {"type": "dir", "owner": "root"}
        return ""

    def _cmd_chown(self, args):
        """Изменяет владельца файла или директории в памяти VFS."""
        two = 2
        if len(args) < two:
            err = "chown: missing operand"
            self.print_text(f"{err}\n")
            return err
            
        new_owner = args[0]
        
        for target in args[1:]:
            resolved = self._resolve_path(target)
            if resolved in self.vfs_files:
                self.vfs_files[resolved]["owner"] = new_owner
            else:
                err = f"chown: cannot access '{target}': No such file"
                self.print_text(f"{err}\n")
                return err
        return ""


    def load_and_run_script(self):
        """Загружает строки стартового скрипта автотестов."""
        if not os.path.exists(self.script_path):
            return
        try:
            with open(self.script_path, "r", encoding="utf-8") as f:
                self.script_commands = [
                    line.strip() for line in f if line.strip()
                ]
            if self.script_commands:
                self.is_running_script = True
                self.root.after(
                    DELAY_SCRIPT_START, self.execute_next_script_command, 0
                )
        except Exception:
            pass

    def execute_next_script_command(self, index):
        """Последовательно воспроизводит команды скрипта с задержкой."""
        if index >= len(self.script_commands):
            self.is_running_script = False
            self.terminal.mark_set(tk.INSERT, tk.END)
            return

        cmd_str = self.script_commands[index]
        self.print_text(f"{cmd_str}\n")
        self.execute_command(cmd_str, from_script=True)
        self.print_text(f"user@emulator:{self.current_path}$ ")
        self.root.after(
            DELAY_SCRIPT_STEP, self.execute_next_script_command, index + 1
        )




def main():
    """Точка входа. Парсит аргументы запуска ОС и стартует GUI."""
    root = tk.Tk()
    TerminalEmulator(root, vfs_path="deep_root.zip", log_path="terminal_log.csv", script_path="tests/start_script.txt")
    root.mainloop()
    parser = argparse.ArgumentParser(description="UNIX Shell Emulator")
    parser.add_argument("--vfs", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--script", required=True)
    args = parser.parse_args()

    root = tk.Tk()
    TerminalEmulator(
        root, vfs_path=args.vfs, log_path=args.log, script_path=args.script
    )
    root.mainloop()


if __name__ == "__main__":
    main()


