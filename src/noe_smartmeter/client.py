"""Contains the Smartmeter API Client."""
import logging

import datetime
import os
import pickle
import requests


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
    
    def __init__(self, username, password):
        """Access the Smartmeter API."""
        self._supports_api = False
        self._metering_point_id = None
        self._account_id = None 
        self._session=None
        self._username = username
        self._password = password

        self._authenticate(username, password)
        self._retrieve_user_data()


    def _authenticate(self, username, password):
        session = None
        session_file='noe_smartmeter_session.pkl'
        
        # Check if a cached session exists
        if os.path.exists(session_file):
            with open(session_file, 'rb') as f:
                session = pickle.load(f)
                # Check if the cached session is still valid
                print("Check if stored Session is valid...")
                response = session.get(self.API_USER_DETAILS_URL)
                if response.status_code != 200:
                    session = None
                    print("Stored session is not valid")
                    print("Reauthenticating...")
                else:
                    print("Stored session is valid")
        
        # If a valid session doesn't exist, authenticate the user
        if session is None:
            session = requests.Session()
            auth_data = {'user': username, 'pwd': password}
            response = session.post(self.AUTH_URL, json=auth_data)
            if response.status_code == 200:
                print("Authentication sucessful")
            elif response.status_code == 401:
                raise SmartmeterLoginError("Login failed. Check username/password.")
            else:
                raise SmartmeterConnectionError(f"Authentication failed with status {response.status_code}")
            # Save the session to disk
            with open(session_file, 'wb') as f:
                pickle.dump(session, f)

        self._session = session        
        return self
    
    def _call_api(self, url, params = None):
        retry_count = 0 
        while retry_count < 1:
            response = self._session.get(url, params=params)
            if response.status_code == 401:
                self._authenticate(self._username, self._password)
                retry_count += 1
            elif response.status_code == 200:
                return response

    def _retrieve_user_data(self):
        accounting_details = self.get_accounting_details()
        meter_details = self.get_meter_details(accounting_details['accountId'])
        

        has_smartmeter = accounting_details['hasSmartMeter']
        has_electricity = accounting_details['hasElectricity']
        has_communicative = accounting_details['hasCommunicative']
        has_active = accounting_details['hasActive']
        
        self._supports_api = has_smartmeter and has_electricity and has_communicative and has_active
        self._metering_point_id = meter_details['meteringPointId']
        self._account_id = accounting_details['accountId']


    def get_user_details(self):
        response = self._call_api(self.API_USER_DETAILS_URL+"?context=2")
        return response.json()[0]
    
    def get_meter_details(self, account_id):
        response = self._call_api(self.API_METER_DETAILS_URL+'?context=2&accountId='+account_id)
        return response.json()[0]

    def get_accounting_details(self):
        response = self._call_api(self.API_ACCOUNTING_DETAILS_URL+"?context=2")
        return response.json()[0]

    def get_consumption_per_day(self, day):
        print(f"Load consumption for day {day}")
        try:
            response = self._call_api(
                self.API_CONSUMPTION_URL + "/Day",
                params={"meterId": self._metering_point_id, "day": day},
            )
            data = response.json()
            consumption_per_day = list(zip(data["peakDemandTimes"], data["meteredValues"]))
            return consumption_per_day
        except (requests.exceptions.RequestException, ValueError) as error:
            print(f"An error occurred: {error}")
            return []
    
    def get_consumption_for_month(self, year, month):
        print(f"Load consumption for month {month}/{year}")
        try:
            response = self._call_api(
                self.API_CONSUMPTION_URL + "/Month",
                params={"meterId": self._metering_point_id, "year": year, "month": month},
            )
            data = response.json()
            consumption_for_month = list(zip(data["peakDemandTimes"], data["meteredValues"]))
            return consumption_for_month
        except (requests.exceptions.RequestException, ValueError) as error:
            print(f"An error occurred: {error}")
            return []
    
    def get_consumption_for_year(self, year):
        print("Load consumption for year:", year)
        try:
            response = self._call_api(
                self.API_CONSUMPTION_URL + "/Year",
                params={"meterId": self._metering_point_id, "year": year},
            )
            response.raise_for_status()  # Raise an exception if the response contains an HTTP error status code
            data = response.json()
            consumption_for_year = list(zip(data["peakDemandTimes"], data["values"]))
            return consumption_for_year
        except (requests.exceptions.RequestException, ValueError) as error:
            print(f"An error occurred: {error}")
            return []


    def get_consumption_since_date(self, input_date_string, offset):
        current_date = datetime.date.today()
        input_date = datetime.datetime.strptime(input_date_string, "%d.%m.%Y %H:%M")
        energy_sum = 0

        if current_date == input_date.date():
            print("The current date is to new. Returning input!")
            return (input_date_string, offset)
        
        # Add up day consumption after input time (hours)
        day_data = self.get_consumption_per_day(input_date.strftime("%Y-%m-%d"))
        for time, consumption in day_data:
            formatted_time = datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
            if formatted_time > input_date:
                energy_sum += consumption

        # Add up the rest of the month consumption after input date (days)
        month_data = self.get_consumption_for_month(input_date.year, input_date.month)
        energy_sum += sum(value[1] for value in month_data[input_date.day:] if value[1] is not None)

        # Add up the rest of the year consumption after input date (months)
        start_index = input_date.month
        end_index = 12
        if input_date.year == current_date.year:
            end_index = current_date.month-1
        year_data = self.get_consumption_for_year(input_date.year)
        energy_sum += sum(value[1] for value in year_data[start_index:end_index] if value[1] is not None)

        # Add up the rest of the time after the input dates year (months)
        if input_date.year != current_date.year:
            start_year = input_date.year + 1 if input_date.year + 1 <= current_date.year else input_date.year
            for year in range(start_year, current_date.year + 1):
                year_values = self.get_consumption_for_year(year)
                energy_sum += sum(value[1] for value in year_values if value[1] is not None)

        # It is assumed that the last datapoint is from the current date at 00:00 since the smartmeter only transmits data once a day
        return (current_date.strftime("%d.%m.%Y %H:%M"), energy_sum + offset)
