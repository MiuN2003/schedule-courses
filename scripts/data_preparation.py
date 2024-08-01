import pandas as pd
import psycopg2

db_config = {
'host': '',
'database': '',
'user': '',
'password': '',
'port': ''
}

conn = psycopg2.connect(**db_config)
cur = conn.cursor()

def load_data():

    query = "SELECT * FROM public.courses;"
    cur.execute(query)
    columns = [desc[0] for desc in cur.description]
    courses = pd.DataFrame(cur.fetchall(), columns=columns)

    query = "SELECT * FROM public.resources;"
    cur.execute(query)
    columns = [desc[0] for desc in cur.description]
    resources = pd.DataFrame(cur.fetchall(), columns=columns)

    query = "SELECT * FROM public.teachers;"
    cur.execute(query)
    columns = [desc[0] for desc in cur.description]
    teachers = pd.DataFrame(cur.fetchall(), columns=columns)

    return resources, courses, teachers

def push_data(results):
     # Lưu youpass_update vào file CSV
    results.to_csv('results_optimizer.csv', index=False)
    
    # Xóa tất cả các dòng dữ liệu trong bảng
    delete_query = "DELETE FROM public.results_optimizer;"
    cur.execute(delete_query)
    conn.commit()
    
    # Nhập dữ liệu từ file CSV vào PostgreSQL
    copy_sql = """
        COPY public.results_optimizer FROM stdin WITH CSV HEADER
        DELIMITER as ','
    """
    with open('results_optimizer.csv', 'r', encoding='utf-8') as f:
        cur.copy_expert(sql=copy_sql, file=f)
    conn.commit()
