import streamlit as st
import sqlite3
import datetime
import pandas as pd
import plotly.express as px


st.set_page_config(
    page_title="Smart Parking System",
    page_icon="🚘",
    layout="wide"
)


# ================= DATABASE =================

conn = sqlite3.connect("parking.db", check_same_thread=False)
cursor = conn.cursor()


def create_database():

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slots(
        slot TEXT PRIMARY KEY,
        status TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT UNIQUE,
        owner TEXT,
        vehicle_type TEXT,
        slot TEXT,
        entry_time TEXT,
        exit_time TEXT,
        hours INTEGER,
        fee INTEGER,
        status TEXT
    )
    """)


    cursor.execute(
        "SELECT * FROM users"
    )

    if cursor.fetchone() is None:

        cursor.execute(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            ("admin","1234","Administrator")
        )

        cursor.execute(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            ("staff","1234","Parking Staff")
        )


    cursor.execute(
        "SELECT COUNT(*) FROM slots"
    )

    count = cursor.fetchone()[0]


    if count == 0:

        for zone in ["A","B","C","D","E"]:

            for i in range(1,11):

                cursor.execute(
                "INSERT INTO slots VALUES(?,?)",
                (f"{zone}-{i:02d}","Free")
                )


    conn.commit()



create_database()



# ================= LOGIN =================


if "login" not in st.session_state:
    st.session_state.login=False


if not st.session_state.login:


    st.title("🔐 Smart Parking Login")


    username=st.text_input("Username")
    password=st.text_input(
        "Password",
        type="password"
    )


    if st.button("Login"):

        cursor.execute(
        """
        SELECT role FROM users
        WHERE username=? AND password=?
        """,
        (username,password)
        )


        result=cursor.fetchone()


        if result:

            st.session_state.login=True
            st.session_state.role=result[0]
            st.rerun()

        else:

            st.error("Wrong username or password")


    st.stop()



# ================= HEADER =================


st.title("🚘 Advanced Smart Parking System")

st.sidebar.success(
    st.session_state.role
)



menu=[
"Dashboard",
"Vehicle Entry",
"Vehicle Exit",
"Reports"
]


choice=st.sidebar.selectbox(
    "Select Option",
    menu
)



# ================= DASHBOARD =================


if choice=="Dashboard":


    st.subheader("Live Parking Status")


    data=pd.read_sql(
        "SELECT * FROM slots",
        conn
    )


    free=len(
        data[data.status=="Free"]
    )

    occupied=50-free


    c1,c2,c3=st.columns(3)


    c1.metric(
        "Total Slots",
        50
    )


    c2.metric(
        "Free",
        free
    )


    c3.metric(
        "Occupied",
        occupied
    )


    fig=px.pie(
        data,
        names="status",
        title="Parking Occupancy"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    for zone in ["A","B","C","D","E"]:

        st.write(
        f"### Zone {zone}"
        )

        temp=data[
        data.slot.str.startswith(zone)
        ]

        st.dataframe(
            temp,
            use_container_width=True
        )



# ================= VEHICLE ENTRY =================


if choice=="Vehicle Entry":


    st.subheader("Vehicle Check-In")


    number=st.text_input(
        "Vehicle Number"
    )

    owner=st.text_input(
        "Owner Name"
    )


    vtype=st.selectbox(
        "Vehicle Type",
        ["Car","Bike","Truck"]
    )


    slots=pd.read_sql(
        "SELECT * FROM slots WHERE status='Free'",
        conn
    )


    slot=st.selectbox(
        "Select Slot",
        slots.slot.tolist()
    )


    if st.button("Park Vehicle"):


        cursor.execute(
        "SELECT * FROM vehicles WHERE number=? AND status='Active'",
        (number,)
        )


        if cursor.fetchone():

            st.error(
            "Vehicle already parked"
            )

        else:


            now=str(
            datetime.datetime.now()
            )


            cursor.execute(
            """
            INSERT INTO vehicles
            (number,owner,vehicle_type,slot,entry_time,status)
            VALUES(?,?,?,?,?,?)
            """,
            (
            number,
            owner,
            vtype,
            slot,
            now,
            "Active"
            )
            )


            cursor.execute(
            """
            UPDATE slots
            SET status='Occupied'
            WHERE slot=?
            """,
            (slot,)
            )


            conn.commit()


            st.success(
            f"{number} parked at {slot}"
            )



# ================= EXIT =================


if choice=="Vehicle Exit":


    st.subheader("Vehicle Check-Out")


    cars=pd.read_sql(
    """
    SELECT * FROM vehicles
    WHERE status='Active'
    """,
    conn
    )


    if len(cars)==0:

        st.info(
        "No active vehicles"
        )

    else:


        vehicle=st.selectbox(
        "Select Vehicle",
        cars.number.tolist()
        )


        if st.button("Generate Bill"):


            row=cars[
            cars.number==vehicle
            ].iloc[0]


            exit_time=datetime.datetime.now()


            entry=datetime.datetime.fromisoformat(
            row.entry_time
            )


            hours=max(
            1,
            int(
            (exit_time-entry).seconds/3600
            )
            )


            fee=hours*50


            cursor.execute(
            """
            UPDATE vehicles
            SET exit_time=?,
            hours=?,
            fee=?,
            status='Completed'
            WHERE number=?
            """,
            (
            str(exit_time),
            hours,
            fee,
            vehicle
            )
            )


            cursor.execute(
            """
            UPDATE slots
            SET status='Free'
            WHERE slot=?
            """,
            (row.slot,)
            )


            conn.commit()


            st.success(
            f"Total Bill: Rs {fee}"
            )



# ================= REPORT =================


if choice=="Reports":


    st.subheader("Admin Reports")


    df=pd.read_sql(
    "SELECT * FROM vehicles",
    conn
    )


    st.dataframe(
        df,
        use_container_width=True
    )


    csv=df.to_csv(
        index=False
    )


    st.download_button(
    "Download Report",
    csv,
    "parking_report.csv"
    )
    # ================= EXTRA FUNCTIONS =================


def generate_receipt(vehicle):

    df=pd.read_sql(
    """
    SELECT * FROM vehicles
    WHERE number=?
    """,
    conn,
    params=(vehicle,)
    )


    if len(df)==0:
        return None


    row=df.iloc[0]


    receipt=f"""

