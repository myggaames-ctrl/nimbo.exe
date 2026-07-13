"""
Windows Detector
"""


class WindowsDetector:

    def detect(self, text: str):

        # ==========================
        # WINDOWS
        # ==========================

        if text.startswith("abre "):

            return {
                "intent": "windows.open_app",
                "query": text.replace("abre ", "").strip()
            }

        return None