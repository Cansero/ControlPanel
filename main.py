import threading
import sys

import pandas as pd
from gspread.utils import rowcol_to_a1
from PySide6 import QtGui
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTableView, QApplication, QMainWindow, QWidget, QCheckBox

from ffautomation import *
from table_content import TableContent
from win_utils import *

time = {
    'time_left': 30,
    'continue': True,
    'update_time': 30
}
auto_update_time = {
    'time_left': 5,
    'continue': True,
    'update_time': 5
}

today = datetime.today().strftime('%Y-%m-%d')
month = datetime.today().strftime('%Y-%m')

gc = gspread.oauth(
    credentials_filename='Credentials/credentials.json',
    authorized_user_filename='Credentials/authorized_user.json'
)


class MainWindow(QMainWindow):
    # Region __init__
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('FF Control Panel')
        self.setMinimumSize(1000, 600)

        # Connect to spreadsheet
        self.buffalo = gc.open('BUFFALO WAREHOUSE').worksheet(month)

        # Menubar for testing
        menu = self.menuBar()
        test = QAction('Test', self)
        test.triggered.connect(self.test)
        menu.addAction(test)

        # Main Table
        self.data = None
        self.data_df = None
        self.table = QTableView()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.doubleClicked.connect(self.select_cells)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)

        # Side Layout
        options_layout = QVBoxLayout()

        # Update Layout
        update = QHBoxLayout()
        self.update_label = QLabel('Not sync')
        self.update_button = QPushButton('Update')
        self.update_button.clicked.connect(self.update_button_clicked)
        self.toggle_update = QPushButton('Cancel Sync')
        self.toggle_update.setEnabled(False)
        self.toggle_update.clicked.connect(self.toggle_update_state)

        update.addWidget(self.update_label)
        update.addWidget(self.update_button)
        update.addWidget(self.toggle_update)
        options_layout.addLayout(update)

        receiving_lay = QHBoxLayout()
        receiving_info = QVBoxLayout()
        self.to_receive = QTableView()
        self.sec_df = None

        label = QLabel('Or receive')

        from_lay = QHBoxLayout()
        from_label = QLabel('From:')
        self.from_line = QLineEdit()
        from_lay.addWidget(from_label)
        from_lay.addWidget(self.from_line)

        to_lay = QHBoxLayout()
        to_label = QLabel('To:')
        self.to_line = QLineEdit()
        to_lay.addWidget(to_label)
        to_lay.addWidget(self.to_line)

        receiving_info.addWidget(self.to_receive)
        receiving_info.addWidget(label)
        receiving_info.addLayout(from_lay)
        receiving_info.addLayout(to_lay)

        self.receive_button = QPushButton('Receive')
        self.receive_button.setEnabled(False)
        self.receive_button.clicked.connect(self.receive_table)

        receiving_lay.addLayout(receiving_info)
        receiving_lay.addWidget(self.receive_button)

        options_layout.addLayout(receiving_lay)

        # Auto_update button
        self.auto_update_button = QCheckBox('Auto Receive and Update Tables')
        self.auto_update_button.stateChanged.connect(self.auto_updating)
        options_layout.addWidget(self.auto_update_button)

        # Terminal
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        options_layout.addWidget(self.terminal)

        main_layout.addLayout(options_layout)
        main_layout.setStretchFactor(self.table, 2)
        main_layout.setStretchFactor(options_layout, 1)
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

        # Print to terminal
        sys.stdout = EmittingStream(textWritten=self.normal_output_written)
        self.updating = start_updating(self)
        self.is_auto_updating = None
        # End __init__

    def test(self):
        print(self.updating.is_alive())

    def select_cells(self, i):
        """
        Adds to from_line and to_line the info of the doubleClicked cell.
        It will write first into from_line. If from_line already has a value, will write into to_line.
        If both fields contain values or only to_line has a value, will write into from_line and clear to_line
        """
        cell = self.data_df.iloc[i.row(), i.column()]
        if not self.from_line.text() and not self.to_line.text():
            self.from_line.setText(cell)
        elif self.from_line.text() and not self.to_line.text():
            self.to_line.setText(cell)
        else:
            self.from_line.setText(cell)
            self.to_line.clear()

    def set_table(self):
        df_test = self.data_df[self.data_df['DATE'] == today]
        stop_point = 0
        count = 0
        for i, _, n in df_test.loc[:, :'SCANNED INBOUND TRACKING'].itertuples(index=True, name=None):
            if not n == '':
                count = 0
            else:
                count += 1
                if count >= 10:
                    stop_point = i
                    break
        df = self.data_df
        df = df.loc[:stop_point]
        self.data_df = df
        self.table.setModel(TableContent(df))
        self.table.resizeRowsToContents()
        index = self.table.model().index(stop_point - 2, 0)
        sleep(0.1)  # ? For some reason the table does not scroll without this
        self.table.scrollTo(index)

    def set_sec_table(self):
        """
        Sets secondary table base on packages of 'today'.
        Packages are all that don't have Reference and are not N/A.
        If 'RCVD' found on notes, all packages below the last 'RCVD' which meet the previous requirements.
        """
        df = self.sec_df
        if not df.empty:
            df = df[df['DATE'] == today]
            df = df[df['REFERENCE (ONLY USE IF THERE IS NO TRACKING)'] == '']
            df = df[df['BOX ID'] != 'N/A']

            rcvd = df[df['NOTES'] == 'RCVD']
            if not rcvd.empty:
                rcvd = rcvd.iloc[-1].name
                df = df.loc[rcvd + 1:]

            df = df.loc[:, 'INBOUND USED':'BOX ID']

        self.sec_df = df
        self.to_receive.setModel(TableContent(df))
        return

    @property
    def getdata(self):
        return self.data

    def setdata(self, df):
        self.data = df
        df = pd.DataFrame(df)
        df.index += 2
        df['INBOUND USED'] = df['INBOUND USED'].astype(str)
        self.data_df = df
        self.sec_df = df
        return

    def enable_receive(self, state):
        self.receive_button.setEnabled(state)
        return

    def enable_update(self, state):
        self.toggle_update.setEnabled(state)
        return

    def update_button_clicked(self):
        self.set_table()
        self.set_sec_table()
        self.set_label('Status: ~')

    def receive_table(self):
        """
        Receives packages. If both from_line and to_line contains values, uses that information. Values should
        come from 'INBOUND USED'. If only one field contains information, while use info from to_receive only if its
        not empty.
        """
        text = ''
        comment = False
        if self.from_line.text() and self.to_line.text():
            start_from, ends_in = self.from_line.text(), self.to_line.text()
            self.from_line.clear()
            self.to_line.clear()

            df = self.data_df
            start_from = df[df['INBOUND USED'] == start_from]
            start_from = start_from.index[0] if len(start_from) == 1 else start_from.iloc[-1].index
            ends_in = df[df['INBOUND USED'] == ends_in]
            ends_in = ends_in.index[0] if len(ends_in) == 1 else ends_in.iloc[-1].index

            df = df.loc[start_from:ends_in, 'INBOUND USED':'BOX ID']
            tracking, nship = df['INBOUND USED'].tolist(), df['BOX ID'].tolist()

        elif self.sec_df.empty:
            return

        else:
            tracking, nship = self.sec_df['INBOUND USED'].tolist(), self.sec_df['BOX ID'].tolist()
            comment = True

        packages_nship = [[A, B] for A, B in zip(tracking, nship)]
        repeated, holds, problems, not_found = receiving(packages_nship, 0.5)

        dictionary = {"Repeated": repeated, "Holds": holds, "Problems": problems, "Not found": not_found}
        for category in dictionary:
            if dictionary[category]:
                text += "{}:\n".format(category)
                for value in dictionary[category]:
                    text += value + '\n'
        if not text:
            text += 'All packages found'

        if comment:
            self.rcvd(tracking[-1])

        self.update_file(dictionary)
        print(datetime.now(), ':\n', text)
        return

    def rcvd(self, tracking):
        df = self.data_df
        index = df[df['INBOUND USED'] == tracking]
        index = index.index[0] if len(index) == 1 else index.index[-1]
        a_notation = rowcol_to_a1(index, 6)
        self.buffalo.update(a_notation, 'RCVD')
        return

    def update_file(self, values):
        indexes = []
        updates = []
        df = self.data_df
        for category in values:
            if values[category]:
                for value in values[category]:
                    index = df[df['INBOUND USED'] == value]
                    index = index.index[0] if len(index) == 1 else index.index[-1]
                    indexes.append((category, index))

        for message, place in indexes:
            a_notation = rowcol_to_a1(place, 5)
            match message:
                case 'Repeated':
                    updates.append({'range': a_notation, 'values': [['COMBINED']]})
                case 'Holds':
                    updates.append({'range': a_notation, 'values': [['HOLD']]})
                case 'Problems':
                    updates.append({'range': a_notation, 'values': [['PROBLEM']]})
                case 'Not found':
                    updates.append({'range': a_notation, 'values': [['NOT IN FF']]})

        self.buffalo.batch_update(updates)
        return

    def set_label(self, text):
        self.update_label.setText(text)
        return

    def toggle_update_state(self):
        if self.updating.is_alive():
            cancel_sync()
            self.toggle_update.setText('Start Sync')
        else:
            self.enable_update(False)
            self.updating = start_updating(self)
            self.toggle_update.setText('Cancel Sync')
            time['continue'] = True
        return

    def auto_updating(self, state):
        if state == 2:  # Value for checked
            auto_update_time['continue'] = True
            self.is_auto_updating = start_auto_updating(self)
        elif state == 0:  # Value for unchecked
            stop_auto_updating()
        return

    def normal_output_written(self, text):
        cursor = self.terminal.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()
        return

    def closeEvent(self, event):
        cancel_sync()
        return


