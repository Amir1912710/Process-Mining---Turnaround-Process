import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# ==============================
# 1) OAuth2 credentials
# ==============================
CLIENT_ID = "amir711-api-client"       # مثلا: "amir711-api-client"
CLIENT_SECRET = "jY5i0NH2d42DYdYakPwPuGltyMO7EuWJ"   # حط الـ secret هنا بس متشاركوش مع حد

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

def get_access_token():
    """
    Get OAuth2 access token from OpenSky using client credentials.
    """
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(TOKEN_URL, data=data, headers=headers)
    print("Token status:", response.status_code)

    if response.status_code != 200:
        print("Token error:", response.text)
        raise RuntimeError("Failed to get access token")

    token_info = response.json()
    return token_info["access_token"]


def get_flights_all(access_token, begin_dt, end_dt):
    """
    Call /flights/all with Bearer token between begin_dt and end_dt (UTC datetimes).
    NOTE: OpenSky بيحسب الـ flights من البيانات التاريخية،
    فغالبًا لازم تستخدم أيام سابقة مش اليوم الحالي. :contentReference[oaicite:1]{index=1}
    """
    begin = int(begin_dt.timestamp())
    end = int(end_dt.timestamp())

    url = "https://opensky-network.org/api/flights/all"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "begin": begin,
        "end": end
    }

    print("Requesting flights/all ...")
    print("URL:", url)
    print("Params:", params)

    r = requests.get(url, headers=headers, params=params)
    print("Flights status:", r.status_code)

    if r.status_code != 200:
        print("Flights error:", r.text)
        raise RuntimeError("Failed to get flights")

    flights = r.json()
    df = pd.DataFrame(flights)
    return df


if __name__ == "__main__":
    # ==============================
    # 2) اختر اليوم اللي عايز تجيب منه داتا
    # ==============================
    # OpenSky بيعمل الـ flights في batch لليوم اللي خلص (UTC)،
    # فخلينا ناخد "مبارح" UTC كيوم كامل. :contentReference[oaicite:2]{index=2}
    today_utc = datetime.now(timezone.utc).date()
    yesterday_utc = today_utc - timedelta(days=1)

    begin_dt = datetime(yesterday_utc.year, yesterday_utc.month, yesterday_utc.day, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = begin_dt + timedelta(days=1)

    print("Begin (UTC):", begin_dt)
    print("End   (UTC):", end_dt)

    # ==============================
    # 3) هات الـ token
    # ==============================
    token = get_access_token()
    print("Got access token.")

    # ==============================
    # 4) ننده على flights/all
    # ==============================
    df_flights = get_flights_all(token, begin_dt, end_dt)
    print("Number of flights:", len(df_flights))
    print(df_flights.head())

    # ==============================
    # 5) حفظ في CSV
    # ==============================
    out_file = "opensky_flights_yesterday.csv"
    df_flights.to_csv(out_file, index=False, encoding="utf-8")
    print(f"Saved flights to {out_file}")
