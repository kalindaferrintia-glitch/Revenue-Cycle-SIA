import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- UI CONFIGURATION ---
st.set_page_config(page_title="PT Maju Jaya AIS", page_icon="🏢", layout="wide")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('revenue_cycle.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Customers (CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, CustomerName TEXT, CreditLimit REAL, Outstanding REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Products (ProductID INTEGER PRIMARY KEY AUTOINCREMENT, ProductName TEXT, UnitPrice REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Sales_Orders (SO_ID INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, CustomerID INTEGER, Salesperson TEXT, SalesType TEXT, PaymentTerms TEXT, Status TEXT, TotalAmount REAL, FOREIGN KEY(CustomerID) REFERENCES Customers(CustomerID))''')
    c.execute('''CREATE TABLE IF NOT EXISTS Sales_Order_Details (DetailID INTEGER PRIMARY KEY AUTOINCREMENT, SO_ID INTEGER, ProductID INTEGER, Quantity INTEGER, UnitPrice REAL, Discount REAL, FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID), FOREIGN KEY(ProductID) REFERENCES Products(ProductID))''')
    c.execute('''CREATE TABLE IF NOT EXISTS Credit_Approvals (ApprovalID INTEGER PRIMARY KEY AUTOINCREMENT, SO_ID INTEGER, CustomerID INTEGER, OrderAmount REAL, AvailableCredit REAL, Decision TEXT, ApprovedBy TEXT, Date TEXT, FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID))''')
    c.execute('''CREATE TABLE IF NOT EXISTS Shippings (ShippingID INTEGER PRIMARY KEY AUTOINCREMENT, SO_ID INTEGER, ShippingDate TEXT, DeliveryAddress TEXT, ShippedBy TEXT, Status TEXT, FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID))''')
    c.execute('''CREATE TABLE IF NOT EXISTS Shipping_Details (ShipDetailID INTEGER PRIMARY KEY AUTOINCREMENT, ShippingID INTEGER, ProductID INTEGER, Quantity INTEGER, FOREIGN KEY(ShippingID) REFERENCES Shippings(ShippingID))''')
    c.execute('''CREATE TABLE IF NOT EXISTS Invoices (InvoiceID INTEGER PRIMARY KEY AUTOINCREMENT, SO_ID INTEGER, ShippingID INTEGER, CustomerID INTEGER, InvoiceDate TEXT, DueDate TEXT, InvoiceAmount REAL, Status TEXT, FOREIGN KEY(SO_ID) REFERENCES Sales_Orders(SO_ID), FOREIGN KEY(ShippingID) REFERENCES Shippings(ShippingID))''')
    c.execute('''CREATE TABLE IF NOT EXISTS Cash_Receipts (ReceiptID INTEGER PRIMARY KEY AUTOINCREMENT, InvoiceID INTEGER, ReceiptDate TEXT, Amount REAL, PaymentMethod TEXT, BankRef TEXT, ReceivedBy TEXT, FOREIGN KEY(InvoiceID) REFERENCES Invoices(InvoiceID))''')
    
    c.execute("SELECT COUNT(*) FROM Customers")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO Customers (CustomerName, CreditLimit, Outstanding) VALUES (?, ?, ?)", [('Tech Corp', 50000, 0), ('Global IT', 20000, 5000)])
        c.executemany("INSERT INTO Products (ProductName, UnitPrice) VALUES (?, ?)", [('Laptop', 1000), ('Printer', 300), ('Projector', 500)])
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

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🏢 PT Maju Jaya")
st.sidebar.markdown("### Revenue Cycle System")
st.sidebar.divider()
menu = st.sidebar.radio("Navigate", ["📊 Dashboard", "📝 1. Sales Order", "⚖️ 2. Credit Approval", "🚚 3. Shipping", "🧾 4. Billing / Invoice", "💵 5. Cash Receipt", "📈 Reports"])

