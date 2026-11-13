
import streamlit as st
import pandas as pd
from database import init_database, get_connection

# Konfigurasi halaman
st.set_page_config(
    page_title="KostMate",
    page_icon="🏠",
    layout="wide"
)

# Inisialisasi database
init_database()

# Pengaturan tampilan sidebar
st.sidebar.title("🏠 KostMate")
st.sidebar.caption("Boarding House Management")

menu = st.sidebar.radio(
    "Navigasi",
    [
        "Dashboard",
        "Kamar & Penghuni",
        "Penagihan",
        "Keluhan",
        "Laporan"
    ]
)

# Fungsi mengambil data dari database
def get_data(query):
    conn = get_connection()
    data = pd.read_sql_query(query, conn)
    conn.close()
    return data


# Halaman Dashboard
if menu == "Dashboard":

    st.title("Dashboard")
    st.caption("Ringkasan kondisi dan aktivitas kost.")

    # Mengambil jumlah kamar
    rooms = get_data("SELECT * FROM rooms")
    total_rooms = len(rooms)
    occupied = len(rooms[rooms["status"] == "Terisi"])
    empty = len(rooms[rooms["status"] == "Kosong"])
    maintenance = len(rooms[rooms["status"] == "Perbaikan"])

    # Mengambil data pembayaran
    payments = get_data("SELECT * FROM payments")

    # Menentukan bulan dan tanggal saat ini
    today = pd.Timestamp.today().date()
    current_month = today.strftime("%Y-%m")

    # Menghitung pemasukan bulan berjalan
    paid_payments = payments[
        (payments["status"] == "Lunas") &
        (payments["payment_date"].notna())
    ]

    paid_this_month = paid_payments[
    paid_payments["payment_date"].str.startswith(current_month)
    ]

    total_income = paid_this_month["amount"].sum()

    # Menghitung tagihan belum lunas
    unpaid_data = payments[
        payments["status"] == "Belum Lunas"
    ]

    unpaid = len(unpaid_data)

    # Menghitung tagihan yang sudah melewati jatuh tempo
    overdue_data = unpaid_data[
        unpaid_data["due_date"] < today.isoformat()
    ]

    overdue = len(overdue_data)

    # Menampilkan ringkasan Dashboard
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Kamar", total_rooms)
    col2.metric("Kamar Terisi", occupied)
    col3.metric("Kamar Kosong", empty)
    col4.metric("Perbaikan", maintenance)

    st.divider()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Pemasukan Bulan Ini",
        f"Rp {total_income:,.0f}"
    )

    col2.metric(
        "Belum Lunas",
        unpaid
    )

    col3.metric(
        "Terlambat",
        overdue
    )

    st.subheader("Status Kamar")

    if not rooms.empty:
        st.dataframe(
            rooms[["room_number", "price", "status"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Belum ada data kamar.")

    st.subheader("Tagihan Belum Lunas")

    unpaid_data = payments[
        payments["status"] == "Belum Lunas"
    ]

    if not unpaid_data.empty:
        st.dataframe(
            unpaid_data,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Tidak ada tagihan yang belum lunas.")


# Halaman Kamar & Penghuni
elif menu == "Kamar & Penghuni":

    st.title("Kamar & Penghuni")
    st.caption("Kelola data kamar dan penghuni kost.")

    # Form tambah kamar dan penghuni
    col1, col2 = st.columns(2)

    # Form tambah kamar
    with col1:
        st.subheader("Tambah Kamar")

        with st.form("form_kamar"):
            room_number = st.text_input("Nomor Kamar")
            price = st.number_input(
                "Harga Sewa per Bulan (Rp)",
                min_value=0,
                step=50000
            )

            submit_room = st.form_submit_button(
                "Tambah Kamar",
                use_container_width=True
            )

            if submit_room:
                if not room_number.strip() or price <= 0:
                    st.error("Isi nomor kamar dan harga sewa dengan benar.")
                else:
                    conn = get_connection()
                    try:
                        conn.execute(
                            """
                            INSERT INTO rooms (room_number, price, status)
                            VALUES (?, ?, 'Kosong')
                            """,
                            (room_number.strip(), price)
                        )
                        conn.commit()
                        st.success("Kamar berhasil ditambahkan.")
                        st.rerun()

                    except Exception:
                        st.error("Nomor kamar sudah digunakan.")

                    finally:
                        conn.close()

    # Form tambah penghuni
    with col2:
        st.subheader("Tambah Penghuni")

        available_rooms = get_data(
            "SELECT * FROM rooms WHERE status = 'Kosong'"
        )

        with st.form("form_penghuni"):
            name = st.text_input("Nama Penghuni")
            phone = st.text_input("Nomor Telepon")

            if not available_rooms.empty:
                room_id = st.selectbox(
                    "Pilih Kamar",
                    available_rooms["id"].tolist(),
                    format_func=lambda x: (
                        f"Kamar {available_rooms.loc[available_rooms['id'] == x, 'room_number'].iloc[0]}"
                    )
                )
            else:
                room_id = None
                st.info("Belum ada kamar kosong.")

            start_date = st.date_input("Tanggal Mulai Sewa")
            end_date = st.date_input("Tanggal Akhir Sewa")

            submit_tenant = st.form_submit_button(
                "Daftarkan Penghuni",
                use_container_width=True
            )

            if submit_tenant:
                if not name.strip():
                    st.error("Nama penghuni wajib diisi.")
                elif room_id is None:
                    st.error("Tambahkan kamar kosong terlebih dahulu.")
                elif end_date <= start_date:
                    st.error("Tanggal akhir harus setelah tanggal mulai.")
                else:
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()

                        # Memastikan kamar masih kosong
                        cursor.execute(
                            "SELECT status FROM rooms WHERE id = ?",
                            (room_id,)
                        )
                        room = cursor.fetchone()

                        if room is None or room["status"] != "Kosong":
                            st.error("Kamar sudah tidak tersedia.")
                        else:
                            cursor.execute(
                                """
                                INSERT INTO tenants
                                (name, phone, room_id, start_date, end_date)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    name.strip(),
                                    phone.strip(),
                                    room_id,
                                    start_date.isoformat(),
                                    end_date.isoformat()
                                )
                            )

                            cursor.execute(
                                """
                                UPDATE rooms
                                SET status = 'Terisi'
                                WHERE id = ?
                                """,
                                (room_id,)
                            )

                            conn.commit()
                            st.success("Penghuni berhasil didaftarkan.")
                            st.rerun()

                    finally:
                        conn.close()

    st.divider()

    # Menampilkan data kamar
    st.subheader("Daftar Kamar")

    rooms = get_data("SELECT * FROM rooms")

    if not rooms.empty:
        st.dataframe(
            rooms[["room_number", "price", "status"]].rename(
                columns={
                    "room_number": "Nomor Kamar",
                    "price": "Harga Sewa",
                    "status": "Status"
                }
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Belum ada kamar yang terdaftar.")

    # Menampilkan data penghuni
    st.subheader("Daftar Penghuni")

    tenants = get_data(
        """
        SELECT
            tenants.name,
            tenants.phone,
            rooms.room_number,
            tenants.start_date,
            tenants.end_date
        FROM tenants
        JOIN rooms ON tenants.room_id = rooms.id
        """
    )

    if not tenants.empty:
        st.dataframe(
            tenants.rename(
                columns={
                    "name": "Nama Penghuni",
                    "phone": "Nomor Telepon",
                    "room_number": "Nomor Kamar",
                    "start_date": "Mulai Sewa",
                    "end_date": "Akhir Sewa"
                }
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Belum ada penghuni yang terdaftar.")


# Halaman Penagihan
elif menu == "Penagihan":

    st.title("Penagihan Sewa")
    st.caption("Kelola tagihan dan catat pembayaran penghuni.")

    # Mengambil data penghuni dan kamar
    tenants = get_data("""
        SELECT
            tenants.id,
            tenants.name,
            rooms.room_number,
            rooms.price
        FROM tenants
        JOIN rooms ON tenants.room_id = rooms.id
    """)

    # Form membuat tagihan
    st.subheader("Buat Tagihan Baru")

    if not tenants.empty:

        with st.form("form_tagihan"):

            tenant_id = st.selectbox(
                "Pilih Penghuni",
                tenants["id"].tolist(),
                format_func=lambda x: (
                    f"{tenants.loc[tenants['id'] == x, 'name'].iloc[0]} "
                    f"- Kamar {tenants.loc[tenants['id'] == x, 'room_number'].iloc[0]}"
                )
            )

            amount = st.number_input(
                "Jumlah Tagihan (Rp)",
                min_value=1,
                value=500000,
                step=50000
            )

            due_date = st.date_input("Tanggal Jatuh Tempo")

            submit = st.form_submit_button(
                "Buat Tagihan",
                use_container_width=True
            )

            if submit:
                conn = get_connection()

                conn.execute(
                    """
                    INSERT INTO payments
                    (tenant_id, amount, due_date, status)
                    VALUES (?, ?, ?, 'Belum Lunas')
                    """,
                    (tenant_id, amount, due_date.isoformat())
                )

                conn.commit()
                conn.close()

                st.success("Tagihan berhasil dibuat.")
                st.rerun()

    else:
        st.info("Daftarkan penghuni terlebih dahulu.")

    st.divider()

    # Mengambil seluruh data tagihan
    st.subheader("Daftar Tagihan")

    payments = get_data("""
        SELECT
            payments.id,
            tenants.name,
            rooms.room_number,
            payments.amount,
            payments.due_date,
            payments.payment_date,
            payments.status
        FROM payments
        JOIN tenants ON payments.tenant_id = tenants.id
        JOIN rooms ON tenants.room_id = rooms.id
        ORDER BY payments.due_date DESC
    """)

    if not payments.empty:

        # Ringkasan tagihan
        unpaid = payments[
            payments["status"] == "Belum Lunas"
        ]

        paid = payments[
            payments["status"] == "Lunas"
        ]

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Tagihan", len(payments))
        col2.metric("Belum Lunas", len(unpaid))
        col3.metric("Sudah Lunas", len(paid))

        st.divider()

        # Menampilkan setiap tagihan
        for _, payment in payments.iterrows():

            with st.container(border=True):

                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**{payment['name']}**")
                    st.caption(
                        f"Kamar {payment['room_number']} | "
                        f"Jatuh tempo: {payment['due_date']}"
                    )

                    st.write(
                        f"Rp {payment['amount']:,.0f}"
                    )

                    if payment["status"] == "Lunas":
                        st.success(
                            f"Lunas pada {payment['payment_date']}"
                        )
                    else:
                        st.warning("Belum Lunas")

                with col2:

                    if payment["status"] == "Belum Lunas":

                        if st.button(
                            "Tandai Lunas",
                            key=f"paid_{payment['id']}",
                            use_container_width=True
                        ):

                            conn = get_connection()

                            conn.execute(
                                """
                                UPDATE payments
                                SET status = 'Lunas',
                                    payment_date = ?
                                WHERE id = ?
                                """,
                                (
                                    pd.Timestamp.today().date().isoformat(),
                                    payment["id"]
                                )
                            )

                            conn.commit()
                            conn.close()

                            st.success("Pembayaran berhasil dicatat.")
                            st.rerun()

    else:
        st.info("Belum ada tagihan yang dibuat.")


# Halaman Keluhan
elif menu == "Keluhan":

    st.title("Tiket Keluhan Fasilitas")
    st.caption("Catat dan pantau laporan kerusakan fasilitas kost.")

    # Mengambil data penghuni
    tenants = get_data("""
        SELECT
            tenants.id,
            tenants.name,
            rooms.room_number
        FROM tenants
        JOIN rooms ON tenants.room_id = rooms.id
    """)

    st.subheader("Buat Laporan Keluhan")

    if not tenants.empty:

        with st.form("form_keluhan"):

            tenant_id = st.selectbox(
                "Nama Penghuni",
                tenants["id"].tolist(),
                format_func=lambda x: (
                    f"{tenants.loc[tenants['id'] == x, 'name'].iloc[0]} "
                    f"- Kamar {tenants.loc[tenants['id'] == x, 'room_number'].iloc[0]}"
                )
            )

            description = st.text_area(
                "Deskripsi Kerusakan",
                placeholder="Contoh: AC kamar tidak dingin."
            )

            submit = st.form_submit_button(
                "Kirim Laporan",
                use_container_width=True
            )

            if submit:

                if not description.strip():
                    st.error("Deskripsi keluhan wajib diisi.")

                else:
                    conn = get_connection()

                    conn.execute(
                        """
                        INSERT INTO complaints
                        (tenant_id, description, report_date, status)
                        VALUES (?, ?, ?, 'Baru')
                        """,
                        (
                            tenant_id,
                            description.strip(),
                            pd.Timestamp.today().date().isoformat()
                        )
                    )

                    conn.commit()
                    conn.close()

                    st.success("Laporan keluhan berhasil dibuat.")
                    st.rerun()

    else:
        st.info("Daftarkan penghuni terlebih dahulu.")

    st.divider()

    # Menampilkan daftar keluhan
    st.subheader("Daftar Keluhan")

    complaints = get_data("""
        SELECT
            complaints.id,
            tenants.name,
            rooms.room_number,
            complaints.description,
            complaints.report_date,
            complaints.status
        FROM complaints
        JOIN tenants ON complaints.tenant_id = tenants.id
        JOIN rooms ON tenants.room_id = rooms.id
        ORDER BY complaints.id DESC
    """)

    if not complaints.empty:

        # Ringkasan keluhan
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Keluhan Baru",
            len(complaints[complaints["status"] == "Baru"])
        )

        col2.metric(
            "Diproses",
            len(complaints[complaints["status"] == "Diproses"])
        )

        col3.metric(
            "Selesai",
            len(complaints[complaints["status"] == "Selesai"])
        )

        st.divider()

        # Menampilkan setiap laporan
        for _, complaint in complaints.iterrows():

            with st.container(border=True):

                st.write(
                    f"**{complaint['name']} - "
                    f"Kamar {complaint['room_number']}**"
                )

                st.caption(
                    f"Tanggal laporan: {complaint['report_date']}"
                )

                st.write(complaint["description"])

                # Pilihan status penanganan
                status_options = [
                    "Baru",
                    "Diproses",
                    "Selesai"
                ]

                new_status = st.selectbox(
                    "Status Penanganan",
                    status_options,
                    index=status_options.index(complaint["status"]),
                    key=f"status_{complaint['id']}"
                )

                if st.button(
                    "Simpan Status",
                    key=f"save_{complaint['id']}"
                ):

                    conn = get_connection()

                    conn.execute(
                        """
                        UPDATE complaints
                        SET status = ?
                        WHERE id = ?
                        """,
                        (new_status, complaint["id"])
                    )

                    conn.commit()
                    conn.close()

                    st.success("Status keluhan berhasil diperbarui.")
                    st.rerun()

    else:
        st.info("Belum ada laporan keluhan.")


# Halaman Laporan Keuangan
elif menu == "Laporan":

    st.title("Laporan Keuangan Kost")
    st.caption("Ringkasan pemasukan dan pengeluaran kost.")

    # Form pencatatan pengeluaran
    st.subheader("Tambah Pengeluaran")

    with st.form("form_pengeluaran"):

        description = st.text_input(
            "Keterangan Pengeluaran",
            placeholder="Contoh: Perbaikan AC kamar A01"
        )

        amount = st.number_input(
            "Jumlah Pengeluaran (Rp)",
            min_value=1,
            value=100000,
            step=50000
        )

        expense_date = st.date_input("Tanggal Pengeluaran")

        submit = st.form_submit_button(
            "Simpan Pengeluaran",
            use_container_width=True
        )

        if submit:

            if not description.strip():
                st.error("Keterangan pengeluaran wajib diisi.")

            else:
                conn = get_connection()

                conn.execute(
                    """
                    INSERT INTO expenses
                    (description, amount, expense_date)
                    VALUES (?, ?, ?)
                    """,
                    (
                        description.strip(),
                        amount,
                        expense_date.isoformat()
                    )
                )

                conn.commit()
                conn.close()

                st.success("Pengeluaran berhasil dicatat.")
                st.rerun()

    st.divider()

    # Memilih periode laporan
    st.subheader("Ringkasan Keuangan")

    selected_month = st.date_input(
        "Pilih Bulan Laporan",
        value=pd.Timestamp.today().date().replace(day=1),
        key="report_month"
    )

    month = selected_month.strftime("%Y-%m")

    # Mengambil pemasukan dari pembayaran lunas
    income_data = get_data("""
        SELECT amount, payment_date
        FROM payments
        WHERE status = 'Lunas'
        AND payment_date IS NOT NULL
    """)

    # Mengambil data pengeluaran
    expense_data = get_data("""
        SELECT description, amount, expense_date
        FROM expenses
    """)

    # Menghitung pemasukan bulan terpilih
    if not income_data.empty:
        income_data = income_data[
            income_data["payment_date"].str.startswith(month)
        ]

        total_income = income_data["amount"].sum()

    else:
        total_income = 0

    # Menghitung pengeluaran bulan terpilih
    if not expense_data.empty:
        expense_data = expense_data[
            expense_data["expense_date"].str.startswith(month)
        ]

        total_expense = expense_data["amount"].sum()

    else:
        total_expense = 0

    # Menghitung selisih keuangan
    balance = total_income - total_expense

    # Menampilkan ringkasan
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Pemasukan",
        f"Rp {total_income:,.0f}"
    )

    col2.metric(
        "Total Pengeluaran",
        f"Rp {total_expense:,.0f}"
    )

    col3.metric(
        "Selisih",
        f"Rp {balance:,.0f}"
    )

    st.divider()

    # Grafik pemasukan dan pengeluaran
    st.subheader("Grafik Keuangan")

    chart_data = pd.DataFrame({
        "Kategori": ["Pemasukan", "Pengeluaran"],
        "Jumlah": [total_income, total_expense]
    })

    st.bar_chart(
        chart_data.set_index("Kategori")
    )

    st.divider()

    # Riwayat pengeluaran
    st.subheader("Riwayat Pengeluaran")

    if not expense_data.empty:

        st.dataframe(
            expense_data.rename(
                columns={
                    "description": "Keterangan",
                    "amount": "Jumlah (Rp)",
                    "expense_date": "Tanggal"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Belum ada pengeluaran pada bulan ini.")
