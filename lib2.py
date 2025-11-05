import mysql.connector
import getpass
import pandas as pd
from datetime import datetime, timedelta

conn = mysql.connector.connect(host = "localhost", user = "root", password = "youARE@100%", database = "test")
cursor = conn.cursor()
print("Connected to libary database successfully!")

table_users = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(100) NOT NULL,
    role ENUM('admin', 'member') DEFAULT 'member'
);
"""

table_books="""
CREATE TABLE IF NOT EXISTS books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100) NOT NULL,
    genre VARCHAR(50),
    price DECIMAL(10, 2),
    stock_count INT DEFAULT 1
);
"""

table_transactions = """
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    book_id INT,
    issue_date DATE,
    due_date DATE,
    return_date DATE,
    fine FLOAT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id)
);
"""
def adding_tables():
    cursor = conn.cursor()
    cursor.execute(table_users)
    cursor.execute(table_books)
    cursor.execute(table_transactions)


    
    conn.commit()
    cursor.close()
    # DO NOT close conn here — keep it open for program lifetime



# USER REGISTRATION
def registration():
    name = input("Name: ")
    phone = input("Phone: ")
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    role = input("Role (admin/member): ")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)", 
            (name, email, password, role if role=='admin' else 'member')
        )
        conn.commit()
        print("Registration successful!")
    except mysql.connector.errors.IntegrityError:
        print("Email already registered.")
    cursor.close()
    # DO NOT close conn here

#USER LOGIN
def login():
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, role FROM users WHERE email=%s AND password=%s", (email, password)
    )
    user = cursor.fetchone()
    cursor.close()
    # DO NOT close conn here
    if user:
        print("Login successful!")
        return {'id': user[0], 'name': user[1], 'role': user[2]}
    else:
        print("Login failed; check credentials.")
        return None

#ADDING BOOKS 
def add_book():
    title = input("Book Title: ")
    author = input("Author: ")
    genre = input("Genre: ")
    price = float(input("Price: "))
    stock = int(input("Stock Count: "))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, genre, price, stock_count) VALUES (%s, %s, %s, %s, %s)", 
        (title, author, genre, price, stock)
    )
    conn.commit()
    print("Book added.")
    cursor.close()
    # DO NOT close conn here

#PRINT LIST OF BOOKS
def list_books():
    df = pd.read_sql("SELECT id, title, author, genre, stock_count FROM books", conn)
    if df.empty:
        print("No books available.")
    else:
        print("Books Available:")
        print(df.to_string(index=False))
    # DO NOT close conn here

#BORROW BOOK
def borrow_book(user_id):
    df = pd.read_sql("SELECT id, title, author, genre, stock_count FROM books", conn)
    print("\nBooks Available for Borrowing:")
    print(df.to_string(index=False))
    try:
        book_id = int(input("Enter Book ID to borrow: "))
        book_row = df.loc[df['id'] == book_id]
        if book_row.empty:
            print("Invalid Book ID.")
            return
        stock = book_row.iloc[0]['stock_count']
        if stock <= 0:
            print("Book not available.")
            return
        today = datetime.now().date()
        due = today + timedelta(days=14)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (user_id, book_id, issue_date, due_date) VALUES (%s, %s, %s, %s)",
            (user_id, book_id, today, due)
        )
        cursor.execute(
            "UPDATE books SET stock_count = stock_count - 1 WHERE id=%s", (book_id,)
        )
        conn.commit()
        print(f"Book borrowed; due date is {due}.")
        cursor.close()
    except Exception as e:
        print("Borrow failed.", e)
    # DO NOT close conn here

def return_book(user_id):
    df = pd.read_sql(
        "SELECT t.id AS transaction_id, b.title, t.due_date, t.return_date "
        "FROM transactions t JOIN books b ON t.book_id=b.id "
        "WHERE t.user_id=%s AND t.return_date IS NULL",
        conn,
        params=(user_id,)
    )
    if df.empty:
        print("You have no borrowed books to return.")
        return
    print("\nBorrowed Books:")
    print(df.to_string(index=False))
    try:
        tid = int(input("Enter transaction_id to return: "))
        if tid not in df['transaction_id'].values:
            print("Invalid transaction id.")
            return
        selected_row = df[df['transaction_id'] == tid].iloc[0]
        return_date = datetime.now().date()
        fine = 0
        due_date = selected_row['due_date']
        # normalize due_date if it's a Timestamp
        if pd.notnull(due_date):
            due_date = pd.to_datetime(due_date).date()
            if return_date > due_date:
                days_late = (return_date - due_date).days
                fine = days_late * 5  # Rs. 5 per late day
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET return_date=%s, fine=%s WHERE id=%s", 
            (return_date, fine, tid)
        )
        cursor.execute(
            "UPDATE books SET stock_count = stock_count + 1 WHERE id = (SELECT book_id FROM transactions WHERE id=%s)", 
            (tid,)
        )
        conn.commit()
        print(f"Book returned. Fine: {fine}")
        cursor.close()
    except Exception as e:
        print("Return failed.", e)
    # DO NOT close conn here

def view_transactions(user_id):
    df = pd.read_sql(
        "SELECT b.title, t.issue_date, t.due_date, t.return_date, t.fine "
        "FROM transactions t JOIN books b ON t.book_id=b.id WHERE t.user_id=%s",
        conn,
        params=(user_id,)
    )
    print("\nYour Transactions:")
    if df.empty:
        print("No transactions.")
    else:
        print(df.to_string(index=False))
        export = input("Export as CSV? (y/n): ")
        if export.strip().lower() == "y":
            filename = f"user_{user_id}_transactions.csv"
            df.to_csv(filename, index=False)
            print(f"Exported to {filename}.")
    # DO NOT close conn here

def admin_view_all_transactions():
    df = pd.read_sql(
        "SELECT u.name, b.title, t.issue_date, t.due_date, t.return_date, t.fine "
        "FROM transactions t JOIN users u ON t.user_id=u.id JOIN books b ON t.book_id=b.id",
        conn
    )
    print("\nAll Transactions:")
    if df.empty:
        print("No transactions.")
    else:
        print(df.to_string(index=False))
        export = input("Export as CSV? (y/n): ")
        if export.strip().lower() == "y":
            filename = "all_transactions.csv"
            df.to_csv(filename, index=False)
            print(f"Exported to {filename}.")
    # DO NOT close conn here

#UPDATE 
def update_profile(user):
    print("\n--- Update Profile ---")
    print("1. Update Name")
    print("2. Update Phone")
    print("3. Update Email")
    print("4. Update Password")
    print("5. Back to Menu")
    choice = input("Choose: ").strip()
    cursor = conn.cursor()
    if choice == '1':
        new_name = input("Enter new name: ")
        cursor.execute("UPDATE users SET name=%s WHERE id=%s", (new_name, user['id']))
        print("Name updated.")
    elif choice == '2':
        new_phone = input("Enter new phone: ")
        cursor.execute("UPDATE users SET phone=%s WHERE id=%s", (new_phone, user['id']))
        print("Phone updated.")
    elif choice == '3':
        new_email = input("Enter new email: ")
        cursor.execute("UPDATE users SET email=%s WHERE id=%s", (new_email, user['id']))
        print("Email updated.")
    elif choice == '4':
        new_password = getpass.getpass("Enter new password: ")
        cursor.execute("UPDATE users SET password=%s WHERE id=%s", (new_password, user['id']))
        print("Password updated.")
    elif choice == '5':
        pass
    else:
        print("Invalid choice.")
    conn.commit()
    cursor.close()

#SEARCH
def search_books():
    print("\n--- Book Search ---")
    print("1. Search by Title")
    print("2. Search by Author")
    print("3. Search by Genre")
    choice = input("Choose (1/2/3): ").strip()
    
    col_map = {'1': 'title', '2': 'author', '3': 'genre'}
    col = col_map.get(choice, 'title')
    keyword = input(f"Enter {col.capitalize()} keyword: ").strip()
    
    # Use SQL LIKE for fuzzy matching
    df = pd.read_sql(
        f"SELECT id, title, author, genre, price, stock_count FROM books WHERE {col} LIKE %s",
        conn,
        params=(f'%{keyword}%',)
    )
    if df.empty:
        print("No matching books found.")
    else:
        print("\nMatching Books:")
        print(df.to_string(index=False))

#DELETE BOOK (ADMIN ONLY)
def delete_book():
    list_books()  # Show all books
    try:
        book_id = int(input("Enter the Book ID to delete: "))
    except ValueError:
        print("Invalid input.")
        return
    cursor = conn.cursor()
    # First check if book exists
    cursor.execute("SELECT * FROM books WHERE id=%s", (book_id,))
    book = cursor.fetchone()
    if not book:
        print("Book not found.")
        cursor.close()
        return
    # Optional: Confirm deletion
    confirm = input(f"Are you sure you want to delete '{book[1]}'? (y/n): ")
    if confirm.lower() != 'y':
        print("Deletion cancelled.")
        cursor.close()
        return
    # Delete book
    cursor.execute("DELETE FROM books WHERE id=%s", (book_id,))
    conn.commit()
    print("Book deleted successfully.")
    cursor.close()

#update book details (ADMIN ONLY)
def update_book():
    list_books()  # Show all books
    try:
        book_id = int(input("Enter the Book ID to update: "))
    except ValueError:
        print("Invalid input.")
        return
    cursor = conn.cursor()
    # Check if book exists
    cursor.execute("SELECT * FROM books WHERE id=%s", (book_id,))
    book = cursor.fetchone()
    if not book:
        print("Book not found.")
        cursor.close()
        return

    print("What do you want to update?")
    print("1. Title\n2. Author\n3. Genre\n4. Price\n5. Stock Count\n6. Cancel")
    choice = input("Choose option: ")
    update_query = None
    update_val = None

    if choice == '1':
        new_title = input("Enter new title: ")
        update_query = "UPDATE books SET title=%s WHERE id=%s"
        update_val = (new_title, book_id)
    elif choice == '2':
        new_author = input("Enter new author: ")
        update_query = "UPDATE books SET author=%s WHERE id=%s"
        update_val = (new_author, book_id)
    elif choice == '3':
        new_genre = input("Enter new genre: ")
        update_query = "UPDATE books SET genre=%s WHERE id=%s"
        update_val = (new_genre, book_id)
    elif choice == '4':
        try:
            new_price = float(input("Enter new price: "))
            update_query = "UPDATE books SET price=%s WHERE id=%s"
            update_val = (new_price, book_id)
        except ValueError:
            print("Invalid price.")
            cursor.close()
            return
    elif choice == '5':
        try:
            new_stock = int(input("Enter new stock count: "))
            update_query = "UPDATE books SET stock_count=%s WHERE id=%s"
            update_val = (new_stock, book_id)
        except ValueError:
            print("Invalid stock count.")
            cursor.close()
            return
    elif choice == '6':
        cursor.close()
        print("Update cancelled.")
        return
    else:
        cursor.close()
        print("Invalid choice.")
        return

    cursor.execute(update_query, update_val)
    conn.commit()
    cursor.close()
    print("Book updated successfully.")

# MAIN MENU
def show_menu(user):
    while True:
        print("\n--- Library Menu ---")
        if user['role'] == 'admin':
            print("1. Add Book")
            print("2. List Books")
            print("3. View All Transactions")
            print("4. Search Books")
            print("5. Delete Book")
            print("6. Update Book")
            print("7. Logout")
            choice = input("Choose: ")
            if choice == '1': add_book()
            elif choice == '2': list_books()
            elif choice == '3': admin_view_all_transactions()
            elif choice == '4': search_books()
            elif choice == '5': delete_book()
            elif choice == '6': update_book()
            elif choice == '7': break
            else: print("Invalid.")
        else:
            print("1. List Books")
            print("2. Borrow Book")
            print("3. Return Book")
            print("4. My Transactions")
            print("5. Update Profile")
            print("6. Search Books")
            print("7. Logout")
            choice = input("Choose: ")
            if choice == '1': list_books()
            elif choice == '2': borrow_book(user['id'])
            elif choice == '3': return_book(user['id'])
            elif choice == '4': view_transactions(user['id'])
            elif choice == '5': update_profile(user)
            elif choice == '6': search_books()
            elif choice == '7': break
            else: print("Invalid.")

# BOOTSTRAP
def main():
    print("Initializing DB...")
    adding_tables()
    try:
        while True:
            print("\n--- Library Management System ---")
            print("1. Register")
            print("2. Login")
            print("3. Exit")
            action = input("Choose: ")
            if action == '1':
                registration()
            elif action == '2':
                user = login()
                if user:
                    show_menu(user)
            elif action == '3':
                print("Exiting....Goodbye!")
                break
            else:
                print("Invalid.")
    finally:
        try:
            if conn.is_connected():
                conn.close()
                print("Database connection closed.")
        except Exception:
            # fallback close
            try:
                conn.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()