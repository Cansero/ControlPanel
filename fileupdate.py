import pandas as pd
import gspread

gc = gspread.oauth(
    credentials_filename='credentials/credentials.json',
    authorized_user_filename='credentials/authorized_user.json'
)


def correct_length(string):
    while len(string) < 10:
        string = '0' + string
    return string


def new_packages(directory):
    cm_package = gc.open('CM NSHIP PACKAGE INFORMATION 2023')
    main_file = pd.DataFrame(cm_package.worksheet('MAIN FILE').get_all_records())
    main_file['Inbound tracking'] = main_file['Inbound tracking'].astype(str)

    unreceived = pd.read_csv(directory)
    unreceived = unreceived.loc[:, 'Status':'Postal Code']

    unreceived['Inbound tracking'] = unreceived['Inbound tracking'].str[1:]
    unreceived['Outbound tracking'] = unreceived['Outbound tracking'].str[4:]

    mascara = unreceived['Inbound tracking'].isin(['link to amazon', 'Tracking Available Soon']) | \
              pd.isna(unreceived['Inbound tracking'])

    unreceived = unreceived.loc[~mascara]

    mascara = unreceived['Inbound tracking'].isin(main_file['Inbound tracking'])

    unreceived = unreceived.loc[~mascara]
    unreceived = unreceived.fillna('')

    dl = cm_package.worksheet('DL')
    dl.update([unreceived.columns.values.tolist()] + unreceived.values.tolist())


def asins(directory):
    master_file = gc.open('MASTER FILE NUEVO')
    master_file = pd.DataFrame(master_file.worksheet('DATA').get_all_records())
    master_file['ASIN\n0'] = master_file['ASIN\n0'].astype(str)
    master_file['ASIN\n0'] = master_file['ASIN\n0'].apply(correct_length)

    asins_manual = gc.open('UNRECEIVED CA')
    asins_manual = pd.DataFrame(asins_manual.worksheet('UNRECEIVED CA').get_all_records())
    asins_manual['ASIN'] = asins_manual['ASIN'].astype(str)
    asins_manual['ASIN'] = asins_manual['ASIN'].apply(correct_length)

    unreceived = pd.read_csv(directory)
    unreceived = unreceived.loc[:, ['ASIN', 'Country']]
    unreceived = unreceived.fillna(value={'Country': 'China'})
    unreceived['Country'] = unreceived['Country'].apply(lambda x: x.upper())
    unreceived['ASIN'] = unreceived['ASIN'].astype(str)

    mascara = unreceived['ASIN'].isin(master_file['ASIN\n0'])
    unreceived = unreceived.loc[~mascara]

    mascara = unreceived['ASIN'].isin(asins_manual['ASIN'])
    unreceived = unreceived.loc[~mascara]

    coo = pd.read_csv('CSV/UNRECEIVED CA - COO.csv')
    coo = coo.set_index('COUNTRY')

    unreceived['Country'] = unreceived['Country'].map(coo['ALPHA 2'])
    unreceived = unreceived.fillna(value={'Country': 'CN'})

    asin = unreceived['ASIN'].tolist()
    country = unreceived['Country'].tolist()

    return asin, country
