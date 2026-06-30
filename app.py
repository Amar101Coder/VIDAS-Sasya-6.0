from main import app

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8001,
        threaded=True,
        debug=False,
        use_reloader=False
    )
