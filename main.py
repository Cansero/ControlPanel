import threading
import gspread
from datetime import datetime
import pandas as pd
from time import sleep
from PySide6.QtWidgets import QTableView, QApplication, QMainWindow, QHBoxLayout, QPushButton, QWidget, QVBoxLayout, \
    QLabel, QLineEdit
from table_content import TableContent

from ffautomation import *
from win_utils import *

time = {
    'time_left': 30,
    'continue': True,
    'update_time': 30
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

        self.data = None
        self.data_df = None  # pd.DataFrame(self.data)
        self.table = QTableView()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)

        options_layout = QVBoxLayout()

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

        main_layout.addLayout(options_layout)
        main_layout.setStretchFactor(self.table, 2)
        main_layout.setStretchFactor(options_layout, 1)
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

        start_updating(self)
        # End __init__

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
        self.table.setModel(TableContent(df))
        index = self.table.model().index(stop_point - 2, 0)
        sleep(0.1)  # ? For some reason the table does not scroll without this
        self.table.scrollTo(index)

    def set_sec_table(self):
        """
        Sets secondary table base on packages of 'today'.
        Packages are all that don't have Reference and are not N/A.
        If 'RCVD' found on notes, all packages below the last 'RCVD' which meet the previous requirements.
        """
        # ! Error when table is empty

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

    @property
    def getdata(self):
        return self.data

    def setdata(self, df):
        self.data = df
        df = pd.DataFrame(df)
        df.index += 2
        self.data_df = df
        self.sec_df = df

    def enable_receive(self, state):
        self.receive_button.setEnabled(state)

    def receive_table(self):

        # ! Too much repeated code | Kinda hard to read even for me xd

        text = ''
        if self.from_line.text() and self.to_line.text():
            start_from, ends_in = self.from_line.text(), self.to_line.text()
            self.from_line.clear()
            self.to_line.clear()

            df = self.data_df
            start_from = df[df['INBOUND USED'] == start_from]
            start_from = start_from.index[0] - 2 if len(start_from) == 1 else start_from.iloc[-1].index
            ends_in = df[df['INBOUND USED'] == ends_in]
            ends_in = ends_in.index[0] - 2 if len(ends_in) == 1 else ends_in.iloc[-1].index

            df = df.loc[start_from:ends_in, 'INBOUND USED':'BOX ID']
            tracking, nship = df['INBOUND USED'].tolist(), df['BOX ID'].tolist()
            packages_nship = [[A, B] for A, B in zip(tracking, nship)]
            repeated, holds, problems, not_found = receiving(packages_nship, 0.1)

            dictionary = {"Repeated": repeated, "Holds": holds, "Problems": problems, "Not found": not_found}
            for category in dictionary:
                if dictionary[category]:
                    text += "{}:\n".format(category)
                    for value in dictionary[category]:
                        text += value + '\n'
            if not text:
                text += 'All packages found'

        elif self.from_line.text() or self.to_line.text():
            self.from_line.clear()
            self.to_line.clear()
            text = 'No correct data to receive'

        else:
            tracking, nship = self.sec_df['INBOUND USED'].tolist(), self.sec_df['BOX ID'].tolist()
            packages_nship = [[A, B] for A, B in zip(tracking, nship)]
            repeated, holds, problems, not_found = receiving(packages_nship, 0.1)

            dictionary = {"Repeated": repeated, "Holds": holds, "Problems": problems, "Not found": not_found}
            for category in dictionary:
                if dictionary[category]:
                    text += "{}:\n".format(category)
                    for value in dictionary[category]:
                        text += value + '\n'
            if not text:
                text += 'All packages found'

            self.sec_df = pd.DataFrame()
            self.set_sec_table()

        dlg = CustomDialog(parent=self, text=text)
        dlg.exec()

    def closeEvent(self, event):
        cancel_sync()


# def checkupdate(window):
#     while not state:
#         sleep(5)
#         df = gc.open('FF File').sheet1.get_all_records()
#         if df != window.getdata:
#             window.changelabel('Update: !')
#             window.setdata(df)
#     window.changelabel('Not sync')

def checkupdate(window):
    buffalo = gc.open('BUFFALO WAREHOUSE').worksheet(month)
    df = buffalo.get_all_records()
    window.setdata(df)
    window.set_table()
    window.set_sec_table()
    window.enable_receive(True)

    while time['continue']:
        if time['time_left'] > 0:
            time['time_left'] -= 0.2
            sleep(0.2)
        else:
            df = buffalo.get_all_records()
            if df != window.getdata:
                window.setdata(df)
            time['time_left'] = time['update_time']
    # window.changelabel('Not sync')


def cancel_sync():
    time['continue'] = False


def start_updating(window):
    x = threading.Thread(target=checkupdate, args=(window,))
    x.start()


if __name__ == "__main__":
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
    exit(0)
