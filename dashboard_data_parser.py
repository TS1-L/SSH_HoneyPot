import pandas as pd
import re
import requests


def parse_creds_audits_log(creds_audits_log_file):
    data = []
    try:
        with open(creds_audits_log_file, 'r') as file:
            for line in file:
                parts = line.strip().split(', ')
                # Skip malformed lines — can happen during log rotation or a partial write
                if len(parts) < 3:
                    continue
                data.append([parts[0], parts[1], parts[2]])
    except FileNotFoundError:
        print(f"[!] Log file not found: {creds_audits_log_file}")
    df = pd.DataFrame(data, columns=["ip_address", "username", "password"])
    return df


def parse_cmd_audits_log(cmd_audits_log_file):
    data = []
    pattern = re.compile(r"Command (.+) executed by (\d+\.\d+\.\d+\.\d+)")
    try:
        with open(cmd_audits_log_file, 'r') as file:
            for line in file:
                match = pattern.search(line.strip())
                if match:
                    command, ip = match.groups()
                    data.append({'IP Address': ip, 'Command': command})
    except FileNotFoundError:
        print(f"[!] Log file not found: {cmd_audits_log_file}")
    df = pd.DataFrame(data)
    return df


def top_10_calculator(dataframe, column):
    top_10_df = None
    for col in dataframe.columns:
        if col == column:
            top_10_df = dataframe[column].value_counts().reset_index().head(10)
            top_10_df.columns = [column, "count"]
    return top_10_df


def get_country_code(ip):
    data_list = []
    # CleanTalk rate-limits to 1,000 lookups per 60 seconds
    url = f"https://api.cleantalk.org/?method_name=ip_info&ip={ip}"
    try:
        response = requests.get(url)
        api_data = response.json()
        if response.status_code == 200:
            data = response.json()
            ip_data = data.get('data', {})
            country_info = ip_data.get(ip, {})
            data_list.append({'IP Address': ip, 'Country_Code': country_info.get('country_code')})
        elif response.status_code == 429:
            print(api_data["error_message"])
            print(f"[!] CleanTalk IP->Geolocation Rate Limited Exceeded.\n Please wait 60 seconds or turn Country=False (default).\n {response.status_code}")
        else:
            print(f"[!] Error: Unable to retrieve data for IP {ip}. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"[!] Request failed: {e}")
    return data_list

def ip_to_country_code(dataframe):
    data = []
    for ip in dataframe['ip_address']:
        get_country = get_country_code(ip)
        if not get_country:
            continue
        data.append({"IP Address": ip, "Country_Code": get_country[0]["Country_Code"]})
    df = pd.DataFrame(data)
    return df
