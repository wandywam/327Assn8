import socket
import psycopg2
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv() #added to keep DB connection strings private

LOCAL_DB = os.environ["LOCAL_DB"]
PEER_DB = os.environ["PEER_DB"]

LOCAL_HOUSE = os.environ["LOCAL_HOUSE"]
PEER_HOUSE = os.environ["PEER_HOUSE"]

LOCAL_TABLE_NAME = os.environ["LOCAL_TABLE_NAME"]
PEER_TABLE_NAME = os.environ["PEER_TABLE_NAME"]

LOCAL_TOPIC = os.environ["LOCAL_TOPIC_SUBSTRING"]
PEER_TOPIC = os.environ["PEER_TOPIC_SUBSTRING"]

RANDY_SHARING_TIME = datetime(2026, 4, 30, 5, 3, 5, tzinfo=timezone.utc) 
MIA_SHARING_TIME = datetime(2026, 4, 30, 5, 16, 13, tzinfo=timezone.utc) #Mia's sharing time was later
SHARING_START = MIA_SHARING_TIME

DB_METADATA = {
    "local": {
        "house": LOCAL_HOUSE,
        "topic_substring" : LOCAL_TOPIC,
        "table": LOCAL_TABLE_NAME
    },
    "peer": {
        "house": PEER_HOUSE,
        "topic_substring": PEER_TOPIC,
        "table": PEER_TABLE_NAME
    },
}

conn_str1 = LOCAL_DB
conn_str2 = PEER_DB

#safe connection check function
def safe_connection(conn_str, label):
    try:
        conn = psycopg2.connect(conn_str)
        print(f"Successfully connected to {label}!")
        return conn
    except Exception as e:
        print(f"Failed to connect to {label}, Error: {e}")
        return None

mia_conn = safe_connection(conn_str1, "Mia's DB")
randy_conn = safe_connection(conn_str2, "Randy's DB")

#dict of connections for quick and clear access, ie. connections["randy_new"]
connections = {
    "randy_db" : randy_conn,
    "mia_db" : mia_conn
    }

def connection_check(conn):
    if conn.closed == 0:
        print("Connected")
    else:
        print("Connection inactive")



def get_avg_moisture(conn):
    intervals = {
        "past hour": "1 hour",
        "past week": "1 week",
        "past month": "1 month"}
    
    results = {}

    with conn.cursor() as cur:
        for label, interval in intervals.items():
            query = f"""
            SELECT AVG(value::float)
            FROM "Assn8_virtual",
            LATERAL json_each_text(payload::json) AS sensor(key, value)
            WHERE key ILIKE '%Moisture%'
            AND time >= NOW() - INTERVAL '{interval}';
            """
            cur.execute(query)
            results[label] = cur.fetchone()[0]

    return(
        "Average fridge moisture:\n"
        f"Past hour: {results['past hour']:.2f}\n"
        f"Past week: {results['past week']:.2f}\n"
        f"Past month: {results['past month']:.2f}"
    )

def get_avg_water(conn):
    intervals = {
        "past hour": "1 hour",
        "past week": "1 week",
        "past month": "1 month"
    }

    results = {}

    with conn.cursor() as cur:
        for label, interval in intervals.items():
            query = f"""
            SELECT AVG(value::float)
            FROM "Assn8_virtual",
            LATERAL json_each_text(payload::json) AS sensor(key, value)
            WHERE key ILIKE '%Water Consumption%'
            AND time >= NOW() - INTERVAL '{interval}';
            """
            cur.execute(query)
            results[label] = cur.fetchone()[0]

    return (
        "Average dishwasher water consumption:\n"
        f"Past hour: {results['past hour']:.2f}\n"
        f"Past week: {results['past week']:.2f}\n"
        f"Past month: {results['past month']:.2f}"
    )

