from src.db import _fix_database_url  
u='postgresql://postgres.wsozuddacussmvqynesv:Kuntorres?1234@aws-1-eu-west-1.pooler.supabase.com:6543/postgres'  
print(_fix_database_url(u))  