# --- 📊 DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Revenue Cycle Dashboard")
    st.markdown("Overview of PT Maju Jaya's main business operations.")
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    total_cust = run_query("SELECT COUNT(*) as c FROM Customers").iloc[0]['c']
    total_so = run_query("SELECT COUNT(*) as c FROM Sales_Orders").iloc[0]['c']
    total_inv = run_query("SELECT COUNT(*) as c FROM Invoices").iloc[0]['c']
    total_out = run_query("SELECT SUM(Outstanding) as o FROM Customers").iloc[0]['o']
    
    col1.metric("👥 Total Customers", total_cust)
    col2.metric("📝 Sales Orders", total_so)
    col3.metric("🧾 Total Invoices", total_inv)
    col4.metric("💰 Outstanding Receivables", f"${total_out if total_out else 0:,.2f}")
    
    st.divider()
    st.subheader("Recent Sales Orders")
    st.dataframe(run_query("SELECT SO_ID, Date, CustomerID, Status, TotalAmount FROM Sales_Orders ORDER BY SO_ID DESC LIMIT 5"), use_container_width=True)

# --- 📝 1. SALES ORDER ---
elif menu == "📝 1. Sales Order":
    st.title("📝 Create Sales Order")
    customers = run_query("SELECT * FROM Customers")
    products = run_query("SELECT * FROM Products")
    
    with st.container():
        st.markdown("#### Order Information")
        with st.form("so_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                customer_name = st.selectbox("Select Customer", customers['CustomerName'])
                salesperson = st.text_input("Salesperson Name", placeholder="e.g. John Doe")
                sales_type = st.radio("Sales Type", ["Credit", "Cash"], horizontal=True)
            with col2:
                product_name = st.selectbox("Select Product", products['ProductName'])
                qty = st.number_input("Quantity", min_value=0, value=1, help="Quantity must be greater than 0")
                discount = st.number_input("Discount ($)", min_value=0.0, value=0.0)
                payment_terms = st.text_input("Payment Terms", placeholder="e.g. Net 30")
            
            st.divider()
            submitted = st.form_submit_button("Submit Sales Order", use_container_width=True)
            
            if submitted:
                # TEST 2: Quantity = 0 -> Rejected
                if qty <= 0:
                    st.error("❌ Order Rejected: Quantity must be greater than 0!")
                else:
                    cust_id = customers[customers['CustomerName'] == customer_name]['CustomerID'].values[0]
                    prod_id = products[products['ProductName'] == product_name]['ProductID'].values[0]
                    unit_price = products[products['ProductName'] == product_name]['UnitPrice'].values[0]
                    
                    total_amount = (qty * unit_price) - discount
                    status = "Pending Approval" if sales_type == "Credit" else "Approved"
                    
                    so_id = execute_query("INSERT INTO Sales_Orders (Date, CustomerID, Salesperson, SalesType, PaymentTerms, Status, TotalAmount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d"), cust_id, salesperson, sales_type, payment_terms, status, total_amount))
                    execute_query("INSERT INTO Sales_Order_Details (SO_ID, ProductID, Quantity, UnitPrice, Discount) VALUES (?, ?, ?, ?, ?)",
                                  (so_id, prod_id, qty, unit_price, discount))
                    # TEST 1: Valid customer -> SO can be created
                    st.success(f"✅ Sales Order #{so_id} created successfully! Total Amount: **${total_amount:,.2f}** | Status: **{status}**")

# --- ⚖️ 2. CREDIT APPROVAL ---
elif menu == "⚖️ 2. Credit Approval":
    st.title("⚖️ Credit Approval")
    pending_so = run_query("SELECT * FROM Sales_Orders WHERE Status = 'Pending Approval'")
    
    if pending_so.empty:
        st.info("No Sales Orders are currently pending approval.")
    else:
        for index, row in pending_so.iterrows():
            with st.expander(f"SO #{row['SO_ID']} - Action Required", expanded=True):
                customer = run_query(f"SELECT * FROM Customers WHERE CustomerID = {row['CustomerID']}").iloc[0]
                limit, outstanding, order_amount = customer['CreditLimit'], customer['Outstanding'], row['TotalAmount']
                available = limit - outstanding
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Customer", customer['CustomerName'])
                col2.metric("Available Credit", f"${available:,.2f}")
                col3.metric("Order Amount", f"${order_amount:,.2f}")
                col4.metric("Status Condition", "OK" if available >= order_amount else "EXCEEDED")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Approve Order", key=f"app_{row['SO_ID']}", use_container_width=True):
                        if available >= order_amount:
                            execute_query("UPDATE Sales_Orders SET Status = 'Approved' WHERE SO_ID = ?", (row['SO_ID'],))
                            execute_query("INSERT INTO Credit_Approvals (SO_ID, CustomerID, OrderAmount, AvailableCredit, Decision, ApprovedBy, Date) VALUES (?, ?, ?, ?, 'APPROVED', 'Admin', ?)", (row['SO_ID'], row['CustomerID'], order_amount, available, datetime.now().strftime("%Y-%m-%d")))
                            st.success(f"SO #{row['SO_ID']} APPROVED successfully!") # TEST 3
                            st.rerun()
                        else:
                            st.error("Cannot approve. Order amount exceeds available credit.")
                with c2:
                    if st.button("❌ Reject Order", key=f"rej_{row['SO_ID']}", use_container_width=True):
                        execute_query("UPDATE Sales_Orders SET Status = 'Rejected' WHERE SO_ID = ?", (row['SO_ID'],))
                        execute_query("INSERT INTO Credit_Approvals (SO_ID, CustomerID, OrderAmount, AvailableCredit, Decision, ApprovedBy, Date) VALUES (?, ?, ?, ?, 'REJECTED', 'Admin', ?)", (row['SO_ID'], row['CustomerID'], order_amount, available, datetime.now().strftime("%Y-%m-%d")))
                        st.warning(f"SO #{row['SO_ID']} REJECTED!") # TEST 4
                        st.rerun()

