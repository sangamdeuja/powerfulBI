import os
from dotenv import load_dotenv

load_dotenv()
import mysql.connector
from mysql.connector import errorcode

DB_HOST = os.getenv("DB_HOST")  # RDS endpoint
DB_PORT = os.getenv("DB_PORT")  # Default MySQL port
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
SQL_FILE = os.getenv("SQL_FILE")


def create_database(cursor, db_name):
    try:
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"Database {db_name} created successfully.")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DB_CREATE_EXISTS:
            print(f"Database {db_name} already exists.")
        else:
            print(f"Failed creating database: {err}")
            exit(1)


def execute_sql_file(cursor, filename):
    """
    Execute an SQL file line by line
    """
    with open(filename, "r") as sql_file:
        sql_commands = sql_file.read().split(";")  # Split by each SQL statement
        for command in sql_commands:
            try:
                if command.strip():
                    cursor.execute(command)
                    print(f"Executed command: {command}")
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                print(f"Skipped command: {command}")


def populate():
    # Connect to the MySQL RDS instance
    try:
        cnx = mysql.connector.connect(
            user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        cursor = cnx.cursor()

        # Create the new database
        create_database(cursor, DB_NAME)

        # Select the new database
        cnx.database = DB_NAME

        # Execute the SQL file to load the schema and data
        execute_sql_file(cursor, SQL_FILE)

        # Commit the transactions
        cnx.commit()

        # Close the connection
        cursor.close()
        cnx.close()

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    else:
        print("Script executed successfully.")


populate()