# End Main


def checkupdate(window: MainWindow):
    buffalo = gc.open('BUFFALO WAREHOUSE').worksheet(month)
    df = buffalo.get_all_records()
    window.setdata(df)
    window.set_table()
    window.set_sec_table()
    window.enable_receive(True)
    window.set_label('Status: ~')
    window.enable_update(True)

    while time['continue']:
        if time['time_left'] > 0:
            sleep(0.2)
            time['time_left'] -= 0.2
        else:
            df = buffalo.get_all_records()
            if df != window.getdata:
                window.setdata(df)
                window.set_label('Status: !')
            time['time_left'] = time['update_time']
    window.set_label('Not Sync')
    return


def cancel_sync():
    time['continue'] = False
    return


def start_updating(window):
    x = threading.Thread(target=checkupdate, args=(window,))
    x.start()
    return x


def start_auto_updating(window):
    x = threading.Thread(target=autoupdate, args=(window,))
    x.start()
    return x


def stop_auto_updating():
    auto_update_time['continue'] = False


def autoupdate(window: MainWindow):
    while auto_update_time['continue']:
        if auto_update_time['time_left'] > 0:
            sleep(1)
            auto_update_time['time_left'] -= 1
        else:
            if window.update_label.text() == 'Status: !':
                window.update_button_clicked()
                sleep(5)
            window.receive_table()
            auto_update_time['time_left'] = auto_update_time['update_time']
    return


if __name__ == "__main__":
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
    exit(0)