# --- 🚚 3. SHIPPING ---
elif menu == "🚚 3. Shipping":
    st.title("🚚 Process Shipping")
    approved_so = run_query("SELECT * FROM Sales_Orders WHERE Status = 'Approved'")
    
    if approved_so.empty:
        st.info("No approved orders ready for shipping.") # TEST 5: Shipping without approval not allowed
    else:
        with st.container():
            st.markdown("#### Select an Approved Order")
            st.dataframe(approved_so[['SO_ID', 'Date', 'TotalAmount']], use_container_width=True)
            
            with st.form("shipping_form"):
                so_sel = st.selectbox("Select SO ID to Ship", approved_so['SO_ID'])
                address = st.text_area("Delivery Address")
                shipped_by = st.text_input("Courier Name")
                
                st.divider()
                if st.form_submit_button("Confirm Shipping", use_container_width=True):
                    ship_id = execute_query("INSERT INTO Shippings (SO_ID, ShippingDate, DeliveryAddress, ShippedBy, Status) VALUES (?, ?, ?, ?, 'Shipped')", (so_sel, datetime.now().strftime("%Y-%m-%d"), address, shipped_by))
                    details = run_query(f"SELECT * FROM Sales_Order_Details WHERE SO_ID = {so_sel}")
                    for _, det in details.iterrows():
                        execute_query("INSERT INTO Shipping_Details (ShippingID, ProductID, Quantity) VALUES (?, ?, ?)", (ship_id, det['ProductID'], det['Quantity']))
                    
                    execute_query("UPDATE Sales_Orders SET Status = 'Shipped' WHERE SO_ID = ?", (so_sel,))
                    st.success(f"✅ Shipping Document #{ship_id} generated for SO #{so_sel}!")

# --- 🧾 4. BILLING / INVOICE ---
elif menu == "🧾 4. Billing / Invoice":
    st.title("🧾 Generate Invoice")
    shipped_so = run_query("SELECT * FROM Sales_Orders WHERE Status = 'Shipped'")
    
    if shipped_so.empty:
        st.info("No shipped orders ready for billing.") # TEST 6: Invoice without shipping not allowed
    else:
        with st.form("invoice_form"):
            so_sel = st.selectbox("Select Shipped SO to Bill", shipped_so['SO_ID'])
            due_date = st.date_input("Select Due Date")
            
            if st.form_submit_button("Generate Invoice", use_container_width=True):
                so_data = shipped_so[shipped_so['SO_ID'] == so_sel].iloc[0]
                shipping_data = run_query(f"SELECT * FROM Shippings WHERE SO_ID = {so_sel}").iloc[0]
                
                inv_id = execute_query("INSERT INTO Invoices (SO_ID, ShippingID, CustomerID, InvoiceDate, DueDate, InvoiceAmount, Status) VALUES (?, ?, ?, ?, ?, ?, 'UNPAID')",
                              (so_sel, int(shipping_data['ShippingID']), int(so_data['CustomerID']), datetime.now().strftime("%Y-%m-%d"), due_date.strftime("%Y-%m-%d"), so_data['TotalAmount']))
                
                execute_query("UPDATE Sales_Orders SET Status = 'Invoiced' WHERE SO_ID = ?", (so_sel,))
                execute_query("UPDATE Customers SET Outstanding = Outstanding + ? WHERE CustomerID = ?", (so_data['TotalAmount'], int(so_data['CustomerID'])))
                st.success(f"✅ Invoice #{inv_id} created for SO #{so_sel}! Amount: ${so_data['TotalAmount']:,.2f}")

