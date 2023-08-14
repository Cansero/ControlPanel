import sys

from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import QMainWindow, QTextEdit, QApplication


class EmittingStream(QtCore.QObject):

    textWritten = QtCore.Signal(str)

    def write(self, text):
        self.textWritten.emit(str(text))


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)
        sys.stderr = open('text_files/text.txt', 'w')
        self.setWindowTitle('Test')
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)

        self.setCentralWidget(self.terminal)

        print('lol')
        print('pero que ha pasao')

    def normalOutputWritten(self, text):
        """Append text to the QTextEdit."""
        # Maybe QTextEdit.append() works as well, but this is how I do it:
        cursor = self.terminal.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

    def printtoterminal(self, text):
        pass




if __name__ == '__main__':
    app = QApplication([])
    x = MainWindow()
    x.show()
    app.exec()
