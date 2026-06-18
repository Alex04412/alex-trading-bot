import os

from avanza import Avanza


def build_client() -> Avanza:
    username = os.environ["USERNAME"]
    password = os.environ["PASSWORD"]
    totp_secret = os.environ["TOTP_SECRET"]

    return Avanza(
        {
            "username": username,
            "password": password,
            "totpSecret": totp_secret,
        }
    )


def main() -> None:
    avanza = build_client()
    overview = avanza.get_overview()
    print(overview)


if __name__ == "__main__":
    main()
