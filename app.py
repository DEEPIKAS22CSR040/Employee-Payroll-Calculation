from flask import Flask, render_template, request, redirect, url_for, session,flash
import psycopg2
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = 'xyz'

# Database connection function
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="Deepika@2004",
        database="employee",
        port=5432,
    )
    return conn

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        employee_id = request.form['employee_id'] if role == 'employee' else None

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the email already exists
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return "User with this email already exists."

        # Validate employee_id for 'employee' role
        if role == 'employee':
            cursor.execute("SELECT employee_id FROM employees WHERE employee_id = %s", (employee_id,))
            if not cursor.fetchone():
                return f"Employee ID {employee_id} does not exist."

        # Insert new user into the database
        try:
            cursor.execute("""
                INSERT INTO users (email, password, role, employee_id)
                VALUES (%s, %s, %s, %s)
            """, (email, password, role, employee_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"Error: {str(e)}"
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check user credentials in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, password, role, employee_id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        # Check if user exists and compare the entered password
        if user and user[1] == password:
            session['user_id'] = user[0]
            session['role'] = user[2]
            session['employee_id'] = user[3]

            if user[2] == 'admin':
                return render_template('admin_dashboard.html')
            else:
                return redirect(url_for('view_employee_details'))
        else:
            return "Invalid credentials"
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/employee/leave_requests', methods=['GET'])
def view_leave_requests():
    if 'employee_id' not in session:
        return redirect(url_for('login'))

    employee_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch leave requests for the logged-in employee
    cursor.execute("""
        SELECT request_id, start_date, end_date, reason, status 
        FROM leave_requests 
        WHERE employee_id = %s
    """, (employee_id,))
    leave_requests = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_leave_requests.html', leave_requests=leave_requests)



@app.route('/admin/employees', methods=['GET', 'POST'])
def view_employees():
    if session.get('role') != 'admin':
        return "Unauthorized access"

    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        search_query = request.form['search_query']
        cursor.execute("""
                       SELECT * FROM employees WHERE name ILIKE %s OR position ILIKE %s""",
                       (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("SELECT * FROM employees")
    
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('view_employees.html', employees=employees)

@app.route('/employee/details', methods=['GET'])
def view_employee_details():
    if 'employee_id' not in session:
        return redirect(url_for('login'))

    employee_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch employee details
    cursor.execute("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    
    cursor.close()
    conn.close()

    return render_template('view_employee_details.html', employee=employee)

@app.route('/employee/leave_request', methods=['GET', 'POST'])
def leave_request():
    if 'employee_id' not in session:
        return redirect(url_for('login'))

    employee_id = session['employee_id']  # Get employee ID from session
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        reason = request.form['reason']

        # Insert the leave request into the database
        cursor.execute("""
            INSERT INTO leave_requests (employee_id, start_date, end_date, reason, status)
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (employee_id, start_date, end_date, reason))
        conn.commit()

        # Flash a success message
        flash("Leave request submitted successfully!", "success")
        
        cursor.close()
        conn.close()
        return redirect(url_for('view_leave_requests'))  # Redirect to view leave requests

    cursor.close()
    conn.close()
    return render_template('leave_request.html')


# Update the attendance view to show only the logged-in employee's records
@app.route('/employee/attendance', methods=['GET'])
def view_employee_attendance():
    if 'employee_id' not in session:
        return redirect(url_for('login'))

    employee_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.attendance_id, a.attendance_date, a.status, a.remarks
        FROM attendance a
        WHERE a.employee_id = %s
    """, (employee_id,))
    attendance_records = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_employee_attendance.html', attendance_records=attendance_records)


@app.route('/admin/employees/create', methods=['GET', 'POST'])
def create_employee():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        position = request.form['position']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO employees (employee_id, name, email, phone, position, salary) VALUES (%s, %s, %s, %s, %s, NULL)""",
                       (employee_id, name, email, phone, position))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_employees'))
    return render_template('create_employee.html')

@app.route('/admin/employees/update/<employee_id>', methods=['GET', 'POST'])
def update_employee(employee_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        position = request.form['position']
        
        cursor.execute("""
                       UPDATE employees SET name=%s, email=%s, phone=%s, position=%s WHERE employee_id=%s""",
                       (name, email, phone, position, employee_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_employees'))
    cursor.close()
    conn.close()
    return render_template('update_employee.html', employee=employee)

@app.route('/admin/employees/delete/<employee_id>', methods=['GET', 'POST'])
def delete_employee(employee_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('view_employees'))

@app.route('/admin/attendance', methods=['GET', 'POST'])
def mark_attendance():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        attendance_date = request.form['attendance_date']
        status = request.form['status']
        remarks = request.form.get('remarks', '')  

        cursor.execute("""
            INSERT INTO attendance (employee_id, attendance_date, status, remarks)
            VALUES (%s, %s, %s, %s)
        """, (employee_id, attendance_date, status, remarks))
        
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_attendance'))

    cursor.execute("SELECT employee_id, name FROM employees")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('mark_attendance.html', employees=employees)

@app.route('/admin/attendance/view', methods=['GET'])
def view_attendance():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.attendance_id, e.name, a.attendance_date, a.status, a.remarks
        FROM attendance a
        JOIN employees e ON a.employee_id = e.employee_id
    """)
    attendance_records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('view_attendance.html', attendance_records=attendance_records)

@app.route('/admin/leave_requests', methods=['GET', 'POST'])
def manage_leave_requests():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        request_id = request.form['request_id']
        action = request.form['action']  
        
        
        new_status = 'Approved' if action == 'approve' else 'Rejected'
        cursor.execute("UPDATE leave_requests SET status = %s WHERE request_id = %s", (new_status, request_id))
        conn.commit()

    cursor.execute("SELECT * FROM leave_requests")
    leave_requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('manage_leave_requests.html', leave_requests=leave_requests)

@app.route('/admin/salary/calculate', methods=['GET', 'POST'])
def calculate_employee_salary():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the employee's position from the employees table
        cursor.execute("SELECT position FROM employees WHERE employee_id = %s", (employee_id,))
        employee = cursor.fetchone()

        if employee:
            position = employee[0]

            # Fetch the base salary based on the role_name (instead of position)
            cursor.execute("SELECT base_salary FROM roles WHERE role_name = %s", (position,))
            salary_data = cursor.fetchone()

            if salary_data:
                base_salary = salary_data[0]
                
                # Fetch leaves taken by the employee
                cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE employee_id = %s AND status = 'Approved'", (employee_id,))
                leaves_taken = cursor.fetchone()[0]

                # Define deduction per leave
                deduction_per_leave = 50  # Example value for deduction

                # Calculate final salary
                final_salary = base_salary - (leaves_taken * deduction_per_leave)

                # Update the salary in the employees table
                cursor.execute("UPDATE employees SET salary = %s WHERE employee_id = %s", (final_salary, employee_id))
                conn.commit()

                flash(f"Salary calculated successfully! New salary: {final_salary}", "success")
            else:
                flash(f"Error: Role not found for the position '{position}'.", "danger")
        else:
            flash("Error: Employee not found.", "danger")

        cursor.close()
        conn.close()
        return redirect(url_for('view_employees'))

    # Get the list of employees for the dropdown
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id, name FROM employees")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('calculate_salary.html', employees=employees)




if __name__ == '__main__':
    app.run(debug=True)
