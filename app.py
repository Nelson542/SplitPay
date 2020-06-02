from flask import Flask, render_template, request, redirect
import socket
import sqlite3 as sql

app = Flask(__name__)

con = sql.connect('friends.db')
con.execute('CREATE TABLE IF NOT EXISTS "users" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "username" VARCHAR,'
            '"password" VARCHAR, "paid" REAL DEFAULT 0 , "each" REAL DEFAULT 0 , "balance" REAL DEFAULT 0 )')

con = sql.connect('friends.db')
con.execute('CREATE TABLE IF NOT EXISTS "cur_user" ("user" VARCHAR, "ip_address" VARCHAR )')

con = sql.connect('friends.db')
con.execute('CREATE TABLE IF NOT EXISTS "balance" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "payfrom" VARCHAR,'
            '"payto" VARCHAR, "money" REAL )')

con = sql.connect('friends.db')
con.execute('CREATE TABLE IF NOT EXISTS "events" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "payfrom" VARCHAR,'
            '"payto" VARCHAR, "event_name" VARCHAR, "amount" REAL )')

@app.route('/')
def home():
    return render_template("home.html")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        username = username.title()
        password = request.form['password']

        users = retrieveUsers()
        users = [item for t in users for item in t]

        if username not in users:
            con = sql.connect("friends.db")
            cur = con.cursor()
            cur.execute("INSERT INTO users (username,password) VALUES (?,?)", (username, password))
            con.commit()
            con.close()
        else:
            return redirect('/')

        return redirect('/login')
    return render_template("signup.html")


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username_login = request.form['username']
        username_login = username_login.title()
        password_login = request.form['password']

        con = sql.connect("friends.db")
        cur = con.cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (username_login,))
        password = cur.fetchall()
        password = [item for t in password for item in t]
        con.close()

        ip_address = retrieveIP()

        for item in password:
            if password_login == item:
                con = sql.connect("friends.db")
                cur = con.cursor()
                cur.execute("INSERT INTO cur_user (user, ip_address) VALUES (?,?)", (username_login, ip_address))
                con.commit()
                con.close()
                return redirect('/friends')
            else:
                return redirect('/')

    return render_template("login.html")


@app.route('/base')
def base():
    return render_template("base.html")


@app.route('/friends')
def friends():
    con = sql.connect("friends.db")
    cur = con.cursor()
    ip_address = retrieveIP()
    cur.execute("SELECT user FROM cur_user where ip_address = ?", (ip_address,))
    user = cur.fetchall()
    user = [item for t in user for item in t]

    for item in user:
        cur.execute("SELECT balance FROM users WHERE username = ?", (item,))
        balance = cur.fetchall()

        cur.execute("SELECT payfrom, money FROM balance WHERE payto = ? AND payfrom != ?", (item, item))
        receive1 = cur.fetchall()
        receive = dict(receive1)

        cur.execute("SELECT payto, money FROM balance WHERE payto != ? AND payfrom = ?", (item, item))
        pay1 = cur.fetchall()
        pay = dict(pay1)

        if bool(receive) == False:
            pay_output = pay

        elif bool(pay) == False:
            receive_output = receive

        elif bool(receive) == True and bool(pay) == True:
            same = list(set(receive.keys()).intersection(pay.keys()))

            if same:
                res = {key: receive[key] - pay.get(key, 0)
                       for key in same}
                for name in same:
                    del receive[name]
                    del pay[name]
                receive_output_pop = receive
                pay_output_pop = pay
            else:
                receive_output = receive
                pay_output = pay
        con.close()
        return render_template("friends.html", **locals())


@app.route('/activities', methods=['POST', 'GET'])
def activities():
    users = retrieveUsers()
    users = [item for t in users for item in t]

    if request.method == 'POST':
        event_name = request.form['name']
        paid_by = request.form['paidby']
        amount = request.form['amount']
        share = request.form.getlist('share')

        if amount:
            amount = float(amount)
            if len(share) != 0:
                each = float((amount / len(share)))

                con = sql.connect("friends.db")
                cur = con.cursor()

                cur.execute("UPDATE users SET paid = paid + ? WHERE username =?", (amount, paid_by))

                for item in share:
                    cur.execute("UPDATE users SET each = each + ? WHERE username =?", (each, item))
                    cur.execute("INSERT INTO events (payfrom, payto, event_name,amount) VALUES (?,?,?,?)",
                                (item, paid_by, event_name, amount))

                for user in users:
                    cur.execute("UPDATE users SET balance = paid - each WHERE username = ?", (user,))

                for item in share:
                    cur.execute("SELECT id FROM balance WHERE payfrom = ? AND payto = ?", (item, paid_by))
                    same = cur.fetchall()
                    same = [item for t in same for item in t]

                    if same:
                        for id in same:
                            cur.execute("UPDATE balance SET money = money + ? WHERE id =  ?",
                                            (each, id))
                    else:
                        cur.execute("INSERT INTO balance (payfrom, payto, money) "
                                        "VALUES (?,?,?)",
                                        (item, paid_by, each))
                con.commit()
                con.close()

        return redirect('/events')
    return render_template("activities.html", **locals())

@app.route('/events')
def events():
    con = sql.connect("friends.db")
    cur = con.cursor()
    ip_address = retrieveIP()
    cur.execute("SELECT user FROM cur_user where ip_address = ?", (ip_address,))
    user = cur.fetchall()
    user = [item for t in user for item in t]

    for item in user:
        cur.execute("SELECT event_name,payto,amount FROM events WHERE payto = ? OR payfrom = ? ORDER BY ID DESC", (item,item))
        output = cur.fetchall()
        output_event = removeDuplicates(output)
        con.close()
        return render_template("events.html", output_event = output_event)

@app.route('/logout')
def logout():
    con = sql.connect("friends.db")
    cur = con.cursor()
    ip_address = retrieveIP()
    cur.execute("DELETE FROM cur_user where ip_address = ?", (ip_address,))
    con.commit()
    con.close()
    return render_template("home.html")

def retrieveUsers():
    con = sql.connect("friends.db")
    cur = con.cursor()
    cur.execute("SELECT username FROM users")
    users = cur.fetchall()
    con.close()
    return users

def retrieveIP():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

def removeDuplicates(listofElements):
    uniqueList = []
    for elem in listofElements:
        if elem not in uniqueList:
            uniqueList.append(elem)
    return uniqueList




if __name__ == "__main__":
    app.run(debug=True)