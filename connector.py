import ctypes
import ipaddress
import json
import queue
import socket
import threading
import time
import urllib.request
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Connector:
    def __init__(self, root):
        self.root = root
        self.process = None
        self.closing = False
        self.token = secrets.token_urlsafe(32)
        self.directory = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'QZdeskConnector'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.root.title('QZdesk · 电脑助手')
        self.root.iconbitmap(str(Path(__file__).resolve().parent / 'connector.ico'))
        self.root.geometry('560x680')
        self.root.minsize(520, 620)
        ctk.set_appearance_mode('light')
        ctk.set_widget_scaling(1.0)
        self.root.configure(background='#f3f3f3')
        style = ttk.Style()
        style.theme_use('clam')
        font = ('Microsoft YaHei UI', 10)
        style.configure('TFrame', background='#f3f3f3')
        style.configure('TLabel', background='#f3f3f3', foreground='#1a1a1a', font=font)
        style.configure('Muted.TLabel', foreground='#595959')
        style.configure('TCombobox', padding=(12, 9), font=font, arrowsize=16,
                        fieldbackground='#ffffff', foreground='#1a1a1a')
        style.map('TCombobox', fieldbackground=[('readonly', '#ffffff'), ('disabled', '#f3f3f3')],
                  foreground=[('disabled', '#767676'), ('readonly', '#1a1a1a')])
        style.configure('Card.TFrame', background='#ffffff', relief='flat', borderwidth=1)
        style.configure('Status.TFrame', background='#ffffff', relief='flat', borderwidth=1)
        style.configure('Card.TLabel', background='#ffffff', foreground='#0f172a', font=font)
        style.configure('Hint.TLabel', background='#ffffff', foreground='#64748b', font=font)
        style.configure('TButton', padding=(16, 11), font=font, background='#ffffff',
                        foreground='#334155', bordercolor='#e2e8f0', lightcolor='#ffffff',
                        darkcolor='#ffffff', focuscolor='#64748b')
        style.map('TButton', background=[('active', '#f1f5f9')],
                  foreground=[('disabled', '#94a3b8')])
        style.configure('Primary.TButton', background='#0067c0', foreground='#ffffff',
                        bordercolor='#0067c0', lightcolor='#0067c0', darkcolor='#0067c0')
        style.map('Primary.TButton', background=[('disabled', '#e2e8f0'), ('pressed', '#004e92'), ('active', '#005a9e')],
                  foreground=[('disabled', '#595959'), ('!disabled', '#ffffff')])
        style.configure('Danger.TButton', background='#ffffff', foreground='#dc2626',
                        bordercolor='#dc2626', lightcolor='#ffffff', darkcolor='#ffffff')
        style.map('Danger.TButton', background=[('active', '#fef2f2'), ('disabled', '#f8fafc')],
                  foreground=[('disabled', '#94a3b8'), ('active', '#b91c1c')])
        style.configure('TEntry', padding=(12, 10), font=font, fieldbackground='#ffffff',
                        bordercolor='#cbd5e1', lightcolor='#ffffff', darkcolor='#ffffff')
        style.map('TEntry', bordercolor=[('focus', '#475569')])
        panel = ctk.CTkScrollableFrame(root, fg_color='#f3f3f3', corner_radius=0)
        panel.pack(fill='both', expand=True, padx=20, pady=20)
        ui_font = ('Microsoft YaHei UI', 14)
        ctk.CTkLabel(panel, text='QZdesk · 电脑助手', font=ui_font,
                     text_color='#475569').pack(anchor='w', padx=8)
        ctk.CTkLabel(panel, text='连接你的设备', font=('Microsoft YaHei UI', 24, 'bold'),
                     text_color='#0f172a').pack(anchor='w', padx=8, pady=(18, 4))
        ctk.CTkLabel(panel, text='同一网络，在 QZdesk 上确认授权。', font=ui_font,
                     text_color='#475569').pack(anchor='w', padx=8, pady=(0, 22))
        self.state = tk.StringVar(value='等待连接')
        self.pulse_phase = 0
        self.is_active = False
        self.host = tk.StringVar()
        self.device = tk.StringVar()
        self.address = tk.StringVar(value='启动后生成连接地址')
        self.events = queue.Queue()
        self.devices = {}
        self.pair_cancel = threading.Event()
        self.selection = tk.StringVar()
        network = ctk.CTkFrame(panel, fg_color='#ffffff', corner_radius=18)
        network.pack(fill='x', padx=4)
        status = ctk.CTkFrame(network, fg_color='transparent')
        status.pack(fill='x', padx=22, pady=(20, 14))
        self.indicator = tk.Canvas(status, width=16, height=16, background='#ffffff', highlightthickness=0)
        self.indicator.pack(side='left', padx=(0, 8))
        self.indicator.create_oval(3, 3, 13, 13, fill='#cbd5e1', outline='', tags='dot')
        self.indicator.create_oval(3, 3, 13, 13, fill='#cbd5e1', outline='', tags='pulse', state='hidden')
        ctk.CTkLabel(status, textvariable=self.state, font=ui_font,
                     text_color='#475569', wraplength=360, anchor='w').pack(side='left', fill='x', expand=True)
        device_row = ctk.CTkFrame(network, fg_color='transparent')
        device_row.pack(fill='x', padx=22, pady=(0, 16))
        self.device_list = ctk.CTkComboBox(device_row, variable=self.selection, values=[], state='readonly',
            font=ui_font, height=44, corner_radius=10, border_width=1, border_color='#cbd5e1',
            fg_color='#f8fafc', button_color='#e2e8f0', button_hover_color='#cbd5e1', text_color='#0f172a')
        self.device_list.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.entries = [self.device_list]
        self.scan_button = ctk.CTkButton(device_row, text='刷新', command=self.scan, width=64, height=44,
            corner_radius=10, fg_color='#eef2f6', hover_color='#e2e8f0', text_color='#334155', font=ui_font)
        self.scan_button.pack(side='right')
        actions = ctk.CTkFrame(network, fg_color='transparent')
        actions.pack(fill='x', padx=22, pady=(0, 20))
        self.start_button = ctk.CTkButton(actions, text='连接设备', command=self.start, height=44,
            corner_radius=12, fg_color='#2563eb', hover_color='#1d4ed8', font=ui_font)
        self.start_button.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.stop_button = ctk.CTkButton(actions, text='停止访问', command=self.stop, state='disabled',
            width=100, height=44, corner_radius=12, fg_color='#f1f5f9', hover_color='#fee2e2',
            text_color='#b91c1c', text_color_disabled='#64748b', font=ui_font)
        self.stop_button.pack(side='right')
        self.pairing = ctk.CTkFrame(network, fg_color='#f4f7fc', corner_radius=12)
        self.pair_code = tk.StringVar(value='')
        ctk.CTkLabel(self.pairing, text='核对校验码', text_color='#475569', font=ui_font).pack(pady=(12, 0))
        ctk.CTkLabel(self.pairing, textvariable=self.pair_code,
            font=('Consolas', 28, 'bold'), text_color='#1e40af').pack(pady=6)
        self.pair_hint = tk.StringVar(value='在 QZdesk 屏幕上点击允许。')
        ctk.CTkLabel(self.pairing, textvariable=self.pair_hint, font=('Microsoft YaHei UI', 12),
            text_color='#475569', wraplength=380).pack(padx=16, pady=(0, 14))
        self.details_button = ctk.CTkButton(panel, text='连接详情', command=self.toggle_details,
            fg_color='transparent', hover_color='#e8edf3', text_color='#475569', height=36,
            width=96, corner_radius=10, font=('Microsoft YaHei UI', 12))
        self.details_button.pack(anchor='w', padx=4, pady=(12, 0))
        self.details = ctk.CTkFrame(panel, fg_color='#ffffff', corner_radius=14)
        ctk.CTkEntry(self.details, textvariable=self.address, state='readonly',
            height=36, corner_radius=8, font=('Consolas', 12)).pack(fill='x', padx=16, pady=(16, 8))
        copy_actions = ctk.CTkFrame(self.details, fg_color='transparent')
        copy_actions.pack(fill='x', padx=16, pady=(0, 16))
        self.address_button = ctk.CTkButton(copy_actions, text='复制地址', command=self.copy_address,
            state='disabled', width=90, height=36, corner_radius=8, font=('Microsoft YaHei UI', 12))
        self.address_button.pack(side='left', padx=(0, 8))
        ctk.CTkButton(copy_actions, text='复制密钥', command=self.copy, width=90, height=36,
            corner_radius=8, font=('Microsoft YaHei UI', 12)).pack(side='left', padx=(0, 8))
        ctk.CTkButton(copy_actions, text='日志', command=self.open_logs, width=64, height=36,
            corner_radius=8, fg_color='#eef2f6', hover_color='#e2e8f0', text_color='#334155',
            font=('Microsoft YaHei UI', 12)).pack(side='left')
        self.feedback = tk.StringVar()
        ctk.CTkLabel(panel, textvariable=self.feedback, text_color='#475569', wraplength=420,
            justify='left', font=('Microsoft YaHei UI', 12)).pack(anchor='w', padx=8, pady=(8, 0))
        ctk.CTkLabel(panel, text='访问由设备授权，关闭窗口即可结束。', text_color='#475569',
            font=('Microsoft YaHei UI', 12)).pack(anchor='w', padx=8, pady=(8, 12))
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(300, self.poll)
        root.after(400, self.scan)
        root.after(50, self.update_pulse)

    def toggle_details(self):
        if self.details.winfo_manager():
            self.details.pack_forget()
            self.details_button.configure(text='连接详情')

        else:
            self.details.pack(after=self.details_button, fill='x', pady=(8, 0))
            self.details_button.configure(text='收起详情')


    def update_pulse(self):
        """呼吸灯脉冲动画（仅在 is_active=True 时显示）"""
        if self.is_active:
            import math
            self.pulse_phase = (self.pulse_phase + 0.08) % (2 * math.pi)
            opacity = int((math.sin(self.pulse_phase) + 1) * 127.5)
            weight = 0.35 + opacity / 255 * 0.65
            channels = [round(255 + (channel - 255) * weight) for channel in (22, 163, 74)]
            pulse_color = '#' + ''.join(f'{channel:02x}' for channel in channels)
            try:
                if pulse_color:
                    self.indicator.itemconfigure('pulse', fill=pulse_color, state='normal')
                else:
                    self.indicator.itemconfigure('pulse', state='hidden')
            except tk.TclError:
                pass
        else:
            try:
                self.indicator.itemconfigure('pulse', state='hidden')
            except tk.TclError:
                pass
        if not self.closing:
            self.root.after(50, self.update_pulse)

    def scan(self):
        if self.process:
            return
        self.scan_button.configure(state='disabled')
        self.state.set('正在搜索局域网 QZdesk…')
        def worker():
            found = {}
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(0.4)
                    targets = {'255.255.255.255'}
                    for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                        ip = info[4][0]
                        if ipaddress.IPv4Address(ip).is_private and not ip.startswith('127.'):
                            targets.add(ip.rsplit('.', 1)[0] + '.255')
                    for target in targets:
                        try:
                            sock.sendto(b'QZDESK_DISCOVER_V1', (target, 18765))
                        except OSError:
                            continue
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        try:
                            data, peer = sock.recvfrom(1024)
                            value = json.loads(data)
                            port = value.get('port')
                            if value.get('service') == 'qzdesk-pairing-v1' and isinstance(port, int) and 1 <= port <= 65535:
                                found[f'QZdesk · {peer[0]}'] = (peer[0], port)
                        except (socket.timeout, ValueError):
                            continue
                self.events.put(('devices', found))
            except OSError as error:
                self.events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def pair_http(host, port, path, body):
        request = urllib.request.Request(f'http://{host}:{port}/api/computer/{path}',
            json.dumps(body).encode(), {'Content-Type': 'application/json'}, method='POST')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=5) as response:
            return json.loads(response.read(8192))

    def pairing_worker(self, host, port):
        try:
            result = self.pair_http(host, port, 'pair', {'name': socket.gethostname(), 'token': self.token})
            self.events.put(('code', result['code']))
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline and not self.pair_cancel.wait(1):
                response = self.pair_http(host, port, 'status', {'id': result['id']})
                status = response['status']
                if status != 'pending':
                    if not self.pair_cancel.is_set():
                        self.events.put(('approved', response.get('control') is True) if status == 'approved' else ('pair', status))
                    return
            if not self.pair_cancel.is_set():
                self.events.put(('pair', 'expired'))
        except (OSError, ValueError, KeyError) as error:
            if not self.pair_cancel.is_set():
                self.events.put(('error', str(error)))

    def start(self):
        if self.process:
            return
        try:
            if self.selection.get() not in self.devices:
                raise ValueError('请先选择搜索到的 QZdesk')
            device, port = self.devices[self.selection.get()]
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
                route.connect((device, port))
                self.host.set(route.getsockname()[0])
            self.device.set(device)
            self.token = secrets.token_urlsafe(32)
            self.pair_cancel = threading.Event()
            networks = [ipaddress.ip_network(item) for item in ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']]
            addresses = [ipaddress.IPv4Address(value.get().strip()) for value in [self.host, self.device]]
            if any(not any(address in network for network in networks) for address in addresses):
                raise ValueError('请填写有效的局域网 IPv4 地址')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                try:
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    probe.bind((str(addresses[0]), 8000))
                except OSError as error:
                    raise ValueError('端口 8000 已被占用或无法绑定。请先在旧电脑助手中点击停止访问并关闭旧窗口；如果仍失败，在任务管理器检查 QZdeskMcpEngine.exe。不要同时启动两个连接器。') from error
            engine = Path(sys.executable).parent / 'engine' / 'QZdeskMcpEngine.exe'
            if not engine.exists():
                raise ValueError('缺少 engine 目录，请使用完整发行包')
            with (self.directory / 'server.log').open('ab') as log:
                self.process = subprocess.Popen([str(engine), 'serve', '--transport', 'streamable-http',
                    '--host', str(addresses[0]), '--port', '8000', '--auth-key', self.token,
                    '--ip-allowlist', str(addresses[1]), '--tools', 'Snapshot', '--no-control'], stdin=subprocess.DEVNULL,
                    stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            self.address.set(f'http://{addresses[0]}:8000/mcp')
            self.address_button.configure(state='normal')
            self.indicator.itemconfigure('dot', fill='#d97706')
            self.state.set('引擎运行中 · 等待设备连接验证')
            self.start_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
            for entry in self.entries:
                entry.configure(state='disabled')
            threading.Thread(target=self.pairing_worker, args=(device, port), daemon=True).start()
        except (ValueError, OSError) as error:
            messagebox.showerror('无法启动', str(error))

    def stop(self):
        self.pair_cancel.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.state.set('正在停止访问…')
        self.stop_button.configure(state='disabled')

    def poll(self):
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == 'devices':
                self.devices = value
                self.device_list.configure(values=list(value))
                self.selection.set(next(iter(value), ''))
                self.scan_button.configure(state='normal')
                self.state.set(f'发现 {len(value)} 台 QZdesk' if value else '未发现设备，请确认设备已更新并处于同一局域网')
            elif kind == 'code':
                self.pairing.pack(fill='x', padx=22, pady=(0, 20))
                self.pair_code.set('  '.join(str(value)))
                self.pair_hint.set('请在 QZdesk 屏幕核对这个校验码并点击允许（90秒内）。')
            elif kind == 'approved' and self.process:
                if value:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                        engine = Path(sys.executable).parent / 'engine' / 'QZdeskMcpEngine.exe'
                        with (self.directory / 'server.log').open('ab') as log:
                            self.process = subprocess.Popen([str(engine), 'serve', '--transport', 'streamable-http',
                                '--host', self.host.get(), '--port', '8000', '--auth-key', self.token,
                                '--ip-allowlist', self.device.get(), '--tools', 'Snapshot,Click,Type,Scroll,Move,Shortcut,App,ControlStatus',
                                '--control'], stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                    except (OSError, subprocess.TimeoutExpired) as error:
                        self.feedback.set(f'控制模式启动失败：{error}')
                        self.stop()
                        continue
                self.indicator.itemconfigure('dot', fill='#16a34a')
                self.state.set('已授权控制 · 可点击和输入' if value else '已配对 · 仅查看')
                self.pairing.pack_forget()
                self.pair_hint.set('点击停止访问可立即结束本次连接。')
                self.is_active = True
            elif kind in ('error', 'pair'):
                self.stop()
                self.feedback.set(str(value) if kind == 'error' else '配对被拒绝或已过期，请重新发起。')
                self.scan_button.configure(state='normal')
        if self.process and self.process.poll() is not None:
            code = self.process.returncode
            self.process = None
            self.state.set('访问已停止' if code == 0 else f'引擎已退出（{code}），请查看日志')
            self.indicator.itemconfigure('dot', fill='#94a3b8' if code == 0 else '#dc2626')
            self.is_active = False
            self.address_button.configure(state='disabled')
            self.start_button.configure(state='normal')
            self.stop_button.configure(state='disabled')
            for entry in self.entries:
                entry.configure(state='readonly')
        if self.closing and not self.process:
            self.root.destroy()
            return
        self.root.after(500 if self.process else 1500, self.poll)

    def copy_value(self, value, message):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.feedback.set(message)
        if getattr(self, 'feedback_timer', None):
            self.root.after_cancel(self.feedback_timer)
        self.feedback_timer = self.root.after(3000, self.clear_feedback)

    def clear_feedback(self):
        self.feedback.set('')
        self.feedback_timer = None

    def copy(self):
        self.copy_value(self.token, '密钥已复制，请仅粘贴到你的 QZdesk 配置。')

    def copy_address(self):
        if self.process and self.process.poll() is None:
            self.copy_value(self.address.get(), '连接地址已复制。')

    def open_logs(self):
        window = getattr(self, 'log_window', None)
        if window is not None and window.winfo_exists():
            window.lift()
            window.focus_set()
            return
        window = ctk.CTkToplevel(self.root)
        self.log_window = window
        window.title('QZdesk · 运行日志')
        window.geometry('760x520')
        window.minsize(520, 360)
        window.transient(self.root)
        toolbar = ctk.CTkFrame(window, fg_color='transparent')
        toolbar.pack(fill='x', padx=20, pady=(16, 8))
        ctk.CTkLabel(toolbar, text='运行日志 · 每 2 秒刷新',
                     font=('Microsoft YaHei UI', 14)).pack(side='left')
        text = ctk.CTkTextbox(window, corner_radius=12, font=('Consolas', 13), wrap='word')
        text.pack(fill='both', expand=True, padx=20, pady=(0, 12))
        text.configure(state='disabled')
        status = tk.StringVar(value='显示最近 128 KiB；密钥已隐藏')
        ctk.CTkLabel(window, textvariable=status, font=('Microsoft YaHei UI', 12)).pack(pady=(0, 12))
        previous = [None]

        def refresh():
            if not window.winfo_exists():
                return
            try:
                with (self.directory / 'server.log').open('rb') as stream:
                    stream.seek(0, 2)
                    size = stream.tell()
                    stream.seek(max(0, size - 131072))
                    content = stream.read(131072).decode('utf-8', errors='replace')
                content = content.replace(self.token, '[密钥已隐藏]')
                if not content:
                    content = '暂无日志，连接设备后会在这里显示。'
            except FileNotFoundError:
                content = '暂无日志，连接设备后会在这里显示。'
            except OSError as error:
                content = f'无法读取日志：{error}'
            if content != previous[0]:
                at_bottom = text.yview()[1] >= 0.99
                position = text.yview()[0]
                text.configure(state='normal')
                text.delete('1.0', 'end')
                text.insert('1.0', content)
                text.configure(state='disabled')
                if at_bottom or previous[0] is None:
                    text.see('end')
                else:
                    text.yview_moveto(position)
                previous[0] = content
            window.after(2000, refresh)

        def copy_logs():
            window.clipboard_clear()
            window.clipboard_append(text.get('1.0', 'end-1c'))
            status.set('日志已复制；密钥已隐藏')

        ctk.CTkButton(toolbar, text='复制日志', command=copy_logs, width=100,
                      height=36, corner_radius=10).pack(side='right')
        refresh()

    def close(self):
        self.closing = True
        self.start_button.configure(state='disabled')
        self.stop()


if __name__ == '__main__':
    if sys.platform != 'win32':
        raise SystemExit('仅支持 Windows')
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (OSError, AttributeError):
        pass
    root = tk.Tk()
    Connector(root)
    root.mainloop()
