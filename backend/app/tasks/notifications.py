from app.worker import app


@app.task(name="app.tasks.notifications.send_notification")
def send_notification(user_id: str, title: str, body: str):
    # TODO: implementeres i neste steg
    print(f"Notification to {user_id}: {title}")
