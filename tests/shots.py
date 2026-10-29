import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.app import Application

application = Application()
app = application.app

from src.core.database import Database
from src.ui.windows.main import MainWindow
from src.ui.dialogs.import_accounts import ImportAccountsDialog
from src.ui.dialogs.login import LoginDialog

db = Database()
for name, tag in (("studio.one", "music"), ("studio.two", "music"), ("brand.three", "clips")):
    if not db.get_account_by_username(name):
        db.save_account(name, f"tiktok_session-{name}.cookie", tag=tag)

window = MainWindow()
window.resize(1120, 720)
window.show()
app.processEvents()

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")
os.makedirs(out, exist_ok=True)
for index, name in ((0, "accounts"), (1, "uploads"), (2, "stats"), (3, "settings")):
    window.show_page(index)
    app.processEvents()
    window.grab().save(os.path.join(out, f"{name}.png"))

dialog = ImportAccountsDialog(window, db.get_account_tags())
dialog.text.setPlainText("studio.four\tabcdef0123456789abcdef0123456789\tuseast8\n")
dialog.show()
app.processEvents()
dialog.grab().save(os.path.join(out, "import.png"))

login = LoginDialog(window, "studio.four")
login.show()
app.processEvents()
login.grab().save(os.path.join(out, "login.png"))
login.close()

for name in ("studio.one", "studio.two", "brand.three"):
    account = db.get_account_by_username(name)
    if account:
        db.delete_accounts([account[0]])
print("SHOTS OK", out)