====================================
        SMART PARKING SYSTEM
             RECEIPT
====================================

Vehicle No   : {row.number}
Owner        : {row.owner}
Type         : {row.vehicle_type}

Parking Slot : {row.slot}

Entry Time   : {row.entry_time}
Exit Time    : {row.exit_time}

Total Hours  : {row.hours}

Parking Fee  : Rs {row.fee}

====================================
Thank you for using our system 🚘
====================================

"""


    return receipt



# ================= SEARCH MODULE =================


if choice=="Dashboard":


    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "🔎 Vehicle Search"
    )


    search=st.sidebar.text_input(
        "Enter Vehicle Number"
    )


    if search:


        result=pd.read_sql(
        """
        SELECT *
        FROM vehicles
        WHERE number LIKE ?
        """,
        conn,
        params=(f"%{search}%",)
        )


        st.sidebar.dataframe(
            result,
            use_container_width=True
        )



# ================= ADVANCED EXIT =================


if choice=="Vehicle Exit":


    st.markdown("---")


    st.subheader(
        "🧾 Generate Customer Receipt"
    )


    completed=pd.read_sql(
    """
    SELECT number
    FROM vehicles
    WHERE status='Completed'
    ORDER BY id DESC
    """,
    conn
    )


    if len(completed)>0:


        selected=st.selectbox(
        "Select Previous Vehicle",
        completed.number.tolist()
        )


        if st.button(
        "Show Receipt"
        ):


            receipt=generate_receipt(
                selected
            )


            st.code(
                receipt
            )


            st.download_button(
            "Download Receipt",
            receipt,
            file_name=
            f"{selected}_receipt.txt"
            )



# ================= SLOT MAP =================


if choice=="Dashboard":


    st.markdown("---")

    st.subheader(
        "🅿️ Smart Parking Map"
    )


    slots=pd.read_sql(
    "SELECT * FROM slots",
    conn
    )


    cols=st.columns(10)


    for index,row in slots.iterrows():


        with cols[index%10]:


            if row.status=="Free":

                st.success(
                row.slot
                )

            else:

                st.error(
                row.slot
                )



# ================= VEHICLE HISTORY =================


if choice=="Reports":


    st.markdown("---")


    st.subheader(
    "📜 Vehicle History"
    )


    history=pd.read_sql(
    """
    SELECT 
    number,
    slot,
    entry_time,
    exit_time,
    hours,
    fee,
    status
    FROM vehicles
    ORDER BY id DESC
    """,
    conn
    )


    st.dataframe(
        history,
        use_container_width=True
    )



# ================= DAILY REVENUE =================


if choice=="Reports":


    today=str(
    datetime.datetime.now().date()
    )


    revenue=pd.read_sql(
    """
    SELECT SUM(fee)
    FROM vehicles
    WHERE exit_time LIKE ?
    """,
    conn,
    params=(today+"%",)
    )


    value=revenue.iloc[0,0]


    if value is None:
        value=0


    st.metric(
        "Today's Revenue",
        f"Rs {value}"
    )
    # ================= PREMIUM UI =================


st.markdown("""
<style>

