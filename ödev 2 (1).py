
import sqlite3
from tkinter import *
from tkinter import messagebox as ms
import json
import http.client
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# SQLite veritabanı bağlantısı kurma
conn = sqlite3.connect('veritabanı.db')
cursor = conn.cursor()

# Tabloları oluşturma
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_information(
    amount_of_money INTEGER,
    code TEXT,
    lastupdate TEXT
    )
    ''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS currencies (
    code TEXT PRIMARY KEY,
    name TEXT,
    rate REAL,
    calculatedstr TEXT,
    calculated REAL,
    success TEXT,
    base TEXT,
    lastupdate TEXT
    )
    ''')

conn.commit()

# Tkinter penceresi oluşturma
pen = Tk()
pen.title("Varlık Yönetimi")

# Listbox oluşturma ve yerleştirme
Lb1 = Listbox(pen, selectmode=BROWSE)
Lb1.grid(row=1, column=1)

# HTTP API bağlantısı kurma
conn_api = http.client.HTTPSConnection("api.collectapi.com")

headers = {
    'content-type': "application/json",
    'authorization': "apikey 75P4IkRSIXPURdaFT1ujJi:5Ovgzb5Ma272xPipXec4Yu"
}

conn_api.request("GET", "/economy/currencyToAll?int=10&base=USD", headers=headers)

res = conn_api.getresponse()
data = res.read().decode("utf-8")
conn_api.close()

# API verisini JSON olarak düzenleme
api_data = json.loads(data)

# API yanıtını kontrol etme
if api_data.get('success') is False:
    ms.showerror('API Hatası', f"API hatası: {api_data.get('message', 'Bilinmeyen hata')}")
else:
    if 'result' in api_data and 'data' in api_data['result']:
        currencies_data = api_data['result']['data']
        
        # Currencies tablosuna veri ekleme veya güncelleme
        for currency in currencies_data:
            Lb1.insert(END, currency['code'])

            cursor.execute('''
                INSERT OR REPLACE INTO currencies (code, name, rate, calculatedstr, calculated)
                VALUES (?, ?, ?, ?, ?)
            ''', (currency['code'], currency['name'], currency['rate'], currency['calculatedstr'], currency['calculated']))

        # Currencies tablosunu success, base ve lastupdate ile güncelleme
        cursor.execute('''
            UPDATE currencies
            SET success = ?, base = ?, lastupdate = ?
        ''', (api_data['success'], api_data['result']['base'], api_data['result']['lastupdate']))

        conn.commit()

        print("Başarılı ekleme")
    else:
        ms.showerror('API Hatası', 'API yanıtı beklenen formatta değil')

# Currencies ve user_information tablolarından veri alam
cursor.execute("SELECT * FROM currencies")
rows = cursor.fetchall()

cursor.execute("SELECT * FROM user_information")
rows2 = cursor.fetchall()

# Toplam varlık hesaplama
def total(rows, rows2):
    sum = 0
    for currency in rows:
        selected_code = currency[0]
        cursor.execute("SELECT * FROM user_information WHERE code = ?", (selected_code,))
        user_info = cursor.fetchone()
        if user_info:
            amount = user_info[0]
            rate = currency[2]
            sum += amount * rate
    return sum

# Para güncelleme işlemini gerçekleştiren fonksiyon
def update():
    try:
        selected_index = Lb1.curselection()
        if selected_index and ent1.get() and ent2.get():
            selected_code = Lb1.get(selected_index)
            amount = ent1.get()
            lastupdate = ent2.get()

            cursor.execute('SELECT * FROM user_information WHERE code = ?', (selected_code,))
            existing_row = cursor.fetchone()

            if existing_row:
                cursor.execute('''
                    UPDATE user_information
                    SET amount_of_money = ?, lastupdate = ?
                    WHERE code = ?
                ''', (amount, lastupdate, selected_code))
                ms.showinfo('Başarılı', f'{selected_code} için {amount} para miktarı güncellendi.')
            else:
                cursor.execute('''
                    INSERT INTO user_information (amount, code, lastupdate)
                    VALUES (?, ?, ?)
                ''', (amount, selected_code, lastupdate))
                ms.showinfo('Başarılı', f'{selected_code} için yeni bir kayıt oluşturuldu.')

            conn.commit()
            update_graph()
    except sqlite3.Error as e:
        ms.showerror('Veritabanı Hatası', f'Veritabanı işlemi sırasında hata oluştu: {e}')

# Grafiği güncelleyen fonksiyon
def update_graph():
    cursor.execute("SELECT lastupdate, amount, code FROM user_information")
    data = cursor.fetchall()
    
    if data:
        dates = [row[0] for row in data]
        amounts = [row[1] for row in data]
        codes = [row[2] for row in data]

        fig, ax = plt.subplots()
        ax.plot(dates, amounts, label='Varlık Değeri')

        ax.set(xlabel='Tarih', ylabel='Varlık Değeri',
               title='Varlık Değerinin Tarihsel Değişimi')
        ax.grid()
        ax.legend()

        canvas = FigureCanvasTkAgg(fig, master=pen)
        canvas.draw()
        canvas.get_tk_widget().grid(row=300, columnspan=70)

# Etiketler ve giriş pencereleri oluşturma ve yerleştirme
lbl1 = Label(pen, text="Para miktarı girişi:", font="calibri")
lbl1.grid(row=0, column=0)

ent1 = Entry(pen)
ent1.grid(row=0, column=1)

lbl2 = Label(pen, text="Para miktarı giriş tarihi:", font="calibri")
lbl2.grid(row=50, column=0)

ent2 = Entry(pen)
ent2.grid(row=50, column=1)

lbl3 = Label(pen, text=f"Toplam varlık : {total(rows, rows2)}", font="calibri")
lbl3.grid(row=200, column=0)

lbl3 = Label(pen, text=f"verilerin grafik gösterimi : {update_graph()}", font="calibri")
lbl3.grid(row=200, column=200)

btn1 = Button(pen, text="Para miktarını güncelle", command=update)
btn1.grid(row=4, column=1)

pen.mainloop()

conn.close()

