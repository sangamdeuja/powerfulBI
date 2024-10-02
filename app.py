from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import boto3
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from datetime import timedelta
from llm import *

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if os.getenv("ENVIRONMENT") == "DEVELOPMENT":
    app.config["SESSION_COOKIE_SECURE"] = False
else:
    app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = timedelta(minutes=30)

# Logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# AWS Cognito Configuration
COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_REGION = os.getenv("COGNITO_REGION")

# Create Cognito client
import boto3

# Define your AWS credentials(currently using this for testing/service principle or iam role will be used later)
ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.getenv("SECRET_ACCESS_KEY")


# Create the Cognito client
cognito_client = boto3.client(
    "cognito-idp",
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    region_name=COGNITO_REGION,
)


# Route for the main page
@app.route("/")
def index():
    logged_in = session.get("logged_in", False)
    username = session.get("username", None)
    return render_template("index.html", logged_in=logged_in, username=username)


# Route to sign in using AWS Cognito
@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username")
    password = request.json.get("password")
    logger.info(f"User {username} attempting to log in.")

    try:
        response = cognito_client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        access_token = response["AuthenticationResult"]["AccessToken"]
        print(response)
        print(access_token)

        # Store user information in session
        session.clear()  # Clear existing session
        session["logged_in"] = True
        session["username"] = username
        session["token"] = access_token
        session.permanent = True

        logger.info(f"User {username} logged in successfully.")

        return jsonify({"message": "Login successful"})
    except cognito_client.exceptions.NotAuthorizedException:
        logger.error(
            f"Failed login attempt for user {username}: Incorrect username or password."
        )
        return jsonify({"error": "The username or password is incorrect"}), 401
    except cognito_client.exceptions.UserNotFoundException:
        logger.warning(f"Login attempt for non-existent user: {username}.")
        return jsonify({"error": "User does not exist"}), 404
    except Exception as e:
        logger.error(f"An error occurred during login: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/logout", methods=["POST"])
def logout():
    logger.info(f"User {session.get('username')} logging out.")
    session.clear()
    return jsonify({"message": "Logged out successfully"})


# Route to handle chat messages
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    logger.info(
        f"Chat request received from user {session.get('username')}: {user_message}"
    )

    if session.get("logged_in"):
        token = session.get("token")
        try:
            user = cognito_client.get_user(AccessToken=token)
            # User is authenticated, use SQL agent
            agent_executor = create_sql_agent()
            logger.info("Accessing database to process chat request.")
            response = agent_executor.invoke(
                {"messages": [{"role": "user", "content": user_message}]}
            )
            logger.info("Database access completed successfully.")
            # Extract the last AI message
            last_ai_message = None
            for msg in response["messages"]:
                if isinstance(msg, AIMessage) and msg.content:
                    last_ai_message = msg.content
            return jsonify(
                {
                    "response": (
                        last_ai_message if last_ai_message else "No response from AI."
                    )
                }
            )
        except cognito_client.exceptions.NotAuthorizedException:
            logger.warning(f"Invalid token for user {session.get('username')}.")
            return jsonify({"error": "Invalid token"}), 403
        except Exception as e:
            logger.error(f"An error occurred during chat processing: {str(e)}")
            return jsonify({"error": str(e)}), 500
    else:
        # Unauthenticated user, use OpenAI agent
        prompt = create_openai_agent()
        prompt = prompt.format(user_message=user_message)
        response = model.invoke(prompt)
        return jsonify({"response": response.content})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
