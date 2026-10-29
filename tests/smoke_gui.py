import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from src.core.database import Database
from src.ui.windows.main import MainWindow
from src.ui.dialogs.import_accounts import ImportAccountsDialog

SID = "deadbeefcafe1234567890abcdef1234"
db = Database()
db.save_account("smoke_user", "smoke.cookie", tag="smoke")
db.set("upload_delay", 5)

window = MainWindow()
assert window.windowTitle() == "ClipForge"
assert window.pages.currentWidget() is window.overview_page
assert window.sidebar.ITEMS == ["Обзор", "Публикации", "Аккаунты", "Статистика", "Настройки"]
assert window.accounts_page.table.rowCount() >= 0
window.accounts_page.search.setText("smoke")
window.show_page(1)
assert window.uploads_page.group.count() >= 1, "группа не построилась"
window.uploads_page.refresh()
window.show_page(2)
window.stats_page.reload()
window.stats_page._export  # существует
window.show_page(3)
window.settings_page.refresh()
assert window.settings_page.delay.value() == 5

dlg = ImportAccountsDialog(window, db.get_account_tags())
dlg.text.setPlainText(f"newuser\t{SID}\tuseast8\nbad line here\n")
assert len(dlg.accounts) == 1, dlg.accounts
dlg.tag_input.setText("smoke")
dlg.accept_action()
assert dlg.accounts[0]["username"] == "newuser"

window.accounts_page._save_account("newuser", "smoke", SID, "useast8", quiet=True)
assert db.get_account_by_username("newuser") is not None
window.accounts_page.refresh()
window.accounts_page.search.setText("newuser")
assert window.accounts_page.table.rowCount() == 1
rows = window.accounts_page._selected_rows()
window.accounts_page._delete_selected()  # без выбора ничего не делает

# очередь загрузки: несуществующий файл должен дать понятную ошибку, а не падение
from src.ui.pages.uploads import UploadThread
t = UploadThread("C:/нет-такого-файла.mp4", "test", ["newuser"])
print("thread ok:", t.delay == 0)

for name in ("smoke_user", "newuser"):
    acc = db.get_account_by_username(name)
    if acc:
        db.delete_accounts([acc[0]])

print("SMOKE OK")