def get_electricity_comparison(conn):
    query = """
    SELECT topic, SUM(value::float)
    FROM "Assn8_virtual",
    LATERAL json_each_text(payload::json) AS sensor(key, value)
    WHERE key ILIKE '%Ammeter%'
    AND time >= NOW() - INTERVAL '24 hours'
    GROUP BY topic;
    """

    usage = {}

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    for topic, total in rows:
        if "randylam" in topic:
            usage["Randy's House"] = total
        elif "mia" in topic:
            usage["Mia's House"] = total

    if len(usage) < 2:
        return "Not enough electricity data from both houses yet."

    randy_usage = usage.get("Randy's House", 0)
    mia_usage = usage.get("Mia's House", 0)

    if randy_usage > mia_usage:
        winner = "Randy's House"
        difference = randy_usage - mia_usage
    elif mia_usage > randy_usage:
        winner = "Mia's House"
        difference = mia_usage - randy_usage
    else:
        return (
            "Electricity usage in the past 24 hours:\n"
            f"Randy's House: {randy_usage:.2f}\n"
            f"Mia's House: {mia_usage:.2f}\n"
            "Both houses consumed the same amount."
        )

    return (
        "Electricity usage in the past 24 hours:\n"
        f"Randy's House: {randy_usage:.2f}\n"
        f"Mia's House: {mia_usage:.2f}\n"
        f"{winner} consumed more electricity by {difference:.2f}."
    )

#with psycopg2.connect(conn_str) as conn:
    #with conn.cursor() as cur:
        #cur.execute("SELECT version();")
        #print(cur.fetchone())
        #print(cur.execute('SELECT COUNT(*) FROM "Assn8_virtual";'))


'''query = ('SELECT * FROM "327Assn8_virtual" LIMIT 10;')
with connections["randy_db"].cursor() as cur:
    cur.execute(query)
    rows = cur.fetchall()
    for row in rows:
        print(row)'''
#results = pd.read_sql_query(query, connections["randy_db"])
#print(results)
#conn.close()


'''def run_query(sql):
    conn = connections["mia_db"].cursor()
    try:
        with conn as cur:
            cur.execute(sql)
            try:
                return cur.fetchall()
            except Exception as e:
                return None
    finally:
        conn.close()

rows = run_query(f'
                SELECT * FROM "{DB_METADATA["local"]["table"]}"
                 where id = 1451
')
print(rows)'''

'''serverIP = "0.0.0.0" #input("Enter server IP: ")
serverPort = 12345 #int(input("Enter server port number: "))
maxBytesToReceive = 1024

myTCPSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
myTCPSocket.bind((serverIP, serverPort))
myTCPSocket.listen(1)

connectionSocket, addr = myTCPSocket.accept()

while True:
    clientMessage = connectionSocket.recv(maxBytesToReceive)

    if not clientMessage:
        break

    decodedMessage = clientMessage.decode("utf-8")
    print(decodedMessage)
    
    if "average moisture" in decodedMessage.lower():
        response = get_avg_moisture(connections["randy_new"])
    elif "water consumption" in decodedMessage.lower():
        response = get_avg_water(connections["randy_new"])
    elif "electricity" in decodedMessage.lower():
        response = get_electricity_comparison(connections["randy_new"])
    else:
        response = "This query cannot be processed."

    connectionSocket.send(response.encode("utf-8"))
    

connectionSocket.close()
#myTCPSocket.close()'''

#function to inspect DB's

def inspect(label, conn, table):
    print("\n")
    print(f"{label}, {table}")
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*), MIN(time), MAX(time) FROM "{table}";')
        count, earliest, latest = cur.fetchone()
        print(f"Rows: {count} | Earliest: {earliest} | Latest: {latest}")
        
        cur.execute(f'SELECT DISTINCT topic FROM "{table}";')
        topics = [row[0] for row in cur.fetchall()]
        print(f"Distinct topics: {topics}")
        
        cur.execute(f'SELECT * FROM "{table}" LIMIT 1;')
        sample = cur.fetchone()
        cols = [desc[0] for desc in cur.description]
        print(f"Sample row columns: {cols}")
        print(f"Sample row values:  {sample}")

inspect("Local - mia",  connections["mia_db"],   DB_METADATA["local"]["table"])
inspect("Peer - randy", connections["randy_db"], DB_METADATA["peer"]["table"])