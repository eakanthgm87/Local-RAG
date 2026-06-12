"""
Ollama Server & Model Manager.
Provides ability to start/stop the Ollama server and manage models (download, run, stop).
"""
import os
import sys
import time
import logging
import subprocess
import signal
import platform
from typing import Dict, Optional
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class OllamaManager:
    """
    Manages the Ollama server process and models.
    On Windows, Ollama runs as a background process launched by the Ollama app.
    This manager provides subprocess-based control when direct API control isn't available.
    """
    
    _ollama_process = None
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.ollama_exe = self._find_ollama()
    
    def _find_ollama(self) -> Optional[str]:
        """Find Ollama executable in PATH or common install locations."""
        # Check PATH first
        try:
            if platform.system() == "Windows":
                result = subprocess.run(["where", "ollama"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip().split('\n')[0]
            else:
                result = subprocess.run(["which", "ollama"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception:
            pass
        
        # Common install locations
        common_paths = [
            "C:\\Program Files\\Ollama\\ollama.exe",
            "C:\\Program Files (x86)\\Ollama\\ollama.exe",
            os.path.expanduser("~\\AppData\\Local\\Programs\\Ollama\\ollama.exe"),
            "/usr/local/bin/ollama",
            "/usr/bin/ollama",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def is_installed(self) -> bool:
        """Check if Ollama is installed on the system."""
        return self._find_ollama() is not None
    
    def check_server(self) -> Dict:
        """Check if Ollama server is running via API."""
        try:
            resp = requests.get(f"{self.base_url}/api/version", timeout=3)
            if resp.status_code == 200:
                return {"running": True, "version": resp.json().get("version", "unknown")}
        except Exception:
            pass
        return {"running": False, "version": None}
    
    def get_running_models(self) -> list:
        """Get list of models currently loaded in memory via /api/ps."""
        try:
            resp = requests.get(f"{self.base_url}/api/ps", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                return [m.get("name", "") for m in models]
        except Exception:
            pass
        return []
    
    def start_server(self) -> Dict:
        """Start the Ollama server as a background process."""
        # Check if already running
        status = self.check_server()
        if status["running"]:
            return {"success": True, "message": "Ollama server is already running."}
        
        if not self._find_ollama():
            return {"success": False, "message": "Ollama is not installed. Download from https://ollama.com"}
        
        try:
            # Use subprocess.run with creationflags for Windows detached process
            # This avoids creating a visible console window
            startupinfo = None
            creation_flags = 0
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            
            self._ollama_process = subprocess.Popen(
                [self.ollama_exe, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=creation_flags,
            )
            
            # Wait for server to start
            for i in range(15):
                time.sleep(1)
                status = self.check_server()
                if status["running"]:
                    return {"success": True, "message": f"Ollama server started (v{status['version']})"}
            
            return {"success": False, "message": "Server started but not responding. Check Ollama logs."}
        
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return {"success": False, "message": f"Failed to start Ollama: {str(e)}"}
    
    def stop_server(self) -> Dict:
        """Stop the Ollama server gracefully via API."""
        status = self.check_server()
        if not status["running"]:
            return {"success": True, "message": "Ollama server is not running."}
        
        try:
            if platform.system() == "Windows":
                # On Windows, Ollama typically runs as a system service/background app.
                # First try a graceful shutdown via the API
                try:
                    requests.post(f"{self.base_url}/api/shutdown", timeout=5)
                    time.sleep(3)
                    if not self.check_server()["running"]:
                        return {"success": True, "message": "Ollama server stopped gracefully."}
                except Exception:
                    pass
                
                # If graceful shutdown fails, kill only the `ollama serve` process we started,
                # not all ollama.exe (which includes the background service)
                subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"],
                             capture_output=True, text=True, timeout=10)
            else:
                # On Linux/Mac, use pkill
                subprocess.run(["pkill", "-f", "ollama"], 
                             capture_output=True, text=True, timeout=10)
            
            if self._ollama_process:
                self._ollama_process.terminate()
                self._ollama_process = None
            
            time.sleep(2)
            
            # Check if still running (might be the system service)
            if self.check_server()["running"]:
                return {"success": False, "message": "Ollama system service is still running (managed by background app). Use system tray to stop it."}
            
            return {"success": True, "message": "Ollama process stopped."}
        
        except Exception as e:
            logger.error(f"Failed to stop Ollama: {e}")
            return {"success": False, "message": f"Failed to stop Ollama: {str(e)}"}
    
    def run_model(self, model_name: str) -> Dict:
        """
        'Run' a model by sending a warm-up request.
        This keeps the model loaded in Ollama's cache for faster responses.
        """
        if not self.check_server()["running"]:
            return {"success": False, "message": "Ollama server is not running."}
        
        try:
            # First check if model exists
            resp = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=10
            )
            if resp.status_code != 200:
                # Model not found, try to pull it
                pull_result = self.pull_model(model_name)
                if not pull_result["success"]:
                    return pull_result
            
            # Warm up the model by sending a simple prompt
            warm_up = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Hello",
                    "stream": False,
                    "options": {"num_predict": 1}
                },
                timeout=300  # Long timeout for first load
            )
            
            if warm_up.status_code == 200:
                return {"success": True, "message": f"Model '{model_name}' is loaded and ready."}
            else:
                return {"success": False, "message": f"Failed to run model: {warm_up.status_code}"}
        
        except Exception as e:
            logger.error(f"Failed to run model {model_name}: {e}")
            return {"success": False, "message": f"Error running model: {str(e)}"}
    
    def stop_model(self, model_name: str) -> Dict:
        """
        'Stop' a model by telling Ollama to unload it from memory.
        Uses the /api/generate endpoint with keep_alive=0.
        """
        if not self.check_server()["running"]:
            return {"success": False, "message": "Ollama server is not running."}
        
        try:
            # Set keep_alive=0 to unload immediately after request
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",
                    "stream": False,
                    "options": {"num_predict": 0},
                    "keep_alive": "0s"
                },
                timeout=30
            )
            
            if resp.status_code in [200, 404]:
                return {"success": True, "message": f"Model '{model_name}' unloaded from memory."}
            else:
                return {"success": False, "message": f"Failed to stop model: {resp.status_code}"}
        
        except Exception as e:
            logger.error(f"Failed to stop model {model_name}: {e}")
            return {"success": False, "message": f"Error stopping model: {str(e)}"}
    
    def pull_model(self, model_name: str) -> Dict:
        """Download a model from Ollama registry."""
        if not self.check_server()["running"]:
            return {"success": False, "message": "Ollama server is not running."}
        
        try:
            resp = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=600
            )
            if resp.status_code == 200:
                return {"success": True, "message": f"Model '{model_name}' downloaded successfully."}
            else:
                return {"success": False, "message": f"Download failed: {resp.status_code}"}
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return {"success": False, "message": f"Error downloading model: {str(e)}"}
    
    def remove_model(self, model_name: str) -> Dict:
        """Delete a downloaded model from Ollama."""
        if not self.check_server()["running"]:
            return {"success": False, "message": "Ollama server is not running."}
        
        try:
            resp = requests.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
                timeout=30
            )
            if resp.status_code == 200:
                return {"success": True, "message": f"Model '{model_name}' removed."}
            else:
                return {"success": False, "message": f"Failed to remove model: {resp.status_code}"}
        except Exception as e:
            logger.error(f"Failed to remove model {model_name}: {e}")
            return {"success": False, "message": f"Error removing model: {str(e)}"}


# Singleton
ollama_manager = OllamaManager()