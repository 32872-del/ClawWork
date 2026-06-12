import subprocess
import os
import signal
from .. import settings


class ClashManager:
    def __init__(self, exe_path):
        self.exe_path = exe_path
        self.processes = {}
        self.Proxys = {}

    def start(self, config_path, port_name="default"):
        """
        启动 Clash 实例
        """

        p = subprocess.Popen(
            [self.exe_path, "-f", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        self.Proxys[port_name] = {
            "http": f"http://127.0.0.1:{port_name}",
            "https": f"http://127.0.0.1:{port_name}"
        }
        self.processes[port_name] = p
        return p.pid

    def stop(self, port_name):
        """
        关闭指定实例
        """
        if port_name not in self.processes:
            print("[-] 没有这个实例")
            return

        p = self.processes[port_name]

        try:
            os.kill(p.pid, signal.SIGTERM)
        except Exception:
            subprocess.call(["taskkill", "/F", "/PID", str(p.pid)])
        del self.Proxys[port_name]
        del self.processes[port_name]

    def stop_all(self):
        """
        关闭全部
        """
        for k in list(self.processes.keys()):
            self.stop(k)

    def start_all(self):
        Proxys_path = settings.PROXYS_PATH
        Proxys_file_name = os.listdir(Proxys_path)
        for fname in Proxys_file_name:
            port = fname.split(".")[0]
            self.start(fr"{Proxys_path}\{fname}", port)

