from PyQt6.QtWidgets import QMessageBox, QInputDialog


def show_message(parent, title, text, icon=QMessageBox.Icon.Information):
    msg = QMessageBox(parent)
    msg.setIcon(icon)
    msg.setWindowTitle(title)
    msg.setText(text)
    return msg.exec()


def show_info(parent, title, text):
    return show_message(parent, title, text, QMessageBox.Icon.Information)


def show_warning(parent, title, text):
    return show_message(parent, title, text, QMessageBox.Icon.Warning)


def show_error(parent, title, text):
    return show_message(parent, title, text, QMessageBox.Icon.Critical)


def show_question(parent, title, text) -> bool:
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg.setDefaultButton(QMessageBox.StandardButton.No)
    return msg.exec() == QMessageBox.StandardButton.Yes


def get_text(parent, title, label, text=""):
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(text)
    dialog.resize(420, 160)
    ok = dialog.exec()
    return dialog.textValue(), ok == QInputDialog.DialogCode.Accepted
