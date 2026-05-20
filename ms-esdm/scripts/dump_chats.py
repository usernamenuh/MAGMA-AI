import os
import dotenv
import pandas as pd
from sqlalchemy import create_engine
from sshtunnel import SSHTunnelForwarder
from datetime import datetime

dotenv.load_dotenv()

# SSH Configuration
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_USER = os.getenv("SSH_USER")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

# Database Configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
LOCAL_PORT = 5433  # Local port to bind

print(f"Key exists: {os.path.exists(SSH_KEY_PATH) if SSH_KEY_PATH else 'No key path provided'}")

# Create SSH tunnel with private key
with SSHTunnelForwarder(
    (SSH_HOST, SSH_PORT),
    ssh_username=SSH_USER,
    ssh_pkey=SSH_KEY_PATH,
    remote_bind_address=(DB_HOST, DB_PORT),
    local_bind_address=('127.0.0.1', LOCAL_PORT),
    set_keepalive=10.0
) as tunnel:
    
    print(f"SSH Tunnel established: localhost:{LOCAL_PORT} -> {SSH_HOST}:{DB_PORT}")
    
    # Build connection string for local tunnel
    conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{LOCAL_PORT}/{DB_NAME}"
    
    engine = create_engine(conn_str)
    
    query = """
    SELECT 
        u.email, 
        ch.session_id, 
        ch.role, 
        ch.message,
        ch."references" as "knowledge_base",
        ch.response as "api_documentation", 
        ch.created_at as "timestamp"
    FROM chat_histories as ch 
    INNER JOIN users as u 
        ON ch.user_id = u.user_id;
    """
    
    # Fetch and save
    print("Fetching data from database...")
    df = pd.read_sql(query, engine)
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_logs_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename} ({len(df)} rows)")