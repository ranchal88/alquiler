from src.db import get_conn  
conn=get_conn()  
cur=conn.cursor()  
cur.execute('SELECT 1')  
print(cur.fetchone())  
conn.close()  
