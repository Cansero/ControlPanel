import pandas as pd
import gspread
from gspread.utils import rowcol_to_a1

gc = gspread.oauth(
    credentials_filename='Credentials/credentials.json',
    authorized_user_filename='Credentials/authorized_user.json'
)

buffalo = gc.open('BUFFALO WAREHOUSE').worksheet('2023-08')
df = pd.DataFrame(buffalo.get_all_records())

dictionary = {
    'Repeated':
        [],
    'Holds':
        ['TBA308201623665',
         'TBA308203674965'],
    'Problems':
        ['TBA308198284909',
         'TBA308197997854'],
    'Not found':
        ['TBA308185713702']
}
