from PySide6 import QtCore
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, \
    QLineEdit


class EmittingStream(QtCore.QObject):

    textWritten = QtCore.Signal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

    def flush(self):
        """Just to avoid warning message on console"""
        pass


class InputWin(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(QSize(450, 150))
        self.setWindowTitle("Attention")

        self.userinput = ''

        btn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(btn)
        self.buttonBox.accepted.connect(self.accepted_win)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        self.message = QLabel('Add references:')
        self.input_text = QTextEdit()
        self.input_text.setAcceptRichText(False)

        self.layout.addWidget(self.message)
        self.layout.addWidget(self.input_text)
        self.layout.addWidget(self.buttonBox)

        self.setLayout(self.layout)

    def accepted_win(self):
        self.userinput = self.input_text.toPlainText()
        self.accept()

    @property
    def user_input(self):
        return self.userinput


class OptionSelection(QDialog):
    def __init__(self, labels=None, desc=None):
        super().__init__()
        self.setMinimumSize(QSize(450, 150))
        self.selection = None
        self.item_desc = desc
        self.setWindowTitle('Options')

        btn = QDialogButtonBox.Ok
        self.buttonBox = QDialogButtonBox(btn)
        self.buttonBox.accepted.connect(self.accept)

        layout = QVBoxLayout()

        etiquetas = labels
        if labels:
            for label in etiquetas:
                btn = QPushButton(label)
                btn.setAutoDefault(False)
                btn.clicked.connect(self.select_option)
                layout.addWidget(btn)

        label_text = QHBoxLayout()
        option = QLabel('Not Correct?')
        self.text = QLineEdit()
        self.text.returnPressed.connect(self.try_match)
        label_text.addWidget(option)
        label_text.addWidget(self.text)

        layout.addLayout(label_text)

        self.setLayout(layout)

    def select_option(self):
        self.selection = self.sender().text()
        self.accept()

    def try_match(self):
        palabra = self.text.text().upper()
        self.text.clear()
        if palabra in self.item_desc:
            self.selection = palabra
            self.accept()

    @property
    def get_selection(self):
        return self.selection


class CustomDialog(QDialog):
    def __init__(self, parent=None, text=None):
        super().__init__(parent)
        self.setMinimumSize(QSize(450, 150))
        self.setWindowTitle("Attention")

        btn = QDialogButtonBox.Ok

        self.buttonBox = QDialogButtonBox(btn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        message = QTextEdit()
        message.setReadOnly(True)
        message.setPlainText(text)
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
