"""
Root launcher for Mail AI Project.
Allows starting the Flask application directly from the project root workspace directory.
"""

import os
import sys
import importlib.util

current_dir = os.path.dirname(os.path.abspath(__file__))
mail_ai_dir = os.path.join(current_dir, "mail-ai")

if mail_ai_dir not in sys.path:
    sys.path.insert(0, mail_ai_dir)

# Load mail-ai/app.py explicitly
app_module_path = os.path.join(mail_ai_dir, "app.py")
spec = importlib.util.spec_from_file_location("mail_ai_app", app_module_path)
mail_ai_module = importlib.util.module_from_spec(spec)
sys.modules["mail_ai_app"] = mail_ai_module
spec.loader.exec_module(mail_ai_module)

app = mail_ai_module.app
create_app = mail_ai_module.create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n========================================================")
    print(f" Mail AI Server Running from root on http://127.0.0.1:{port}")
    print(f" College Project: Intelligent Business Email Classification")
    print(f"========================================================\n")
    app.run(host="127.0.0.1", port=port, debug=True)