# --- 💵 5. CASH RECEIPT ---
elif menu == "💵 5. Cash Receipt":
    st.title("💵 Record Cash Receipt")
    invoices = run_query("SELECT * FROM Invoices WHERE Status IN ('UNPAID', 'PARTIAL')")
    
    if invoices.empty:
        st.info("No unpaid invoices available.")
    else:
        st.dataframe(invoices[['InvoiceID', 'InvoiceAmount', 'Status']], use_container_width=True)
        with st.form("receipt_form"):
            col1, col2 = st.columns(2)
            with col1:
                inv_sel = st.selectbox("Select Invoice to Pay", invoices['InvoiceID'])
                method = st.selectbox("Payment Method", ["Bank Transfer", "Credit Card", "Cash"])
            with col2:
                amount = st.number_input("Payment Amount ($)", min_value=1.0)
                bank_ref = st.text_input("Reference / Transfer Number")
            
            st.divider()
            if st.form_submit_button("Record Payment", use_container_width=True):
                inv_data = invoices[invoices['InvoiceID'] == inv_sel].iloc[0]
                paid_so_far_df = run_query(f"SELECT SUM(Amount) as total FROM Cash_Receipts WHERE InvoiceID = {inv_sel}")
                paid_so_far = paid_so_far_df.iloc[0]['total'] if not pd.isna(paid_so_far_df.iloc[0]['total']) else 0
                remaining_balance = inv_data['InvoiceAmount'] - paid_so_far
                
                # TEST 9: Payment exceeds invoice -> Warning/Rejected
                if amount > remaining_balance:
                    st.warning(f"⚠️ Payment Rejected! Amount (${amount:,.2f}) exceeds the remaining balance (${remaining_balance:,.2f}).")
                else:
                    execute_query("INSERT INTO Cash_Receipts (InvoiceID, ReceiptDate, Amount, PaymentMethod, BankRef, ReceivedBy) VALUES (?, ?, ?, ?, ?, 'System')",
                                  (inv_sel, datetime.now().strftime("%Y-%m-%d"), amount, method, bank_ref))
                    
                    new_total_paid = paid_so_far + amount
                    new_status = 'PAID' if new_total_paid >= inv_data['InvoiceAmount'] else 'PARTIAL' # TEST 7 & 8
                    
                    execute_query("UPDATE Invoices SET Status = ? WHERE InvoiceID = ?", (new_status, inv_sel))
                    execute_query("UPDATE Customers SET Outstanding = Outstanding - ? WHERE CustomerID = ?", (amount, int(inv_data['CustomerID'])))
                    
                    st.success(f"✅ Payment of ${amount:,.2f} recorded! Invoice #{inv_sel} status updated to: **{new_status}**")

# --- 📈 REPORTS ---
elif menu == "📈 Reports":
    st.title("📈 System Reports")
    # TEST 10: Report Data matches transactions
    report_type = st.selectbox("Select Report Category", ["Sales Order Report", "Accounts Receivable", "Sales by Product", "Customer Sales Report"])
    
    with st.container():
        st.markdown(f"### {report_type}")
        if report_type == "Sales Order Report":
            st.dataframe(run_query("SELECT SO_ID, Date, CustomerID, Salesperson, Status, TotalAmount FROM Sales_Orders"), use_container_width=True)
        elif report_type == "Accounts Receivable":
            st.dataframe(run_query("SELECT InvoiceID, CustomerID, InvoiceAmount, Status FROM Invoices"), use_container_width=True)
        elif report_type == "Sales by Product":
            query = """SELECT p.ProductName, SUM(d.Quantity) as QuantitySold, SUM(d.Quantity * d.UnitPrice) as SalesAmount FROM Sales_Order_Details d JOIN Products p ON d.ProductID = p.ProductID GROUP BY p.ProductName"""
            st.dataframe(run_query(query), use_container_width=True)
        elif report_type == "Customer Sales Report":
            query = """SELECT c.CustomerName, COUNT(s.SO_ID) as NumberOfOrders, SUM(s.TotalAmount) as TotalSales FROM Sales_Orders s JOIN Customers c ON s.CustomerID = c.CustomerID GROUP BY c.CustomerName"""
            st.dataframe(run_query(query), use_container_width=True)
