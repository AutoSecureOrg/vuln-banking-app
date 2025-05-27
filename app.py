from flask import Flask, session,request, render_template, redirect, url_for
import sqlite3
import os
import subprocess


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong, unique secret key

# Database setup
DATABASE = "mock_database.db"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password TEXT,
                balance REAL
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                comment TEXT
            );

            INSERT OR IGNORE INTO users (username, password, balance) VALUES
            ('admin', 'password123', 10000.00),
            ('user1', 'pass1', 5000.00),
            ('user2', 'pass2', 3000.00);
                           
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                sender TEXT,
                recipient TEXT,
                amount REAL
            );
        ''')

init_db()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get user input from the form
        username = request.form['username']
        password = request.form['password']
        balance = request.form.get('balance', 0)  # Default balance is 0 if not provided

        # SQL Injection vulnerability (do NOT use in production)
        query = f"INSERT INTO users (username, password, balance) VALUES ('{username}', '{password}', {balance})"

        with sqlite3.connect(DATABASE) as conn:
            try:
                conn.execute(query)
                conn.commit()
                return redirect(url_for('login'))  # Redirect to login page after signup
            except Exception as e:
                return f"Error: {e}", 500

    return render_template('signup.html')




@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # SQL query to validate user (vulnerable for testing purposes)
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        print("Query: ----- ", query)
        with sqlite3.connect(DATABASE) as conn:
            user = conn.execute(query).fetchone()
            print("User: ----- ", user)

        if user:
            # Store the username in the session
            session['username'] = user[1]  # Assuming user[1] is the username
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials", 401
    return render_template('index.html')


from flask import session, redirect, url_for


@app.route('/logout')
def logout():
    # Clear session data (if any)
    session.clear()
    return redirect(url_for('login'))  # Redirect to index/login page

@app.route('/dashboard')
def dashboard():
    # Check if the user is logged in
    if 'username' in session:
        username = session['username']

        # Fetch user details from the database
        with sqlite3.connect(DATABASE) as conn:
            query = f"SELECT * FROM users WHERE username = '{username}'"
            user = conn.execute(query).fetchone()

        if user:
            return render_template('dashboard.html', user=user)
        else:
            return "User not found", 404
    else:
        return redirect(url_for(''))  # Redirect to login if not logged in







@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        print("Received Form Data:", request.form)  # Debugging line

        sender = session['username']
        recipient = request.form.get('account', '').strip()
        amount = request.form.get('amount', '').strip()

        print("Sender :", sender)
        print("Amount :", amount)
        print("Recipient :", recipient)
        
        if not recipient or not amount:
            return "Missing recipient or amount", 400
        
        try:
            amount = float(amount)
        except ValueError:
            return "Invalid amount", 400
        
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            sender_query = "SELECT balance FROM users WHERE username = ?"
            sender_balance = cursor.execute(sender_query, (sender,)).fetchone()
            recipient_query = "SELECT username FROM users WHERE username = ?"
            recipient_exists = cursor.execute(recipient_query, (recipient,)).fetchone()
            
            if not sender_balance:
                return "Sender not found", 404
            if not recipient_exists:
                return "Recipient not found", 404
            if sender_balance[0] < amount:
                return "Insufficient balance", 400
            
            cursor.execute("UPDATE users SET balance = balance - ? WHERE username = ?", (amount, sender))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (amount, recipient))
            cursor.execute("INSERT INTO transactions (sender, recipient, amount) VALUES (?, ?, ?)", (sender, recipient, amount))
            conn.commit()
        
        return redirect(url_for('receipt', sender=sender, recipient=recipient, amount=amount))
    
    return render_template('transfer.html')

@app.route('/view_logs', methods=['GET', 'POST'])
def view_logs():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    recipient = request.form.get('filter', '').strip() if request.method == 'POST' else request.args.get('recipient', '').strip()
    transactions = []
    
    if recipient:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            # SQL Injection vulnerability: unsanitized query
            query = f"SELECT sender, recipient, amount FROM transactions WHERE recipient = '{recipient}'"
            cursor.execute(query)
            transactions = cursor.fetchall()
    
    return render_template("view_logs.html", transactions=transactions, recipient=recipient)


@app.route('/confirm_transfer', methods=['POST'])
def confirm_transfer():
    sender_username = request.form['sender_username']
    recipient_username = request.form['recipient_username']
    amount = request.form['amount']  # Still a string, no validation applied

    # Vulnerable SQL queries for updating balances
    with sqlite3.connect(DATABASE) as conn:
        # Subtract from sender's balance (SQL Injection vulnerability)
        conn.execute(f"UPDATE users SET balance = balance - {amount} WHERE username = '{sender_username}'")

        # Add to recipient's balance (SQL Injection vulnerability)
        conn.execute(f"UPDATE users SET balance = balance + {amount} WHERE username = '{recipient_username}'")
        conn.commit()

    # Redirect to receipt page
    return redirect(url_for('receipt', sender=sender_username, recipient=recipient_username, amount=amount))

@app.route('/receipt')
def receipt():
    sender_username = request.args.get('sender')
    recipient_username = request.args.get('recipient')
    amount = request.args.get('amount')

    return render_template('receipt.html', sender=sender_username, recipient=recipient_username, amount=amount)


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'username' not in session:  # Ensure user is logged in
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if request.method == 'POST':
        comment = request.form['comment']  # User input (vulnerable)

        return render_template('feedback.html', comment=comment)  # Display feedback once

    return render_template('feedback.html', comment=None)  # Reset on refresh


'''def feedback():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        feedback = request.form['feedback']

        # Pass user input directly to the template (vulnerable to XSS and HTML injection)
        return render_template('feedback.html', name=name, feedback=feedback)
    
    return render_template('feedback.html', name=None, feedback=None)'''



if __name__ == '__main__':
    app.run(debug=True)
