import socket
import psycopg2
import pandas as pd

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

#conn_str = "postgresql://neondb_owner:npg_GnfzMYr3ItK8@ep-odd-snow-amh8s5el-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
conn_str = "postgresql://neondb_owner:npg_oTfcJe8Wb6xP@ep-falling-dust-anck4xzp-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

#with psycopg2.connect(conn_str) as conn:
    #with conn.cursor() as cur:
        #cur.execute("SELECT version();")
        #print(cur.fetchone())
        #print(cur.execute('SELECT COUNT(*) FROM "Assn8_virtual";'))

conn = psycopg2.connect(conn_str)

if conn.closed == 0:
    print("Connected")
else:
    print("Connection inactive")

query = ('SELECT * FROM "Assn8_virtual" LIMIT 10;')
results = pd.read_sql_query(query, conn)
print(results)
#conn.close()


serverIP = "0.0.0.0" #input("Enter server IP: ")
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
        response = get_avg_moisture(conn)
    elif "water consumption" in decodedMessage.lower():
        response = get_avg_water(conn)
    elif "electricity" in decodedMessage.lower():
        response = get_electricity_comparison(conn)
    else:
        response = "This query cannot be processed."

    connectionSocket.send(response.encode("utf-8"))
    

connectionSocket.close()
#myTCPSocket.close()