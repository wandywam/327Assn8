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

#Constants for conversions
LITERS_PER_GALLON = 3.785
VOLTAGE = 120
INTERVAL_HOURS = 1 / 60

def time_intervals():
    '''time intervals for moisture and water queries'''
    intervals = {
        "Past hour" : timedelta(hours=1),
        "Past week" : timedelta(weeks = 1),
        "Past month" : timedelta(days=30)
    }
    return intervals


#now_utc = datetime.now(timezone.utc) #datetime object in UTC
#now_pst = now_utc.astimezone(ZoneInfo("America/Los_Angeles")) #Convert to pacific time
#print(f'UTC time: {now_utc}')
#print(f'PST time: {now_pst}')

def utc_to_pst(utc_time):
    '''convert utc -> pacific time'''
    return utc_time.astimezone(ZoneInfo("America/Los_Angeles"))


#safe connection check function
def safe_connection(conn_str, label):
    try:
        conn = psycopg2.connect(conn_str)
        print(f"Successfully connected to {label}!")
        return conn
    except Exception as e:
        print(f"Failed to connect to {label}, Error: {e}")
        return None


#Connection setup:
local_conn = safe_connection(LOCAL_DB, f"{LOCAL_HOUSE}'s db")
peer_conn = safe_connection(PEER_DB, f"{PEER_HOUSE}'s db")

connections = {
    "local" : local_conn,
    "peer" : peer_conn
}

def connection_check(conn):
    if conn.closed == 0:
        print("Connected")
    else:
        print("Connection inactive")



#Data retrieval
def query_func(conn, table, key, start_utc, end_utc):
    '''retrieves time, value, topic for each row with provided key AND within time interval'''
    #converted Randy's queries into a function
    query = f'''        
        SELECT time, value::float, topic
        FROM "{table}",
        LATERAL jsonb_each_text(payload::jsonb) AS sensor(key, value)
        WHERE key ILIKE %s
        AND time >= %s
        AND time < %s;'''
    
    with conn.cursor() as cur:
        cur.execute(query, (f"%{key}%", start_utc, end_utc)) #key replaces %s
        return cur.fetchall()
    
def filter_by_topic(rows, substring):
    '''Retrieve from correct DB based on topic'''
    return [r for r in rows if substring in r[2]]


#Distrubted Queries (collect from correct dbs based on time interval!)
def collect_data(connections, key, start_time, end_time):
    '''Need to collect data from both DB's if start time is before sharing time, else use local DB'''
    
    local_meta = DB_METADATA["local"]
    peer_meta = DB_METADATA["peer"]
    
    if start_time >= SHARING_START:
        rows = query_func(connections["local"], local_meta["table"], key, start_time, end_time)
        return rows, "from local db only bc time window is after sharing"
    
    else:
        local_full = query_func(connections["local"], local_meta["table"], key, start_time, end_time)

        local_house = filter_by_topic(local_full, local_meta["topic_substring"])
        peer_post = filter_by_topic(local_full, peer_meta["topic_substring"])

        peer_pre = query_func(connections["peer"], peer_meta["table"], key, start_time, SHARING_START) #end time in replaced with when sharing started
        rows = local_house + peer_post + peer_pre
        return rows, "from local db and peer db bc time window incluses pre-sharing period"
    


def compute_avg(connections, key, label, unit, unit_conversion=None):
    now = datetime.now(timezone.utc)
    intervals = time_intervals() #dictionairy


    results = {}
    for time, interval in intervals.items():
        start_time = now - interval
        rows, sources = collect_data(connections, key, start_time, now)
        
        values = []
        for row in rows:
            value = row[1] #value is second element
            values.append(value)

        if values:
            avg = sum(values) / len(values) #compute avg
            if unit_conversion:
                avg = unit_conversion(avg)
            results[time] = avg
        else:
            results[time] = None

    return(
        "Average fridge moisture:\n"
        f'Query at {utc_to_pst(now)}\n'
        f"Past hour: {results['Past hour']:.2f} {unit}\n"
        f"Past week: {results['Past week']:.2f} {unit}\n"
        f"Past month: {results['Past month']:.2f} {unit}"
    )



def get_avg_moisture(conn):
    return compute_avg(connections, key = "Moisture", label = "Avg Fridge Moisture", unit = "%")
    '''now = datetime.now(timezone.utc)
    intervals = time_intervals()
    
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
    )'''

def get_avg_water(conn):
    return compute_avg(connections, key = "Water Consumption", label = "Avg dishwasher water consumption per cycle", unit = "gal", unit_conversion = lambda liters: liters / LITERS_PER_GALLON)
    '''intervals = {
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
    )'''

def wh_to_kwh(rows):
    # energy per reading (Wh) = amps * volts * hours-per-reading
    total_wh = 0
    for (_, amps, _) in rows:
        total_wh += amps * VOLTAGE * INTERVAL_HOURS
    return total_wh / 1000  # Wh to kWh

def get_electricity_comparison(conn):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24) #compute 24 hours ago from now

    local_meta = DB_METADATA["local"]
    peer_meta = DB_METADATA["peer"]

    rows, sources = collect_data(connections, "Ammeter", start_time, now)

    local_rows = filter_by_topic(rows, local_meta["topic_substring"])
    peer_rows = filter_by_topic(rows, peer_meta["topic_substring"])

    #convert Wh to kWh
    local_kwh = wh_to_kwh(local_rows)
    peer_kwh = wh_to_kwh(peer_rows)

    output = [
        f"Electricity usage in the past 24 hours"
        f"Query at {utc_to_pst(now)}):",
        f"{local_meta['house']}'s House: {local_kwh:.2f} kWh ",
        f"{peer_meta['house']}'s House:  {peer_kwh:.2f} kWh ",
        f"Data {sources}",
    ]

    #choosing winner
    if local_kwh > peer_kwh:
        diff = local_kwh - peer_kwh
        output.append(
            f"{local_meta['house']}'s House consumed more, by {diff:.2f} kWh."
        )
    elif peer_kwh > local_kwh:
        diff = peer_kwh - local_kwh
        output.append(
            f"  → {peer_meta['house']}'s House consumed more, "
            f"by {diff:.2f} kWh."
        )
    else:
        output.append("  → Both houses consumed the same amount.")

    return "\n".join(output)


if __name__ == "__main__":
    print(get_avg_moisture(connections))
    print()
    print(get_avg_water(connections))
    print()
    print(get_electricity_comparison(connections))
    print()

    '''query = """
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
    )'''

#with psycopg2.connect(conn_str) as conn:
    #with conn.cursor() as cur:
        #cur.execute("SELECT version();")
        #print(cur.fetchone())
        #print(cur.execute('SELECT COUNT(*) FROM "Assn8_virtual";'))'''


#TCP Server

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