.stMetric{
background:#f1f5f9;
padding:15px;
border-radius:15px;
}

div[data-testid="stButton"] button{
border-radius:10px;
font-weight:bold;
}

</style>

""",unsafe_allow_html=True)



# ================= ADMIN CONTROL =================


if st.session_state.role=="Administrator":


    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "⚙️ Admin Panel"
    )


    admin_option=st.sidebar.selectbox(
        "Admin Action",
        [
        "None",
        "Backup Database",
        "Clear Completed Records"
        ]
    )



    # DATABASE BACKUP

    if admin_option=="Backup Database":


        with open(
        "parking.db",
        "rb"
        ) as file:


            st.sidebar.download_button(
            "Download Database Backup",
            file,
            file_name="parking_backup.db"
            )



    # DELETE OLD DATA


    if admin_option=="Clear Completed Records":


        st.sidebar.warning(
        "This will delete exited vehicles"
        )


        confirm=st.sidebar.checkbox(
        "I Confirm"
        )


        if confirm:


            if st.sidebar.button(
            "Delete Records"
            ):


                cursor.execute(
                """
                DELETE FROM vehicles
                WHERE status='Completed'
                """
                )

                conn.commit()


                st.sidebar.success(
                "Old records removed"
                )



# ================= ADVANCED ANALYTICS =================


if choice=="Reports":


    st.subheader(
    "📊 Advanced Analytics"
    )


    df=pd.read_sql(
    "SELECT * FROM vehicles",
    conn
    )


    if len(df)>0:


        col1,col2=st.columns(2)


        with col1:


            type_count=df[
            "vehicle_type"
            ].value_counts()


            fig=px.bar(
            type_count,
            title="Vehicle Types"
            )


            st.plotly_chart(
            fig,
            use_container_width=True
            )



        with col2:


            status_count=df[
            "status"
            ].value_counts()


            fig2=px.pie(
            names=status_count.index,
            values=status_count.values,
            title="Vehicle Status"
            )


            st.plotly_chart(
            fig2,
            use_container_width=True
            )



# ================= PARKING SUMMARY =================


if choice=="Dashboard":


    st.markdown("---")


    st.subheader(
    "📌 Parking Summary"
    )


    slots=pd.read_sql(
    "SELECT * FROM slots",
    conn
    )


    summary=pd.DataFrame({

    "Status":
    [
    "Free",
    "Occupied"
    ],

    "Count":
    [
    len(slots[slots.status=="Free"]),
    len(slots[slots.status=="Occupied"])
    ]

    })


    chart=px.bar(
    summary,
    x="Status",
    y="Count",
    title="Current Parking Capacity"
    )


    st.plotly_chart(
    chart,
    use_container_width=True
    )



# ================= FOOTER =================


st.markdown(
"""
<br><br>
<center>

🚘 Smart Parking System  
Developed using Python + Streamlit + SQLite

</center>

""",
unsafe_allow_html=True
)