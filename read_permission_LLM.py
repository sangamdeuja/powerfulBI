import os
from dotenv import load_dotenv

load_dotenv()
import boto3
import mysql.connector


def create_read_only_user():
    try:
        # Establish connection to the MySQL RDS instance
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Create the new read-only user
            create_user_query = f"CREATE USER '{os.getenv('READ_USER')}' IDENTIFIED BY '{os.getenv('READ_USER_PASSWORD')}';"
            cursor.execute(create_user_query)
            print(f"User '{os.getenv('READ_USER')}' created successfully.")

            # Grant read-only permission (SELECT) on the specified database
            grant_privileges_query = f"GRANT SELECT ON {os.getenv('DB_NAME')}.* TO '{os.getenv('READ_USER')}';"
            cursor.execute(grant_privileges_query)
            print(
                f"Read-only privileges granted to user '{os.getenv('READ_USER')}' on database '{os.getenv('DB_NAME')}'."
            )

            # Apply changes
            cursor.execute("FLUSH PRIVILEGES;")
            print("Privileges flushed successfully.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed.")


create_read_only_user()
