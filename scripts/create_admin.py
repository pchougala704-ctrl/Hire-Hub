import getpass
from app import create_app
from app.services.admin_service import AdminService


def main():
    app = create_app()
    email = input("Administrator email: ")
    name = input("Administrator name: ").strip()
    password = getpass.getpass("Password (at least 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    with app.app_context():
        db = app.extensions["mongo_db"]
        user = AdminService(db).create_admin(name, email, password)
        print(f"Administrator account created for {user['email']}. Sign in at /admin/login.")


if __name__ == "__main__":
    main()
