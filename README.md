CECS 327: Assignment 8

-- How To Run --

1. Install dependencies: 'pip install psycopg2-binary python-dotenv tzdata'
2. Create .env file and enter corresponding values from env.example
3. Run the server: 'python3 327assn5server.py'
4. Run the client: 'python3 327assn5.py'
5. On the client, enter the server machine's IP (use ipconfig) and the valid port number
6. On the client, enter one of the valid queries listed and wait for the response from the server
7. Enter "quit" on the client machine to exit the system


-- Database Access --

Our system connects to two PostgreSQL databses hosted on Neon. We use psycopg2 to create the connection. Connection strings are stored in the .env file. Data is retrieved using SQL queries that extract the values of our sensors using JSON. 

-- Distributed Query Processing --

Distributed query processing was implemented with a helper function that decides whether it needs to query a local database or both the local and peer. This is what allows the system to act as a single data system while still separating the two 'smart houses'.

-- How Query Completeness was Determined? --

Our system determines whether a local database has the needed data by comparing the time of the query and the original data sharing time between the two parties. If the query time occurs after sharing begins, a local database is enough. But if a query requires data from before the sharing time, the peer database is then queried as well.

-- DataNiz Metadata/Sharing --

Each of the IoT devices records metadata including its topic, asset UID, name, etc. Our system uses the topic string metadata to identify between the two smart houses. Data sharing was used so that only new, incoming data from the shared house would be added to the local database, and not any historical data prior except for the local's.