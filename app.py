import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('revenue_cycle.db')
    c = conn.cursor()
    
    # 1. Customers
    c.execute('''CREATE TABLE IF NOT EXISTS Customers (
                    CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                    CustomerName TEXT, CreditLimit REAL, Outstanding REAL)''')
    # 2. Products
    c.execute('''CREATE TABLE IF NOT EXISTS Products (
                    ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ProductName TEXT, UnitPrice REAL)''')
    # 3. Sales Orders
    c.execute('''CREATE TABLE IF NOT EXISTS Sales_Orders (
                    SO_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Date TEXT, CustomerID INTEGER, Salesperson TEXT, 
                    SalesType TEXT, PaymentTerms TEXT, Status TEXT, TotalAmount REAL,
                    FOREIGN KEY(CustomerID) REFERENCES Customers(CustomerID))''')
    # 4. Sales Order Details
    c.execute('''CREATE TABLE IF NOT EXISTS Sales_Order_Details (
                    DetailID INTEGER PRIMARY KEY AUTOINCREMENT,
                    SO_ID INTEGER, ProductID INTEGER, Quantity INTEGER, 
                    UnitPrice REAL, Discount REAL,
                    FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID),
                    FOREIGN KEY(ProductID) REFERENCES Products(ProductID))''')
    # 5. Credit Approvals
    c.execute('''CREATE TABLE IF NOT EXISTS Credit_Approvals (
                    ApprovalID INTEGER PRIMARY KEY AUTOINCREMENT,
                    SO_ID INTEGER, CustomerID INTEGER, OrderAmount REAL, 
                    AvailableCredit REAL, Decision TEXT, ApprovedBy TEXT, Date TEXT,
                    FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID))''')
    # 6. Shippings
    c.execute('''CREATE TABLE IF NOT EXISTS Shippings (
                    ShippingID INTEGER PRIMARY KEY AUTOINCREMENT,
                    SO_ID INTEGER, ShippingDate TEXT, DeliveryAddress TEXT, 
                    ShippedBy TEXT, Status TEXT,
                    FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID))''')
    # 7. Shipping Details
    c.execute('''CREATE TABLE IF NOT EXISTS Shipping_Details (
                    ShipDetailID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ShippingID INTEGER, ProductID INTEGER, Quantity INTEGER,
                    FOREIGN KEY(ShippingID) REFERENCES Shippings(ShippingID))''')
    # 8. Invoices
    c.execute('''CREATE TABLE IF NOT EXISTS Invoices (
                    InvoiceID INTEGER PRIMARY KEY AUTOINCREMENT,
                    SO_ID INTEGER, ShippingID INTEGER, CustomerID INTEGER,
                    InvoiceDate TEXT, DueDate TEXT, InvoiceAmount REAL, Status TEXT,
                    FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID),
                    FOREIGN KEY(ShippingID) REFERENCES Shippings(ShippingID))''')
    # 9. Cash Receipts
    c.execute('''CREATE TABLE IF NOT EXISTS Cash_Receipts (
                    ReceiptID INTEGER PRIMARY KEY AUTOINCREMENT,
                    InvoiceID INTEGER, ReceiptDate TEXT, Amount REAL, 
                    PaymentMethod TEXT, BankRef TEXT, ReceivedBy TEXT,
                    FOREIGN KEY(InvoiceID) REFERENCES Invoices(InvoiceID))''')
    
    # Insert Dummy Data if empty
    c.execute("SELECT COUNT(*) FROM Customers")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO Customers (CustomerName, CreditLimit, Outstanding) VALUES ('Tech Corp', 50000, 0)")
        c.execute("INSERT INTO Customers (CustomerName, CreditLimit, Outstanding) VALUES ('Global IT', 20000, 5000)")
        c.execute("INSERT INTO Products (ProductName, UnitPrice) VALUES ('Laptop', 1000)")
        c.execute("INSERT INTO Products (ProductName, UnitPrice) VALUES ('Printer', 300)")
        c.execute("INSERT INTO Products (ProductName, UnitPrice) VALUES ('Projector', 500)")
    
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def run_query(query, params=()):
    conn = sqlite3.connect('revenue_cycle.db')
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_query(query, params=()):
    conn = sqlite3.connect('revenue_cycle.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id

# --- UI SETUP ---
st.set_page_config(page_title="PT Maju Jaya - Revenue Cycle AIS", layout="wide")
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Go to", ["Dashboard", "1. Sales Order", "2. Credit Approval", "3. Shipping", "4. Billing / Invoice", "5. Cash Receipt", "Reports"])

st.title("PT Maju Jaya - Revenue Cycle System")

# --- 1. SALES ORDER ---
if menu == "1. Sales Order":
    st.header("Create Sales Order")
    customers = run_query("SELECT * FROM Customers")
    products = run_query("SELECT * FROM Products")
    
    with st.form("so_form"):
        customer_name = st.selectbox("Customer", customers['CustomerName'])
        salesperson = st.text_input("Salesperson")
        sales_type = st.selectbox("Sales Type", ["Credit", "Cash"])
        payment_terms = st.text_input("Payment Terms (e.g., Net 30)")
        
        st.subheader("Order Details")
        product_name = st.selectbox("Product", products['ProductName'])
        qty = st.number_input("Quantity", min_value=1, value=1)
        discount = st.number_input("Discount ($)", min_value=0.0, value=0.0)
        
        submitted = st.form_submit_button("Submit Sales Order")
        if submitted:
            cust_id = customers[customers['CustomerName'] == customer_name]['CustomerID'].values[0]
            prod_id = products[products['ProductName'] == product_name]['ProductID'].values[0]
            unit_price = products[products['ProductName'] == product_name]['UnitPrice'].values[0]
            
            total_amount = (qty * unit_price) - discount
            status = "Pending Approval" if sales_type == "Credit" else "Approved"
            
            so_id = execute_query("INSERT INTO Sales_Orders (Date, CustomerID, Salesperson, SalesType, PaymentTerms, Status, TotalAmount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (datetime.now().strftime("%Y-%m-%d"), cust_id, salesperson, sales_type, payment_terms, status, total_amount))
            
            execute_query("INSERT INTO Sales_Order_Details (SO_ID, ProductID, Quantity, UnitPrice, Discount) VALUES (?, ?, ?, ?, ?)",
                          (so_id, prod_id, qty, unit_price, discount))
            st.success(f"Sales Order #{so_id} created successfully! Status: {status}")

# --- 2. CREDIT APPROVAL ---
elif menu == "2. Credit Approval":
    st.header("Credit Approval")
    pending_so = run_query("SELECT * FROM Sales_Orders WHERE Status = 'Pending Approval'")
    
    if pending_so.empty:
        st.info("No Sales Orders pending approval.")
    else:
        for index, row in pending_so.iterrows():
            st.write(f"### SO #{row['SO_ID']} - Total: ${row['TotalAmount']}")
            customer = run_query(f"SELECT * FROM Customers WHERE CustomerID = {row['CustomerID']}").iloc[0]
            
            limit = customer['CreditLimit']
            outstanding = customer['Outstanding']
            available = limit - outstanding
            order_amount = row['TotalAmount']
            
            st.write(f"**Customer:** {customer['CustomerName']} | **Credit Limit:** ${limit} | **Outstanding:** ${outstanding}")
            st.write(f"**Available Credit:** ${available} | **Order Amount:** ${order_amount}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Approve SO #{row['SO_ID']}"):
                    if available >= order_amount:
                        execute_query("UPDATE Sales_Orders SET Status = 'Approved' WHERE SO_ID = ?", (row['SO_ID'],))
                        execute_query("INSERT INTO Credit_Approvals (SO_ID, CustomerID, OrderAmount, AvailableCredit, Decision, ApprovedBy, Date) VALUES (?, ?, ?, ?, 'APPROVED', 'Admin', ?)",
                                      (row['SO_ID'], row['CustomerID'], order_amount, available, datetime.now().strftime("%Y-%m-%d")))
                        st.success(f"SO #{row['SO_ID']} APPROVED!")
                        st.rerun()
                    else:
                        st.error("Cannot approve. Order amount exceeds available credit.")
            with col2:
                if st.button(f"Reject SO #{row['SO_ID']}"):
                    execute_query("UPDATE Sales_Orders SET Status = 'Rejected' WHERE SO_ID = ?", (row['SO_ID'],))
                    execute_query("INSERT INTO Credit_Approvals (SO_ID, CustomerID, OrderAmount, AvailableCredit, Decision, ApprovedBy, Date) VALUES (?, ?, ?, ?, 'REJECTED', 'Admin', ?)",
                                      (row['SO_ID'], row['CustomerID'], order_amount, available, datetime.now().strftime("%Y-%m-%d")))
                    st.warning(f"SO #{row['SO_ID']} REJECTED!")
                    st.rerun()

# --- 3. SHIPPING ---
elif menu == "3. Shipping":
    st.header("Shipping")
    approved_so = run_query("SELECT * FROM Sales_Orders WHERE Status = 'Approved'")
    
    if approved_so.empty:
        st.info("No approved orders ready for shipping.")
    else:
        with st.form("shipping_form"):
            so_sel = st.selectbox("Select Approved SO", approved_so['SO_ID'])
            address = st.text_area("Delivery Address")
            shipped_by = st.text_input("Shipped By (Courier)")
            
            if st.form_submit_button("Process Shipping"):
                ship_id = execute_query("INSERT INTO Shippings (SO_ID, ShippingDate, DeliveryAddress, ShippedBy, Status) VALUES (?, ?, ?, ?, 'Shipped')",
                              (so_sel, datetime.now().strftime("%Y-%m-%d"), address, shipped_by))
                
                details = run_query(f"SELECT * FROM Sales_Order_Details WHERE SO_ID = {so_sel}")
                for _, det in details.iterrows():
                    execute_query("INSERT INTO Shipping_Details (ShippingID, ProductID, Quantity) VALUES (?, ?, ?)",
                                  (ship_id, det['ProductID'], det['Quantity']))
                
                execute_query("UPDATE Sales_Orders SET Status = 'Shipped' WHERE SO_ID = ?", (so_sel,))
                st.success(f"Shipping ID #{ship_id} generated for SO #{so_sel}!")

# --- 4. BILLING / INVOICE ---
elif menu == "4. Billing / Invoice":
    st.header("Billing / Invoice")
    shipped_so = run_query("SELECT * FROM Sales_Orders WHERE Status = 'Shipped'")
    
    if shipped_so.empty:
        st.info("No shipped orders ready for billing.")
    else:
        with st.form("invoice_form"):
            so_sel = st.selectbox("Select Shipped SO", shipped_so['SO_ID'])
            due_date = st.date_input("Due Date")
            
            if st.form_submit_button("Generate Invoice"):
                so_data = shipped_so[shipped_so['SO_ID'] == so_sel].iloc[0]
                shipping_data = run_query(f"SELECT * FROM Shippings WHERE SO_ID = {so_sel}").iloc[0]
                
                inv_id = execute_query("INSERT INTO Invoices (SO_ID, ShippingID, CustomerID, InvoiceDate, DueDate, InvoiceAmount, Status) VALUES (?, ?, ?, ?, ?, ?, 'UNPAID')",
                              (so_sel, int(shipping_data['ShippingID']), int(so_data['CustomerID']), datetime.now().strftime("%Y-%m-%d"), due_date.strftime("%Y-%m-%d"), so_data['TotalAmount']))
                
                execute_query("UPDATE Sales_Orders SET Status = 'Invoiced' WHERE SO_ID = ?", (so_sel,))
                execute_query("UPDATE Customers SET Outstanding = Outstanding + ? WHERE CustomerID = ?", (so_data['TotalAmount'], int(so_data['CustomerID'])))
                st.success(f"Invoice #{inv_id} generated for SO #{so_sel}!")

# --- 5. CASH RECEIPT ---
elif menu == "5. Cash Receipt":
    st.header("Cash Receipt")
    invoices = run_query("SELECT * FROM Invoices WHERE Status IN ('UNPAID', 'PARTIAL')")
    
    if invoices.empty:
        st.info("No unpaid invoices.")
    else:
        with st.form("receipt_form"):
            inv_sel = st.selectbox("Select Invoice", invoices['InvoiceID'])
            amount = st.number_input("Payment Amount", min_value=1.0)
            method = st.selectbox("Payment Method", ["Bank Transfer", "Credit Card", "Cash"])
            bank_ref = st.text_input("Bank Reference")
            
            if st.form_submit_button("Record Payment"):
                inv_data = invoices[invoices['InvoiceID'] == inv_sel].iloc[0]
                
                # Update Cash Receipt
                execute_query("INSERT INTO Cash_Receipts (InvoiceID, ReceiptDate, Amount, PaymentMethod, BankRef, ReceivedBy) VALUES (?, ?, ?, ?, ?, 'System')",
                              (inv_sel, datetime.now().strftime("%Y-%m-%d"), amount, method, bank_ref))
                
                # Check status
                paid_so_far = run_query(f"SELECT SUM(Amount) as total FROM Cash_Receipts WHERE InvoiceID = {inv_sel}").iloc[0]['total']
                
                new_status = 'PAID' if paid_so_far >= inv_data['InvoiceAmount'] else 'PARTIAL'
                execute_query("UPDATE Invoices SET Status = ? WHERE InvoiceID = ?", (new_status, inv_sel))
                execute_query("UPDATE Customers SET Outstanding = Outstanding - ? WHERE CustomerID = ?", (amount, int(inv_data['CustomerID'])))
                
                st.success(f"Payment of ${amount} recorded for Invoice #{inv_sel}. Status is now {new_status}.")

# --- REPORTS ---
elif menu == "Reports":
    st.header("Reports")
    report_type = st.selectbox("Select Report", ["Sales Order Report", "Accounts Receivable", "Sales by Product", "Customer Sales Report"])
    
    if report_type == "Sales Order Report":
        st.dataframe(run_query("SELECT SO_ID, Date, CustomerID, Salesperson, Status, TotalAmount FROM Sales_Orders"))
    elif report_type == "Accounts Receivable":
        st.dataframe(run_query("SELECT InvoiceID, CustomerID, InvoiceAmount, Status FROM Invoices"))
    elif report_type == "Sales by Product":
        query = """SELECT p.ProductName, SUM(d.Quantity) as QuantitySold, SUM(d.Quantity * d.UnitPrice) as SalesAmount 
                   FROM Sales_Order_Details d JOIN Products p ON d.ProductID = p.ProductID GROUP BY p.ProductName"""
        st.dataframe(run_query(query))
    elif report_type == "Customer Sales Report":
        query = """SELECT c.CustomerName, COUNT(s.SO_ID) as NumberOfOrders, SUM(s.TotalAmount) as TotalSales 
                   FROM Sales_Orders s JOIN Customers c ON s.CustomerID = c.CustomerID GROUP BY c.CustomerName"""
        st.dataframe(run_query(query))

# --- DASHBOARD ---
elif menu == "Dashboard":
    st.header("Revenue Cycle Dashboard")
    col1, col2, col3 = st.columns(3)
    
    total_cust = run_query("SELECT COUNT(*) as c FROM Customers").iloc[0]['c']
    total_so = run_query("SELECT COUNT(*) as c FROM Sales_Orders").iloc[0]['c']
    total_inv = run_query("SELECT COUNT(*) as c FROM Invoices").iloc[0]['c']
    total_out = run_query("SELECT SUM(Outstanding) as o FROM Customers").iloc[0]['o']
    
    col1.metric("Total Customers", total_cust)
    col2.metric("Total Sales Orders", total_so)
    col3.metric("Total Invoices", total_inv)
    st.metric("Total Outstanding Receivables", f"${total_out if total_out else 0:,.2f}")
