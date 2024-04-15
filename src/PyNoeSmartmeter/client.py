"""Contains the Smartmeter API Client."""

import logging

import datetime
import os
import pickle
import httpx
import aiofiles


from .errors import SmartmeterLoginError, SmartmeterConnectionError

logger = logging.getLogger(__name__)


class Smartmeter:
    """Smartmeter client."""

    AUTH_URL = "https://smartmeter.netz-noe.at/orchestration/Authentication/Login"
    API_BASE_URL = "https://smartmeter.netz-noe.at/orchestration"

    API_USER_DETAILS_URL = API_BASE_URL + "/User/GetBasicInfo"
    API_ACCOUNTING_DETAILS_URL = API_BASE_URL + "/User/GetAccountIdByBussinespartnerId"
    API_METER_DETAILS_URL = API_BASE_URL + "/User/GetMeteringPointByAccountId"

    API_CONSUMPTION_URL = API_BASE_URL + "/ConsumptionRecord"

    SESSION_FILE = "noe_smartmeter_session_httpx.pkl"

    def __init__(self, username, password):
        """Access the Smartmeter API."""
        self.supports_api = False
        self._metering_point_id = None
        self._account_id = None
        self._session = None
        self._username = username
        self._password = password

    async def authenticate(self, username = None, password = None):
        """Load session file or authenticate user."""
        if username is not None:
            self._username = username
            await self._clear_stored_session()
        if password is not None:
            self._password = password
            await self._clear_stored_session()

        if await self._load_check_session():
           return True

        print("Starting new session and authenticate")
        session = httpx.AsyncClient(timeout=30.0)
        auth_data = {"user": self._username, "pwd": self._password}
        response = await session.post(self.AUTH_URL, data=auth_data)

        if response.status_code == 200:
            print("Authentication sucessful")
        elif response.status_code == 401:
            raise SmartmeterLoginError("Login failed. Check username/password.")
        else:
            raise SmartmeterConnectionError(
                f"Authentication failed with status {response.status_code}"
            )
        await self._save_session(session)
        
        self._session = session
        return True

    async def _check_session(self, session):
        try:
            response = await session.get(self.API_USER_DETAILS_URL)
            return response.status_code == 200
        except (TypeError) as error:
            print(error)
            return False

    async def _save_session(self, session):
        serialized_data = pickle.dumps(dict(session.cookies))
        async with aiofiles.open(self.SESSION_FILE, "wb") as f:
            await f.write(serialized_data)
    
    async def _load_check_session(self):
        # Check if a cached session exists
        print("Checking stored session")
        if os.path.exists(self.SESSION_FILE):
            async with aiofiles.open(self.SESSION_FILE, "rb") as f:
                data = await f.read()
                cookies = pickle.loads(data)
                session = httpx.AsyncClient(timeout=30.0, cookies=cookies)
                if await self._check_session(session):
                    print("Stored session is valid")
                    self._session = session
                    return True           
        print("Session is not stored or invalid!")                
        return False

    async def _clear_stored_session(self):
        if os.path.exists(self.SESSION_FILE):
            os.remove(self.SESSION_FILE)
            print("Stored session deleted successfully.")

    async def _call_api(self, url, params=None):
        if self._session is None:
            await self.authenticate()
        retry_count = 0
        while retry_count < 1:
            response = await self._session.get(url, params=params)
            if response.status_code == 401:
                await self.authenticate()
                retry_count += 1
            elif response.status_code == 200:
                return response

    async def get_user_details(self):
        """Load user details"""
        response = await self._call_api(self.API_USER_DETAILS_URL + "?context=2")
        return response.json()[0]

    async def get_accounting_details(self):
        """Load accounting details"""
        response = await self._call_api(self.API_ACCOUNTING_DETAILS_URL + "?context=2")
        entry = response.json()[0]

        has_smartmeter = entry["hasSmartMeter"]
        has_electricity = entry["hasElectricity"]
        has_communicative = entry["hasCommunicative"]
        has_active = entry["hasActive"]
        self.supports_api = (
            has_smartmeter and has_electricity and has_communicative and has_active
        )

        self._account_id = entry["accountId"]
        return entry

    async def get_meter_details(self):
        """Load meter details"""
        if self._account_id is None:
            await self.get_accounting_details()
        response = await self._call_api(
            self.API_METER_DETAILS_URL
            + "?context=2&accountId="
            + (self._account_id or "")
        )
        entry = response.json()[0]

        self._metering_point_id = entry["meteringPointId"]

        return entry

    async def get_consumption_per_day(self, day):
        """Load consumption for one day"""
        print(f"Load consumption for day {day}")
        if self._metering_point_id is None:
            await self.get_meter_details()
        try:
            response = await self._call_api(
                self.API_CONSUMPTION_URL + "/Day",
                params={"meterId": self._metering_point_id, "day": day},
            )
            data = response.json()[0]
            consumption_per_day = list(
                zip(data["peakDemandTimes"], data["meteredValues"])
            )
            return consumption_per_day
        except (httpx.RequestError, ValueError) as error:
            print(f"An error occurred: {error}")
            return []

    async def get_consumption_for_month(self, year, month):
        """Load consumption for one month"""
        print(f"Load consumption for month {month}/{year}")
        if self._metering_point_id is None:
            await self.get_meter_details()
        try:
            response = await self._call_api(
                self.API_CONSUMPTION_URL + "/Month",
                params={
                    "meterId": self._metering_point_id,
                    "year": year,
                    "month": month,
                },
            )
            data = response.json()[0]
            consumption_for_month = list(
                zip(data["peakDemandTimes"], data["meteredValues"])
            )
            return consumption_for_month
        except (httpx.RequestError, ValueError) as error:
            print(f"An error occurred: {error}")
            return []

    async def get_consumption_for_year(self, year):
        """Load consumption for one year"""
        print("Load consumption for year:", year)
        if self._metering_point_id is None:
            await self.get_meter_details()
        try:
            response = await self._call_api(
                self.API_CONSUMPTION_URL + "/Year",
                params={"meterId": self._metering_point_id, "year": year},
            )
            response.raise_for_status()  # Raise an exception if the response contains an HTTP error status code
            data = response.json()[0]
            consumption_for_year = list(zip(data["peakDemandTimes"], data["values"]))
            return consumption_for_year
        except (httpx.RequestError, ValueError) as error:
            print(f"An error occurred: {error}")
            return []

    async def get_consumption_since_date(self, input_date_string, offset):
        """Load consumption since a specific datetime and adds the offset"""
        current_date = datetime.date.today()
        input_date = datetime.datetime.strptime(input_date_string, "%d.%m.%Y %H:%M")
        energy_sum = 0

        if current_date == input_date.date():
            print("The current date is to new. Returning input!")
            return {"timestamp": input_date_string, "consumption": offset}

        # Add up day consumption after input time (hours)
        day_data = await self.get_consumption_per_day(input_date.strftime("%Y-%m-%d"))
        for time, consumption in day_data:
            formatted_time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S")
            if formatted_time > input_date:
                energy_sum += consumption

        # Add up the rest of the month consumption after input date (days)
        month_data = await self.get_consumption_for_month(
            input_date.year, input_date.month
        )
        energy_sum += sum(
            value[1] for value in month_data[input_date.day :] if value[1] is not None
        )

        # Add up the rest of the year consumption after input date (months)
        start_index = input_date.month
        end_index = 12
        if input_date.year == current_date.year:
            end_index = current_date.month - 1
        year_data = await self.get_consumption_for_year(input_date.year)
        energy_sum += sum(
            value[1]
            for value in year_data[start_index:end_index]
            if value[1] is not None
        )

        # Add up the rest of the time after the input dates year (months)
        if input_date.year != current_date.year:
            start_year = (
                input_date.year + 1
                if input_date.year + 1 <= current_date.year
                else input_date.year
            )
            for year in range(start_year, current_date.year + 1):
                year_values = await self.get_consumption_for_year(year)
                energy_sum += sum(
                    value[1] for value in year_values if value[1] is not None
                )

        # It is assumed that the last datapoint is from the current date at 00:00 since the smartmeter only transmits data once a day
        print(f"Consumption until {current_date.strftime("%d.%m.%Y %H:%M")}: {energy_sum + offset}")
        return {"timestamp": current_date.strftime("%d.%m.%Y %H:%M"), "consumption": energy_sum + offset}
