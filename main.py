from app import create_app

app = create_app()

if __name__ == "__main__":
    # Bind to localhost only. Put a reverse proxy with HTTPS in front for company-wide use.
    app.run(host="127.0.0.1", port=5000, debug=False)
