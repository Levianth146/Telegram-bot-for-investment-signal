import base64
import hashlib
import hmac
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import httpx
import pandas as pd
import truststore
from dotenv import load_dotenv
from vnstock import Quote


truststore.inject_into_ssl()
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


def create_headers(api_key, api_secret, path):
    date_value = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    nonce = uuid.uuid4().hex
    text = f"(request-target): get {path}\ndate: {date_value}\nnonce: {nonce}"
    signature = hmac.new(
        api_secret.encode("utf-8"), text.encode("utf-8"), hashlib.sha256
    ).digest()
    signature = quote(base64.b64encode(signature).decode("utf-8"), safe="")

    return {
        "Date": date_value,
        "X-Signature": (
            f'Signature keyId="{api_key}",algorithm="hmac-sha256",'
            f'headers="(request-target) date",signature="{signature}",'
            f'nonce="{nonce}"'
        ),
        "x-api-key": api_key,
        "version": os.getenv("DNSE_API_VERSION", "2026-07-23"),
    }


def parse_as_of_date(as_of_date):
    if isinstance(as_of_date, datetime):
        return as_of_date.date()
    if isinstance(as_of_date, date):
        return as_of_date
    if isinstance(as_of_date, str):
        return datetime.strptime(as_of_date, "%Y-%m-%d").date()
    raise TypeError("as_of_date must be YYYY-MM-DD, date, datetime, or None")


def get_live_close_price(ticker):
    api_key = os.getenv("DNSE_API_KEY")
    api_secret = os.getenv("DNSE_API_SECRET")
    if not api_key or not api_secret:
        return None

    endpoint = f"https://openapi.dnse.com.vn/price/{ticker}/close"
    path = f"/price/{ticker}/close"
    headers = create_headers(api_key, api_secret, path)

    try:
        response = httpx.get(
            endpoint,
            params={"boardId": "G1"},
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        prices = response.json().get("prices")
        if not prices or prices[0].get("closePrice") is None:
            return None

        price_record = prices[0]
        original_price = price_record["closePrice"]
        print(f"DNSE original price: {original_price}")
        price_time = pd.to_datetime(price_record.get("time"), errors="coerce")
        price_date = None if pd.isna(price_time) else price_time.date().isoformat()
        return {
            "price": original_price * 1000,
            "price_date": price_date,
            "price_source": "DNSE close",
            "price_adjustment": "UNADJUSTED",
            "point_in_time_safe": True,
            "warning": None,
        }
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def get_historical_close_price(ticker, as_of_date):
    end_date = parse_as_of_date(as_of_date)
    start_date = end_date - timedelta(days=30)

    try:
        history = Quote(symbol=ticker, source="kbs").history(
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval="1D",
        )
    except (Exception, SystemExit):
        return None

    if history is None or history.empty or not {"time", "close"}.issubset(history):
        return None

    history = history.copy()
    history["time"] = pd.to_datetime(history["time"], errors="coerce")
    history["close"] = pd.to_numeric(history["close"], errors="coerce")
    valid = history.loc[
        history["time"].notna()
        & history["close"].notna()
        & history["time"].dt.date.le(end_date)
    ].sort_values("time")
    if valid.empty:
        return None

    latest = valid.iloc[-1]
    return {
        "price": float(latest["close"]) * 1000,
        "price_date": latest["time"].date().isoformat(),
        "price_source": "KBS historical OHLCV via vnstock",
        "price_adjustment": "ADJUSTED",
        "point_in_time_safe": False,
        "warning": (
            "Historical KBS close is adjusted; it is date-aligned but cannot "
            "be treated as an unadjusted point-in-time market-cap price."
        ),
    }


def get_close_price(ticker, as_of_date=None, return_metadata=False):
    """Return live close or the last close on/before ``as_of_date``.

    Historical KBS OHLCV is adjusted and is labelled as such in metadata.
    Existing live callers receive the numeric price unless ``return_metadata``
    is requested.
    """
    ticker = ticker.strip().upper()
    result = (
        get_live_close_price(ticker)
        if as_of_date is None
        else get_historical_close_price(ticker, as_of_date)
    )
    if return_metadata:
        return result
    return None if result is None else result["price"]


if __name__ == "__main__":
    normalized_price = get_close_price("VNM")
    print("No VNM price available." if normalized_price is None else normalized_price)
